from __future__ import annotations  # utile pour le typage "argparse._SubParsersAction[argparse.ArgumentParser]"

import argparse
import re
from typing import Callable, List, Optional
from tabulate import tabulate

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.DeleteAction import DeleteAction
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store import TYPE__ENTITY
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

from sdk_entrepot_gpf.scripts.utils import Utils


class Entities:
    """Classe pour manipuler les entités en cas d'utilisation cli."""

    ENTITIES = [
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
            if self.action(o_entity):  # si ça retourne True
                # On affiche l'entité
                Config().om.info(f"Affichage de l'entité {o_entity}", green_colored=True)
                Config().om.info(o_entity.to_json(indent=3))
        elif getattr(self.args, "publish_by_label", False) is True:
            Entities.action_annexe_publish_by_labels(self.args.publish_by_label.split(","), datastore=self.datastore)
        elif getattr(self.args, "unpublish_by_label", False) is True:
            Entities.action_annexe_unpublish_by_labels(self.args.unpublish_by_label.split(","), datastore=self.datastore)
        else:
            d_infos_filter = StoreEntity.filter_dict_from_str(self.args.infos)
            if getattr(self.args, "tags", None) is not None:
                d_tags_filter = StoreEntity.filter_dict_from_str(self.args.tags)
            else:
                d_tags_filter = None
            l_entities = self.entity_class.api_list(infos_filter=d_infos_filter, tags_filter=d_tags_filter, page=getattr(self.args, "page", None), datastore=self.datastore)
            Config().om.info(f"Affichage de {len(l_entities)} {self.entity_class.entity_titles()} :", green_colored=True)
            l_props = str(Config().get("cli", f"list_{self.entity_type}", "_id,name"))
            print(tabulate([o_e.get_store_properties(l_props.split(",")) for o_e in l_entities], headers="keys"))

    def action(self, o_entity: StoreEntity) -> bool:  # pylint:disable=too-many-return-statements
        """Traite les actions s'il y a lieu. Renvoie true si on doit afficher l'entité.

        Args:
            o_entity (StoreEntity): entité à traiter

        Returns:
            bool: true si on doit afficher l'entité
        """
        b_return = True
        # Gestion des actions communes
        if getattr(self.args, "delete", False) is True:
            assert isinstance(o_entity, Upload)
            Entities.action_entity_delete(o_entity, self.args.cascade, self.args.force, self.datastore)
            b_return = False

        # Gestion des actions liées aux Livraisons
        if getattr(self.args, "open", False) is True:
            assert isinstance(o_entity, Upload)
            Entities.action_upload_open(o_entity)
            b_return = False
        if getattr(self.args, "checks", False) is True:
            assert isinstance(o_entity, Upload)
            Entities.action_upload_checks(o_entity)
            b_return = False
        if getattr(self.args, "delete_files", None) is not None:
            assert isinstance(o_entity, Upload)
            Entities.action_upload_delete_files(o_entity, self.args.delete_files)
            b_return = False
        if getattr(self.args, "delete_failed_files", False) is True:
            assert isinstance(o_entity, Upload)
            Entities.action_upload_delete_failed_files(o_entity, self.datastore)
            b_return = False
        if getattr(self.args, "close", False) is True:
            assert isinstance(o_entity, Upload)
            Entities.action_upload_close(o_entity, self.args.mode_cartes)
            b_return = False

        # Gestion des actions liées aux Annexes
        if getattr(self.args, "publish", False) is True:
            assert isinstance(o_entity, Annexe)
            Entities.action_annexe_publish(o_entity)
            b_return = False
        if getattr(self.args, "unpublish", False) is True:
            assert isinstance(o_entity, Annexe)
            Entities.action_annexe_unpublish(o_entity)
            b_return = False

        # Gestion des actions liées aux Points d'accès
        if getattr(self.args, "publish_metadata", None) is not None:
            assert isinstance(o_entity, Endpoint)
            Entities.action_endpoint_publish_metadata(o_entity, self.args.publish_metadata, self.args.datastore)
            b_return = False
        if getattr(self.args, "unpublish_metadata", None) is not None:
            assert isinstance(o_entity, Endpoint)
            Entities.action_endpoint_unpublish_metadata(o_entity, self.args.unpublish_metadata, self.args.datastore)
            b_return = False

        return b_return

    @staticmethod
    def action_entity_delete(entity: StoreEntity, cascade: bool, force: bool, datastore: Optional[str]) -> None:
        """Suppression de l'entité indiquée, éventuellement en cascade.

        Args:
            entity (StoreEntity): entité à gérer
            cascade (bool): est-ce qu'il faut supprimer en cascade
            force (bool): est-ce qu'il faut demander confirmation
            datastore (Optional[str]): datastore à considérer
        """
        # création du workflow pour l'action de suppression
        d_action = {
            "type": "delete-entity",
            "entity_type": entity.entity_name(),
            "entity_id": entity.id,
            "cascade": cascade,
            "confirm": not force,
        }
        o_action_delete = DeleteAction("contexte", d_action)
        o_action_delete.run(datastore)

    @staticmethod
    def action_endpoint_publish_metadata(endpoint: Endpoint, l_metadata: List[str], datastore: Optional[str]) -> None:
        Metadata.publish(l_metadata, endpoint.id, datastore)
        Config().om.info(f"Les métadonnées ont été publiées sur le endpoint {endpoint}.")

    @staticmethod
    def action_endpoint_unpublish_metadata(endpoint: Endpoint, l_metadata: List[str], datastore: Optional[str]) -> None:
        Metadata.unpublish(l_metadata, endpoint.id, datastore)
        Config().om.info(f"Les métadonnées ont été dépubliées du endpoint {endpoint}.")

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
            Config().om.info(f"La livraison {upload} vient d'être rouverte.", green_colored=True)
            return
        raise GpfSdkError(f"La livraison {upload} n'est pas dans un état permettant de d'ouvrir la livraison ({upload['status']}).")

    @staticmethod
    def action_upload_close(
        upload: Upload,
        mode_cartes: bool,
        callback: Optional[Callable[[str], None]] = print,
        ctrl_c_action: Optional[Callable[[], bool]] = Utils.ctrl_c_upload,
    ) -> None:
        """fermeture d'une livraison

        Args:
            upload (Upload): livraison à fermer
            mode_cartes (Optional[bool]): Si le mode carte est activé
            callback (Optional[Callable[[str], None]]): fonction de callback à exécuter avec le message de suivi.
            ctrl_c_action (Optional[Callable[[], bool]]): gestion du ctrl-C
        Raises:
            GpfSdkError: impossible de fermer la livraison
        """
        # si ouverte : on ferme puis monitoring
        if upload.is_open():
            # fermeture de l'upload
            upload.api_close()
            Config().om.info(f"La livraison {upload} vient d'être fermée.", green_colored=True)
            # monitoring des tests :
            Utils.monitoring_upload(
                upload,
                "Livraison {upload} fermée avec succès.",
                "Livraison {upload} fermée en erreur !",
                callback,
                ctrl_c_action,
                mode_cartes,
            )
            return
        # si STATUS_CHECKING : monitoring
        if upload["status"] == Upload.STATUS_CHECKING:
            Config().om.info(f"La livraison {upload} est fermée, les tests sont en cours.")
            Utils.monitoring_upload(
                upload,
                "Livraison {upload} fermée avec succès.",
                "Livraison {upload} fermée en erreur !",
                callback,
                ctrl_c_action,
                mode_cartes,
            )
            return
        # si ferme OK ou KO : warning
        if upload["status"] in [Upload.STATUS_CLOSED, Upload.STATUS_UNSTABLE]:
            Config().om.warning(f"La livraison {upload} est déjà fermée, statut : {upload['status']}")
            return
        # autre : action impossible
        raise GpfSdkError(f"La livraison {upload} n'est pas dans un état permettant d'être fermée ({upload['status']}).")

    @staticmethod
    def action_upload_checks(upload: Upload) -> None:
        """Affiche les infos sur une livraison

        Args:
            upload (Upload): livraison à vérifier
        """
        d_checks = upload.api_list_checks()
        Config().om.info(f"Bilan des vérifications de la livraison {upload} :")
        if len(d_checks["passed"]) != 0:
            Config().om.info(f"\t * {len(d_checks['passed'])} vérifications passées avec succès :")
            for d_verification in d_checks["passed"]:
                Config().om.info(f"\t\t - {d_verification['check']['name']} ({d_verification['check']['_id']})")
        if len(d_checks["asked"] + d_checks["in_progress"]) != 0:
            Config().om.warning(f"* {len(d_checks['asked']) + len(d_checks['in_progress'])} vérifications en cours ou en attente :", yellow_colored=True)
            for d_verification in d_checks["asked"] + d_checks["in_progress"]:
                s_name = "asked" if d_verification in d_checks["asked"] else "in_progress"
                Config().om.info(f"\t\t - {s_name} {d_verification['check']['name']} ({d_verification['check']['_id']})")
        if len(d_checks["failed"]) != 0:
            Config().om.warning(f"* {len(d_checks['failed'])} vérifications échouées :", yellow_colored=True)
            for d_verification in d_checks["failed"]:
                o_check = CheckExecution(d_verification, datastore=upload.datastore)
                l_logs = o_check.api_logs_filter("ERROR")
                if l_logs:
                    s_logs = "\n" + "\n".join(l_logs)
                else:
                    s_logs = "\nPas de log contenant 'ERROR', regardez le détail des logs avec la commande 'logs'."
                Config().om.info(f"\t\t - {d_verification['check']['name']} ({d_verification['check']['_id']}) - extrait des logs :{s_logs}")

    @staticmethod
    def action_upload_delete_files(upload: Upload, delete_files: List[str]) -> None:
        """Supprime les fichiers distants indiqués. La livraison n'est ni ouverte ni fermée,
        mais l'utilisateur peut combiner les actions si besoin.

        Args:
            upload (Upload): livraison à considérer
            delete_files (List[str]): liste des fichiers distants à supprimer.
        """
        if not upload.is_open():
            raise GpfSdkError("La livraison est actuellement fermée, ajoutez '--open' à la commande si vous souhaitez qu'elle soit rouverte.")
        Config().om.info(f"Suppression de {len(delete_files)} fichiers téléversés sur la livraison {upload['name']} :")
        for s_file in delete_files:
            if s_file.endswith(".md5"):
                Config().om.info(f"\t - suppression du fichier de clefs '{s_file}'")
                upload.api_delete_data_file(s_file)
            else:
                Config().om.info(f"\t - suppression du fichier de données '{s_file}'")
                upload.api_delete_md5_file(s_file)
        Config().om.info(f"Suppression de {len(delete_files)} fichiers effectuée avec succès.", green_colored=True)

    @staticmethod
    def action_upload_delete_failed_files(upload: Upload, datastore: Optional[str]) -> None:
        """Liste et propose de supprimer les fichiers indiqués comme invalides par les vérifications.

        Args:
            upload (Upload): livraison concernée
            datastore (Optional[str]): datastore concerné
        """
        Config().om.info(f"Suppression des fichiers mal téléversés sur la livraison {upload['name']} :")
        Config().om.info("Listing des fichiers à supprimer...")
        o_regex = re.compile(r"\((.*?)\)")
        l_accepted_check_names = ["Vérification standard"]
        l_files = []
        l_check_execs = upload.api_list_checks()
        # On cherche des fichiers à supprimer uniquement pour la Vérification standard si elle est 'failed'
        for d_check_exec in l_check_execs["failed"]:
            if d_check_exec["check"]["name"] in l_accepted_check_names:
                o_check_exec = CheckExecution(d_check_exec, datastore=datastore)
                l_lines = o_check_exec.api_logs_filter("ERROR")
                for s_line in l_lines:
                    o_match = o_regex.search(s_line)
                    if o_match:
                        s_file = o_match.group(1)
                        l_files.append(s_file)
        if not l_files:
            Config().om.warning("Aucun fichier incorrect à supprimer.")
        else:
            s_files = "\n    * " + "\n    * ".join(l_files)
            Config().om.info(f"{len(l_files)} fichiers incorrects à supprimer :{s_files}")
            Config().om.warning("Voulez-vous effectuer la suppression ? (oui/NON)")
            s_rep = input()
            # si la réponse ne correspond pas à oui on sort
            if s_rep.lower() not in ["oui", "o", "yes", "y"]:
                Config().om.info("Suppression annulée.", green_colored=True)
                return
            # ouverture de la livraison
            upload.api_open()
            # Suppression des fichiers
            for s_file in l_files:
                upload.api_delete_data_file(s_file)
            Config().om.info(f"Suppression des {len(l_files)} fichiers effectuées avec succès.", green_colored=True)

    @staticmethod
    def action_annexe_publish(annexe: Annexe) -> None:
        """Publie l'annexe indiquée.

        Args:
            annexe (Annexe): annexe à publier
        """
        if annexe["published"]:
            Config().om.info(f"L'annexe ({annexe}) est déjà publiée.")
            return
        # modification de la publication
        annexe.api_partial_edit({"published": str(True)})
        Config().om.info(f"L'annexe ({annexe}) a été publiée.")

    @staticmethod
    def action_annexe_unpublish(annexe: Annexe) -> None:
        """Dé-publie l'annexe indiquée.

        Args:
            annexe (Annexe): annexe à dépublier.
        """
        if not annexe["published"]:
            Config().om.info(f"L'annexe ({annexe}) n'est pas publiée.")
            return
        # modification de la publication
        annexe.api_partial_edit({"published": str(False)})
        Config().om.info(f"L'annexe ({annexe}) a été dépubliée.")

    @staticmethod
    def action_annexe_publish_by_labels(l_labels: List[str], datastore: Optional[str]) -> None:
        i_nb = Annexe.publish_by_label(l_labels, datastore=datastore)
        Config().om.info(f"{i_nb} annexe(s) ont été publiée(s).")

    @staticmethod
    def action_annexe_unpublish_by_labels(l_labels: List[str], datastore: Optional[str]) -> None:
        i_nb = Annexe.unpublish_by_label(l_labels, datastore=datastore)
        Config().om.info(f"{i_nb} annexe(s) ont été dépubliée(s).")

    @staticmethod
    def complete_parser_entities(o_sub_parsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:  # pylint: disable=too-many-statements,too-many-branches
        """Complète le parser avec les sous-parsers pour chaque entité."""
        # Pour chaque entité
        for o_entity in Entities.ENTITIES:
            # On crée le parseur
            o_sub_parser = o_sub_parsers.add_parser(
                f"{o_entity.entity_name()}",
                help=f"Gestion des {o_entity.entity_titles()}",
                formatter_class=argparse.RawTextHelpFormatter,
            )
            # Puis on génère la doc en ajoutant les paramètres
            l_epilog = []
            l_epilog.append("""Types de lancement :""")
            # Id
            o_sub_parser.add_argument("id", type=str, nargs="?", default=None, help="Id de l'entité à afficher ou à utiliser pour lancer les actions")
            # Filtres
            o_sub_parser.add_argument("--infos", "-i", type=str, default=None, help=f"Filtrer les {o_entity.entity_titles()} selon les infos")
            o_sub_parser.add_argument("--page", "-p", type=int, default=None, help="Page à récupérer. Toutes si non indiqué.")
            if issubclass(o_entity, TagInterface):
                l_epilog.append(
                    f"""    * lister les {o_entity.entity_titles()} avec d'optionnels filtres sur les infos et les tags : {o_entity.entity_name()} [--infos INFO=VALEUR] [--tags TAG=VALEUR]"""
                )
                o_sub_parser.add_argument("--tags", "-t", type=str, default=None, help=f"Filtrer les {o_entity.entity_titles()} selon les tags")
            else:
                l_epilog.append(f"""    * lister les {o_entity.entity_titles()} avec d'optionnels filtres sur les infos : {o_entity.entity_name()} [--infos INFOS]""")
            l_epilog.append(f"""    * afficher le détail d'une entité : {o_entity.entity_name()} ID""")
            l_epilog.append("""    * effectuer une ACTION sur une entité :""")
            l_epilog.append(f"""        - suppression : {o_entity.entity_name()} ID --delete""")
            o_sub_parser.add_argument("--delete", action="store_true", help="Suppression de l'entité")
            l_epilog.append(f"""        - suppression en cascade : {o_entity.entity_name()} ID --delete --cascade""")
            o_sub_parser.add_argument("--cascade", action="store_true", help="Suppression en cascade")
            l_epilog.append(f"""        - suppression sans confirmation : {o_entity.entity_name()} ID --delete --force""")
            o_sub_parser.add_argument("--force", action="store_true", help="Suppression(s) sans confirmation")

            if o_entity == Annexe:
                l_epilog.append(f"""    * publication / dépublication : `{o_entity.entity_name()} ID [--publish|--unpublish]`""")
                o_sub_parser.add_argument("--publish", action="store_true", help="Publication de l'annexe")
                o_sub_parser.add_argument("--unpublish", action="store_true", help="Dépublication de l'annexe")
                l_epilog.append(f"""    * publication par label : `{o_entity.entity_name()} --publish-by-label label1,label2`""")
                o_sub_parser.add_argument("--publish-by-label", type=str, default=None, help="Publication des annexes portant les labels donnés (ex: label1,label2)")
                l_epilog.append(f"""    * dépublication par label : `{o_entity.entity_name()} --unpublish-by-label label1,label2`""")
                o_sub_parser.add_argument("--unpublish-by-label", type=str, default=None, help="Dépublication des annexes portant les labels donnés (ex: label1,label2)")

            if o_entity == Endpoint:
                l_epilog.append(f"""    * publication de métadonnée : `{o_entity.entity_name()} --publish-metadatas NOM_FICHIER`""")
                o_sub_parser.add_argument("--publish-metadatas", type=str, default=None, help="Publication des métadonnées indiquées (ex: fichier_1,fichier_2)")
                l_epilog.append(f"""    * dépublication de métadonnée : `{o_entity.entity_name()} --unpublish-metadatas NOM_FICHIER`""")
                o_sub_parser.add_argument("--unpublish-metadatas", type=str, default=None, help="Dépublication des métadonnées indiquées (ex: fichier_1,fichier_2)")

            if o_entity == Key:
                l_epilog.append("""    * création de clef : `--f FICHIER`\nExemple du contenu du fichier : `{"key": [{"name": "nom","type": "HASH","type_infos": {"hash": "mon_hash"}}]}`""")
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier décrivant les clefs à créer")

            if o_entity == Upload:
                l_epilog.append(f"""        - ouverture : {o_entity.entity_name()} ID --open""")
                o_sub_parser.add_argument("--open", action="store_true", default=False, help="Rouvrir une livraison fermée")
                l_epilog.append(f"""        - fermeture : {o_entity.entity_name()} ID --close""")
                o_sub_parser.add_argument("--close", action="store_true", default=False, help="Fermer une livraison ouverte")
                l_epilog.append(f"""        - synthèse des vérifications : {o_entity.entity_name()} ID --checks""")
                o_sub_parser.add_argument("--checks", action="store_true", default=False, help="Affiche le bilan des vérifications d'une livraison")
                l_epilog.append(f"""        - suppression de fichiers téléversés : {o_entity.entity_name()} ID --delete-files FILE [FILE]""")
                o_sub_parser.add_argument("--delete-files", type=str, nargs="+", default=None, help="Supprime les fichiers distants indiqués d'une livraison.")
                l_epilog.append(f"""        - suppression auto des fichiers mal téléversés {o_entity.entity_name()} ID --delete-failed-files""")
                o_sub_parser.add_argument("--delete-failed-files", action="store_true", default=False, help="Supprime les fichiers mal téléversés d'une livraison vérifiées et en erreur.")
                l_epilog.append(f"""    * créer / mettre à jour une livraison (déprécié) : {o_entity.entity_name()} --file FILE [--behavior BEHAVIOR] [--check-before-close]""")
                # TODO déprécié
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="(déprécié) Chemin vers le fichier descriptor dont on veut effectuer la livraison)")
                # TODO déprécié
                o_sub_parser.add_argument(
                    "--check-before-close", action="store_true", default=False, help="(déprécié) Si on vérifie l'ensemble de la livraison avant de fermer la livraison (uniquement avec --file|-f)"
                )
                # TODO déprécié
                o_sub_parser.add_argument("--behavior", "-b", choices=UploadAction.BEHAVIORS, default=None, help="(déprécié) Action à effectuer si la livraison existe déjà (uniquement avec -f)")

            l_epilog.append("""""")
            l_epilog.append("""Exemples :""")
            l_epilog.append(f"""    * Listing des {o_entity.entity_title()}s dont le nom contient 'D038' : {o_entity.entity_name()} --infos name=%D038%""")
            l_epilog.append(f"""    * Affichage d'une {o_entity.entity_title()} : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc""")
            l_epilog.append(f"""    * Suppression d'une {o_entity.entity_title()} en cascade : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc --delete --cascade""")
            if o_entity == Upload:
                l_epilog.append(f"""    * Réouverture d'une livraison : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc --open""")
                l_epilog.append(f"""    * Suppression d'un fichier : {o_entity.entity_name()} 576c85eb-6a2e-4d0c-a0c9-ddb83536e1dc --delete-file dossier/fichier.txt""")

            # TODO déprécié
            if o_entity == Static:
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier descriptor dont on veut effectuer la livraison)")
            # TODO déprécié
            if o_entity == Metadata:
                o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin vers le fichier de métadonnées que l'on veut téléverser)")

            # On met à jour l'épilogue suite à la génération de la doc
            o_sub_parser.epilog = "\n".join(l_epilog)
