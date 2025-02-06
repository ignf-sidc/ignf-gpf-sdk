import argparse
from typing import List, Optional

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store import TYPE__ENTITY
from sdk_entrepot_gpf.store.Access import Access
from sdk_entrepot_gpf.store.Annexe import Annexe
from sdk_entrepot_gpf.store.Check import Check
from sdk_entrepot_gpf.store.CheckExecution import CheckExecution
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.Datastore import Datastore
from sdk_entrepot_gpf.store.Endpoint import Endpoint
from sdk_entrepot_gpf.store.Key import Key
from sdk_entrepot_gpf.store.Metadata import Metadata
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.Permission import Permission
from sdk_entrepot_gpf.store.Processing import Processing
from sdk_entrepot_gpf.store.Static import Static
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Tms import Tms
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.TagInterface import TagInterface

from sdk_entrepot_gpf.scripts.utils import monitoring_upload, ctrl_c_upload


class Entities:
    """Classe pour manipuler les entités en cas d'utilisation cli."""

    def __init__(self, datastore: Optional[str], entity_type: str, idu: Optional[str], args: argparse.Namespace) -> None:  # pylint: disable=too-many-branches
        """Si un id est précisé, on récupère l'entité et on fait d'éventuelles actions.
        Sinon on liste les entités avec éventuellement des filtres.

        Args:
            datastore (Optional[str], optional): datastore à considérer
            entity_type (str): type d'entité à gérer
            id (Optional[str]): id de l'entité à manipuler
            args (argparse.Namespace): reste des paramètres
        """

        self.datastore = datastore
        self.entity_type = entity_type
        self.entity_class = TYPE__ENTITY[entity_type]
        self.idu = idu
        self.args = args

        if self.idu is not None:
            o_entity = self.entity_class.api_get(self.idu, datastore=self.datastore)
            # On fait les actions
            if self.action(o_entity):
                Config().om.info(f"Affichage de l'entité {o_entity}", green_colored=True)
                # Si on est là c'est qu'on doit afficher l'entité
                Config().om.info(o_entity.to_json(indent=3))
        else:
            d_infos_filter = StoreEntity.filter_dict_from_str(self.args.infos)
            d_tags_filter = StoreEntity.filter_dict_from_str(self.args.tags)
            l_uploads = self.entity_class.api_list(infos_filter=d_infos_filter, tags_filter=d_tags_filter, datastore=self.datastore)
            for o_upload in l_uploads:
                Config().om.info(f"{o_upload}")

    def action(self, o_entity: StoreEntity) -> bool:
        """Traite les actions s'il y a lieu. Renvoie true si on doit afficher l'entité.

        Args:
            o_entity (StoreEntity): entité à traiter

        Returns:
            bool: true si on doit afficher l'entité
        """
        if getattr(self.args, "open", False) is True:
            assert isinstance(o_entity, Upload)
            self.action_upload_open(o_entity)
            return False
        if getattr(self.args, "close", False) is True:
            assert isinstance(o_entity, Upload)
            self.action_upload_close(o_entity, self.args.mode_cartes)
            return False
        if getattr(self.args, "checks", False) is True:
            assert isinstance(o_entity, Upload)
            self.action_upload_checks(o_entity)
            return False
        if getattr(self.args, "delete_files", None) is None:
            assert isinstance(o_entity, Upload)
            self.action_upload_delete_files(o_entity, self.args.delete_files)
            return False
        if getattr(self.args, "delete_failed_files", False) is True:
            assert isinstance(o_entity, Upload)
            self.action_upload_delete_failed_files(o_entity)
            return False
        return True

    @staticmethod
    def action_upload_open(upload: Upload) -> None:
        """réouverture d'une livraison

        Args:
            upload (Upload): livraison à ouvrir

        Raises:
            GpfSdkError: impossible d'ouvrir la livraison
        """
        if upload.is_open():
            Config().om.warning(f"La livraison {upload} est déjà ouverte.")
            return
        if upload["status"] in [Upload.STATUS_CLOSED, Upload.STATUS_UNSTABLE]:
            upload.api_open()
            Config().om.info(f"La livraison {upload} viens d'être rouverte.", green_colored=True)
            return
        raise GpfSdkError(f"La livraison {upload} n'est pas dans un état permettant de d'ouvrir la livraison ({upload['status']}).")

    @staticmethod
    def action_upload_close(upload: Upload, mode_cartes: bool) -> None:
        """fermeture d'une livraison

        Args:
            upload (Upload): livraison à fermer
            mode_cartes (Optional[bool]): Si le mode carte est activé

        Raises:
            GpfSdkError: impossible de fermer la livraison
        """
        # si ouverte : on ferme puis monitoring
        if upload.is_open():
            # fermeture de l'upload
            upload.api_close()
            Config().om.info(f"La livraison {upload} viens d'être Fermée.", green_colored=True)
            # monitoring des tests :
            monitoring_upload(upload, "Livraison {upload} fermée avec succès.", "Livraison {upload} fermée en erreur !", print, ctrl_c_upload, mode_cartes)
            return
        # si STATUS_CHECKING : monitoring
        if upload["status"] == Upload.STATUS_CHECKING:
            Config().om.info(f"La livraison {upload} est fermé, les tests sont en cours.")
            monitoring_upload(upload, "Livraison {upload} fermée avec succès.", "Livraison {upload} fermée en erreur !", print, ctrl_c_upload, mode_cartes)
            return
        # si ferme OK ou KO : warning
        if upload["status"] in [Upload.STATUS_CLOSED, Upload.STATUS_UNSTABLE]:
            Config().om.warning(f"La livraison {upload} est déjà fermée, status : {upload['status']}")
            return
        # autre : action impossible
        raise GpfSdkError(f"La livraison {upload} n'est pas dans un état permettant de fermer la livraison ({upload['status']}).")

    @staticmethod
    def action_upload_checks(upload: Upload) -> None:
        """
        Affiche les infos sur une livraison
        Args:
            upload (Upload): livraison à vérifier
        """
        d_checks = upload.api_list_checks()
        Config().om.info(f"Bilan des vérifications de la livraison {upload} :")
        if len(d_checks["passed"]) != 0:
            Config().om.info(f"\t * {len(d_checks['passed'])} vérifications passées:")
            for d_verification in d_checks["passed"]:
                Config().om.info(f"\t\t {d_verification['check']['name']} {d_verification['check']['_id']}")
        if len(d_checks["asked"] + d_checks["in_progress"]) != 0:
            Config().om.warning("* " + str(len(d_checks["asked"]) + len(d_checks["in_progress"])) + " vérifications en cours ou en attente:")
            for d_verification in d_checks["asked"] + d_checks["in_progress"]:
                s_name = "asked" if d_verification in d_checks["asked"] else "in_progress"
                Config().om.warning(f"\t {s_name} {d_verification['check']['name']} {d_verification['check']['_id']}")
        if len(d_checks["failed"]) != 0:
            Config().om.error(f"* {len(d_checks['failed'])} vérifications échouées:")
            for d_verification in d_checks["failed"]:
                Config().om.error(f"\t {d_verification['check']['name']} {d_verification['check']['_id']}")
                o_check = CheckExecution(d_verification, datastore=upload.datastore)
                l_lines = o_check.api_logs_filter("ERROR")
                for s_line in l_lines:
                    Config().om.error(s_line)

    @staticmethod
    def action_upload_delete_files(upload: Upload, delete_files: List[str]) -> None:
        Config().om.info(f"Suppression de {len(delete_files)} fichiers téléversés sur la livraison {upload} :")

    @staticmethod
    def action_upload_delete_failed_files(upload: Upload) -> None:
        Config().om.info(f"Suppression des fichiers mal téléversés sur la livraison {upload} :")

    @staticmethod
    def complete_parser_entities(o_sub_parsers) -> None:  # pylint: disable=too-many-statements,too-many-branches
        """Complète le parser avec les sous-parsers pour les entités."""
        # Parsers pour entités
        l_entities = [
            Access,
            Annexe,
            Check,
            CheckExecution,
            Configuration,
            Datastore,
            Endpoint,
            Key,
            Metadata,
            Offering,
            Permission,
            Processing,
            ProcessingExecution,
            Static,
            StoredData,
            Tms,
            Upload,
        ]
        for o_entity in l_entities:
            # On génère la doc
            l_epilog = []
            l_epilog.append("""Types de lancement :""")
            if issubclass(o_entity, TagInterface):
                l_epilog.append(f"""    * lister les {o_entity.entity_title()}s avec d'optionnels filtres sur les infos et les tags : {o_entity.entity_name()} [--infos INFOS] [--tags TAGS]""")
            else:
                l_epilog.append(f"""    * lister les {o_entity.entity_title()}s avec d'optionnels filtres sur les infos : {o_entity.entity_name()} [--infos INFOS]""")
            l_epilog.append(f"""    * afficher le détail d'une entité : {o_entity.entity_name()} ID""")
            l_epilog.append("""    * effectuer une ACTION sur une entité :""")
            l_epilog.append(f"""        - suppression : {o_entity.entity_name()} ID --delete""")
            l_epilog.append(f"""        - suppression sans confirmation : {o_entity.entity_name()} ID --delete --force""")
            if o_entity == Annexe:
                l_epilog.append(f"""    * publication / dépublication : `{o_entity.entity_name()} ID [--publish|--unpublish]`""")
                l_epilog.append(f"""    * publication par label : `{o_entity.entity_name()} --publish-by-label label1,label2`""")
                l_epilog.append(f"""    * dépublication par label : `{o_entity.entity_name()} --unpublish-by-label label1,label2`""")
            if o_entity == Endpoint:
                l_epilog.append(f"""    * publication de métadonnées : `{o_entity.entity_name()} --publish-metadatas NOM_FICHIER`""")
                l_epilog.append(f"""    * dépublication de métadonnées : `{o_entity.entity_name()} --unpublish-metadatas NOM_FICHIER`""")
            if o_entity == Key:
                l_epilog.append("""    * création de clefs : `--f FICHIER`\nExemple du contenu du fichier : `{"key": [{"name": "nom","type": "HASH","type_infos": {"hash": "mon_hash"}}]}`""")
            if o_entity == Upload:
                l_epilog.append(f"""        - ouverture : {o_entity.entity_name()} ID --open""")
                l_epilog.append(f"""        - fermeture : {o_entity.entity_name()} ID --close""")
                l_epilog.append(f"""        - synthèse des vérifications : {o_entity.entity_name()} ID --checks""")
                l_epilog.append(f"""        - suppression de fichiers téléversés : {o_entity.entity_name()} ID --delete-files FILE [FILE]""")
                l_epilog.append(f"""        - suppression auto des fichiers mal téléversés {o_entity.entity_name()} ID --delete-failed-files""")
                l_epilog.append(f"""    * créer / mettre à jour une livraison (déprécié) : {o_entity.entity_name()} --file FILE [--behavior BEHAVIOR] [--check-before-close]""")
            l_epilog.append("""""")
            l_epilog.append("""Exemples :""")
            l_epilog.append(f"""    * Listing des {o_entity.entity_title()}s dont le nom contient 'D038' : {o_entity.entity_name()} --infos name=%D038%""")
            l_epilog.append(f"""    * Affichage d'une {o_entity.entity_title()} : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc""")
            l_epilog.append(f"""    * Suppression d'une {o_entity.entity_title()} en cascade : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc --delete --cascade""")
            if o_entity == Upload:
                l_epilog.append(f"""    * Réouverture d'une livraison : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc --open""")
                l_epilog.append(f"""    * Suppression d'un fichier : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc --delete-file dossier/fichier.txt""")
            # Puis le parser
            o_sub_parser = o_sub_parsers.add_parser(
                f"{o_entity.entity_name()}",
                help=f"Gestion des {o_entity.entity_title()}",
                epilog="\n".join(l_epilog),
                formatter_class=argparse.RawTextHelpFormatter,
            )
            o_sub_parser.add_argument("id", type=str, nargs="?", default=None, help="Id de l'entité afficher")
            # Filtres
            o_sub_parser.add_argument("--infos", "-i", type=str, default=None, help="Filtrer les livraisons selon les infos")
            if issubclass(o_entity, TagInterface):
                o_sub_parser.add_argument("--tags", "-t", type=str, default=None, help="Filtrer les livraisons selon les tags")
            # Actions
            if o_entity == Annexe:
                o_sub_parser.add_argument("--publish", action="store_true", help="Publication de l'annexe (uniquement avec --id)")
                o_sub_parser.add_argument("--unpublish", action="store_true", help="Dépublication de l'annexe (uniquement avec --id)")
                o_sub_parser.add_argument("--publish-by-label", type=str, default=None, help="Publication des annexes portant les labels donnés (ex: label1,label2)")
                o_sub_parser.add_argument("--unpublish-by-label", type=str, default=None, help="Dépublication des annexes portant les labels donnés (ex: label1,label2)")
            if o_entity == Endpoint:
                o_sub_parser.add_argument("--publish-metadatas", type=str, default=None, help="Publication des métadonnées indiquées (ex: fichier_1,fichier_2)")
                o_sub_parser.add_argument("--unpublish-metadatas", type=str, default=None, help="Dépublication des métadonnées indiquées (ex: fichier_1,fichier_2)")
            if o_entity == Static:
                # TODO déprécié
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier descriptor dont on veut effectuer la livraison)")
            if o_entity == Metadata:
                # TODO déprécié
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier de métadonnées que l'on veut téléverser)")
            if o_entity == Key:
                # TODO déprécié
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier décrivant les clefs à créer")
            if o_entity == Upload:
                o_exclusive = o_sub_parser.add_mutually_exclusive_group()
                o_exclusive.add_argument("--open", action="store_true", default=False, help="Rouvrir une livraison fermée (uniquement avec --id)")
                o_exclusive.add_argument("--close", action="store_true", default=False, help="Fermer une livraison ouverte (uniquement avec --id)")
                o_exclusive.add_argument("--checks", action="store_true", default=False, help="Affiche le bilan des vérifications d'une livraison")
                o_exclusive.add_argument("--delete-files", type=str, default=False, help="Supprime les fichiers téléversés indiqué d'une livraison.")
                o_exclusive.add_argument("--delete-failed-files", action="store_true", default=False, help="Supprime les fichiers mal téléversés d'une livraison vérifiées et en erreur.")
                # TODO déprécié
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier descriptor dont on veut effectuer la livraison)")
                # TODO déprécié
                o_sub_parser.add_argument(
                    "--check-before-close", action="store_true", default=False, help="Si on vérifie l'ensemble de la livraison avant de fermer la livraison (uniquement avec --file|-f)"
                )
                # TODO déprécié
                o_sub_parser.add_argument("--behavior", "-b", choices=UploadAction.BEHAVIORS, default=None, help="Action à effectuer si la livraison existe déjà (uniquement avec -f)")
