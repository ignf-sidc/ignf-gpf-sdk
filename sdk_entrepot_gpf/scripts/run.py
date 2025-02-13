"""SDK Python pour simplifier l'utilisation de l'API Entrepôt Géoplateforme."""

# pylint: disable=too-many-lines

import sys
import argparse
import traceback
from pathlib import Path
import shutil
from typing import List, Optional, Sequence
import requests
import toml

import sdk_entrepot_gpf
from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.auth.Authentifier import Authentifier
from sdk_entrepot_gpf.io.Errors import ConflictError, NotFoundError
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.scripts.example import Example
from sdk_entrepot_gpf.scripts.resolve import ResolveCli
from sdk_entrepot_gpf.workflow.action.DeleteAction import DeleteAction
from sdk_entrepot_gpf.workflow.action.ProcessingExecutionAction import ProcessingExecutionAction
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store.Datastore import Datastore
from sdk_entrepot_gpf.scripts.entities import Entities
from sdk_entrepot_gpf.scripts.delivery import Delivery
from sdk_entrepot_gpf.scripts.workflow import WorkflowCli


class Main:
    """Classe d'entrée pour utiliser la lib comme binaire."""

    def __init__(self, program_name: Optional[str] = None) -> None:  # pylint: disable=too-many-branches
        """Constructeur.

        Args:
            program_name (Optional[str], optional): nom du programme (utile car deux voies d'accès...). Defaults to None.

        Raises:
            GpfSdkError: levée si configuration non trouvée
        """
        # Résolution des paramètres utilisateurs
        self.o_args = Main.parse_args(program_name)
        self.datastore: Optional[str] = None

        # Résolution de la config
        if not Path(self.o_args.config).exists():
            raise GpfSdkError(f"Le fichier de configuration précisé ({self.o_args.config}) n'existe pas.")
        Config().read(self.o_args.config)

        # Si debug on monte la config
        if self.o_args.debug:
            Config().om.set_log_level("DEBUG")

        # Résolution du datastore
        self.datastore = self.__datastore()

        # Exécution de l'action demandée
        if self.o_args.task == "auth":
            self.auth()
        elif self.o_args.task == "me":
            self.me_()
        elif self.o_args.task == "config":
            self.config()
        elif self.o_args.task == "example":
            Example(self.o_args.type, self.o_args.name, self.o_args.output)
        elif self.o_args.task == "resolve":
            d_params = {x[0]: x[1] for x in self.o_args.params}
            ResolveCli(self.o_args.datastore, self.o_args.resolve, d_params)
        elif self.o_args.task == "workflow":
            # TODO : retirer le if et ne garder que le début
            if self.o_args.name is None and self.o_args.file is not None:
                d_params = {x[0]: x[1] for x in self.o_args.params}
                d_tags = {l_el[0]: l_el[1] for l_el in self.o_args.tags}
                WorkflowCli(
                    self.o_args.datastore,
                    self.o_args.file,
                    self.o_args.behavior,
                    self.o_args.step,
                    d_params,
                    d_tags,
                    self.o_args.comments,
                )
            else:  # TODO à retirer
                self.workflow()
        elif self.o_args.task == "delivery":
            Delivery(self.datastore, self.o_args.file, self.o_args.behavior, self.o_args.check_before_close, self.o_args.mode_cartes)
        elif self.o_args.task == "dataset":
            self.dataset()
        elif self.o_args.task == "delete":
            self.delete()
        else:
            if getattr(self.o_args, "file", None) is not None:
                Config().om.warning("L'argument --file dans ce contexte est déprécié, merci d'utiliser la commande 'delivery'.")
                if self.o_args.task == "upload":
                    self.upload()
                elif self.o_args.task == "annexe":
                    self.annexe()
                elif self.o_args.task == "static":
                    self.static()
                elif self.o_args.task == "metadata":
                    self.metadata()
                elif self.o_args.task == "key":
                    self.key()
            Entities(self.datastore, self.o_args.task, self.o_args.id, self.o_args)

    @staticmethod
    def parse_args(program_name: Optional[str] = None, args: Optional[Sequence[str]] = None) -> argparse.Namespace:  # pylint:disable=too-many-statements
        """Parse les paramètres utilisateurs.

        Args:
            args (Optional[Sequence[str]], optional): paramètres à parser, si None sys.argv utilisé.
            program_name (Optional[str], optional): nom du programme (utile car deux voies d'accès...). Defaults to None.

        Returns:
            argparse.Namespace: paramètres
        """
        # Parsing des paramètres
        o_parser = argparse.ArgumentParser(prog=program_name, description="Exécutable pour interagir avec l'API Entrepôt de la Géoplateforme.")
        o_parser.add_argument("--ini", dest="config", default="config.ini", help="Chemin vers le fichier de config à utiliser (config.ini par défaut)")
        o_parser.add_argument("--version", action="version", version=f"%(prog)s v{sdk_entrepot_gpf.__version__}")
        o_parser.add_argument("--debug", dest="debug", required=False, default=False, action="store_true", help="Passe l'appli en mode debug (plus de messages affichés)")
        o_parser.add_argument("--datastore", "-d", dest="datastore", required=False, default=None, help="Identifiant du datastore à utiliser")
        o_parser.add_argument("--mode-cartes", dest="mode_cartes", required=False, default=None, help="active la compatibilité des traitements du SDK avec ceux de cartes.gouv.fr")
        o_sub_parsers = o_parser.add_subparsers(dest="task", metavar="TASK", required=True, help="Tâche à effectuer")

        # Parser pour auth
        o_sub_parser = o_sub_parsers.add_parser("auth", help="Gestion de l'authentification")
        o_sub_parser.add_argument("show", type=str, nargs="?", default=None, choices=["token", "header"], help="Donnée à renvoyer")

        # Parser pour me
        o_sub_parser = o_sub_parsers.add_parser("me", help="Mes informations")

        # Parser pour config
        o_sub_parser = o_sub_parsers.add_parser("config", help="Affichage de la configuration")
        o_sub_parser.add_argument("section", type=str, nargs="?", default=None, help="Se limiter à une section")
        o_sub_parser.add_argument("option", type=str, nargs="?", default=None, help="Se limiter à une option (la section doit être renseignée)")
        o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin du fichier où sauvegarder la configuration (si null, la configuration est affichée)")

        # Parser pour resolve
        o_sub_parser = o_sub_parsers.add_parser("resolve", help="Résoudre des chaînes de configuration")
        o_sub_parser.add_argument("resolve", type=str, default=None, help="Chaîne à résoudre")
        o_sub_parser.add_argument("--params", "-p", type=str, nargs=2, action="append", metavar=("Clef", "Valeur"), default=[], help="Paramètres supplémentaires à passer au workflow à résoudre.")

        # Parser pour workflow
        s_epilog_workflow = """quatre types de lancement :
        * liste des exemples de workflow disponibles (déprécié) : `` (aucun arguments)
        * Récupération d'un workflow exemple (déprécié) : `--name NAME`
        * Vérification de la structure du fichier workflow et affichage des étapes : `--file FILE`
        * Lancement l'une étape d'un workflow : `--file FILE --step STEP [--behavior BEHAVIOR]`
          Il est alors possible de :
            - préciser des paramètres pour la résolution du workflow : `-p param1_clef param1_valeur -p "param2 clef" "param2 valeur"`
            - préciser des tags à ajouter : `-t clef1 valeur1 -t clef2 valeur2`
            - préciser des commentaires à ajouter : `-c "commentaire 1" -c "commentaire 2"`
        """
        o_sub_parser = o_sub_parsers.add_parser("workflow", help="Workflow (lancement, vérification)", epilog=s_epilog_workflow, formatter_class=argparse.RawTextHelpFormatter)
        o_sub_parser.add_argument("--file", "-f", type=str, default=None, help="Chemin du fichier à utiliser OU chemin où extraire le dataset")
        o_sub_parser.add_argument("--name", "-n", type=str, default=None, help="Nom du workflow à extraire")
        o_sub_parser.add_argument("--step", "-s", type=str, default=None, help="Étape du workflow à lancer")
        o_sub_parser.add_argument("--behavior", "-b", choices=ProcessingExecutionAction.BEHAVIORS, default=None, help="Action à effectuer si l'exécution de traitement existe déjà")
        o_sub_parser.add_argument("--tags", "-t", type=str, nargs=2, action="append", metavar=("Clef", "Valeur"), default=[], help="Tags à ajouter aux actions (plusieurs tags possibles)")
        o_sub_parser.add_argument(
            "--comments",
            "-c",
            type=str,
            default=[],
            action="append",
            metavar='"Le commentaire"',
            help="Commentaire(s) à ajouter aux actions (plusieurs commentaires possibles, mettre le commentaire entre guillemets)",
        )
        o_sub_parser.add_argument("--params", "-p", type=str, nargs=2, action="append", metavar=("Clef", "Valeur"), default=[], help="Paramètres supplémentaires à passer au workflow à résoudre.")

        # Parser pour example
        s_epilog_example = """Types de lancement :
        * lister les exemples de datasets disponibles : `example dataset`
        * récupérer un exemple de dataset disponible : `example dataset 1_dataset_vecteur`
        * récupérer un exemple de dataset disponible dans un dossier précis : `example dataset 1_dataset_vecteur mon/dossier/precis`
        * mêmes fonctions avec les workflows : `example workflow`
        """
        o_sub_parser = o_sub_parsers.add_parser(
            "example",
            help="Téléversement (livraisons, statiques, métadonnées et/ou clefs)",
            epilog=s_epilog_example,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        o_sub_parser.add_argument("type", type=str, choices=Example.TYPES, help="Type d'example à considérer")
        o_sub_parser.add_argument("name", nargs="?", default=None, help="Nom de l'exemple à récupérer (liste les exemples possibles si non indiqué)")
        o_sub_parser.add_argument("output", nargs="?", type=Path, default=Path("."), help="Dossier où enregistrer l'exemple")

        # Parser pour delivery
        s_epilog_delivery = """Types de lancement :
        * téléversement de données : `delivery upload_descriptor.jsonc`
        * re-livraison de données : `delivery upload_descriptor.jsonc -b CONTINUE`
        * téléversement de métadonnées : `delivery metadata_descriptor.jsonc`
        * téléversement de static : `delivery static_descriptor.jsonc`
        * création de clefs : `delivery keys_descriptor.jsonc`
        """
        o_sub_parser = o_sub_parsers.add_parser(
            "delivery",
            help="Téléversement (livraisons, statiques, métadonnées et/ou clefs)",
            epilog=s_epilog_delivery,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        o_sub_parser.add_argument("file", type=Path, default=None, help="Chemin du fichier descriptif à utiliser")
        o_sub_parser.add_argument("--behavior", "-b", choices=UploadAction.BEHAVIORS, default=None, help="Action à effectuer s'il y a un conflit.")
        o_sub_parser.add_argument("--check-before-close", action="store_true", default=False, help="Si on vérifie l'ensemble de la livraison avant de fermer la livraison (uniquement avec --file|-f)")

        # Parser pour les entités
        Entities.complete_parser_entities(o_sub_parsers)

        # Parser pour dataset
        # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
        o_sub_parser = o_sub_parsers.add_parser("dataset", help="(déprécié) Récupération de jeux de données d'exemple (listing, récupération)")
        o_sub_parser.add_argument("--name", "-n", type=str, default=None, help="Nom du dataset à extraire")
        o_sub_parser.add_argument("--folder", "-f", type=str, default=None, help="Dossier où enregistrer le dataset")

        # Parser pour delete
        o_sub_parser = o_sub_parsers.add_parser("delete", help="(déprécié) Suppression d'entité")
        o_sub_parser.add_argument("--type", choices=DeleteAction.DELETABLE_TYPES, required=True, help="Type de l'entité à supprimer")
        o_sub_parser.add_argument("--id", type=str, required=True, help="Identifiant de l'entité à supprimer")
        o_sub_parser.add_argument("--cascade", action="store_true", help="Action à effectuer si l'exécution de traitement existe déjà")
        o_sub_parser.add_argument("--force", action="store_true", help="Mode forcé, les suppressions sont faites sans aucune interaction")

        return o_parser.parse_args(args)

    def __datastore(self) -> Optional[str]:
        """Fonction pour récupérer l'id du datastore indiqué si l'utilisateur a indiqué son nom.

        Returns:
            Optional[str]: id du datastore
        """
        # On regarde si le datastore est donné
        if self.o_args.datastore:
            return Datastore.get_id(self.o_args.datastore)
        # Sinon en renvoi None
        return None

    def auth(self) -> None:
        """Authentifie l'utilisateur et retourne les informations de connexion demandées.
        Si aucune information est demandée, confirme juste la bonne authentification.
        """
        s_token = Authentifier().get_access_token_string()
        if self.o_args.show == "token":
            print(s_token)
        elif self.o_args.show == "header":
            print(Authentifier().get_http_header())
        else:
            print("Authentification réussie.")

    def me_(self) -> None:
        """Affiche les informations de l'utilisateur connecté."""
        # Requêtage
        o_response = ApiRequester().route_request("me_get")
        # Formatage
        d_info = o_response.json()
        # Info de base
        l_texts = [
            "Vos informations :",
            f"  * email : {d_info['email']}",
            f"  * nom : {d_info.get('first_name')} {d_info.get('last_name')}",
            f"  * votre id : {d_info['_id']}",
        ]
        # Gestion des communautés
        if not d_info["communities_member"]:
            l_texts.append("Vous n'êtes membre d'aucune communauté.")
        else:
            l_cm = d_info["communities_member"]
            l_texts.append("")
            l_texts.append(f"Vous êtes membre de {len(l_cm)} communauté(s) :")
            for d_cm in l_cm:
                d_community = d_cm["community"]
                if isinstance(d_cm["rights"], dict):
                    l_rights = [k.replace("_rights", "") for k, v in d_cm["rights"].items() if v is True]
                else:
                    l_rights = d_cm["rights"]
                s_rights = ", ".join(l_rights)
                l_texts.append("")
                l_texts.append(f"  * communauté « {d_community['name']} » :")
                l_texts.append(f"      - id de la communauté : {d_community['_id']}")
                l_texts.append(f"      - id du datastore : {d_community.get('datastore')}")
                l_texts.append(f"      - nom technique : {d_community['technical_name']}")
                l_texts.append(f"      - droits : {s_rights}")
        # Affichage
        print("\n".join(l_texts))

    def config(self) -> None:
        """Fonction pour afficher ou sauvegarder la configuration :
        * si une section (voire une option) est demandée, on affiche ce qui est demandé
        * sinon :
            * si un fichier est précisé on y enregistre toute la config
            * sinon on affiche toute la config
        """
        d_config = Config().get_config()

        # Juste une section ou toute la config ?
        if self.o_args.section is not None:
            # Juste une section
            d_section = d_config.get(self.o_args.section)
            if d_section is None:
                raise GpfSdkError(f"La section '{self.o_args.section}' n'existe pas dans la configuration.")
            if self.o_args.option is not None:
                # On nous demande une section.option
                if not str(self.o_args.option) in d_section:
                    raise GpfSdkError(f"L'option '{self.o_args.option}' n'existe pas dans la section '{self.o_args.section}'.")
                print(Config().get(self.o_args.section, self.o_args.option))
            else:
                # On nous demande toute une section
                print(toml.dumps({self.o_args.section: d_section}))
        else:
            # On nous demande toute la config
            if self.o_args.file is not None:
                # On sauvegarde la donnée
                try:
                    with open(self.o_args.file, mode="w", encoding="UTF-8") as f_config:
                        toml.dump(d_config, f_config)
                except PermissionError as e_permission_error:
                    raise GpfSdkError(f"Impossible d'écrire le fichier {self.o_args.file} : non autorisé") from e_permission_error
            else:
                # Sinon on l'affiche
                print(toml.dumps(d_config))

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def upload(self) -> None:
        """Création/Gestion des Livraison (Upload).
        Si un fichier descriptor est précisé, on effectue la livraison.
        Si un id est précisé, on affiche la livraison.
        Sinon on liste les Livraisons avec éventuellement des filtres.
        """
        Config().om.warning("Le téléversement de données via la commande 'upload' est déprécié, merci d'utiliser 'delivery' à la place.")
        # on livre les données selon le fichier descripteur donné
        d_res = Delivery.upload_from_descriptor_file(self.o_args.file, self.o_args.behavior, self.o_args.datastore, self.o_args.check_before_close, self.o_args.mode_cartes)
        # Affichage du bilan
        Config().om.info("-" * 100)
        if d_res["upload_fail"] or d_res["check_fail"]:
            Config().om.info("RÉCAPITULATIF DES PROBLÈMES :", green_colored=True)
            if d_res["upload_fail"]:
                Config().om.error(f"{len(d_res['upload_fail'])} livraisons échoués :\n" + "\n".join([f" * {s_nom} : {e_error}" for s_nom, e_error in d_res["upload_fail"].items()]))
            if d_res["check_fail"]:
                Config().om.error(f"{len(d_res['check_fail'])} vérifications de livraisons échoués :\n" + "\n".join([f" * {o_upload}" for o_upload in d_res["check_fail"]]))
            raise GpfSdkError(
                f"BILAN : {len(d_res['ok'])} livraisons effectuées sans erreur, {len(d_res['upload_fail'])} livraisons échouées, {len(d_res['check_fail'])} vérifications de livraisons échouées"
            )
        Config().om.info(f"BILAN : les {len(d_res['ok'])} livraisons se sont bien passées", green_colored=True)

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def dataset(self) -> None:
        """Liste les jeux de données d'exemple proposés et, si demandé par l'utilisateur, en export un."""
        Config().om.warning("La commande 'dataset' est dépréciée, merci d'utiliser 'example' à la place.")
        p_root = Config.data_dir_path / "datasets"
        if self.o_args.name is not None:
            s_dataset = str(self.o_args.name)
            print(f"Exportation du jeu de donnée '{s_dataset}'...")
            p_from = p_root / s_dataset
            if p_from.exists():
                p_output = Path(self.o_args.folder) if self.o_args.folder is not None else Path(s_dataset)
                if p_output.exists():
                    p_output = p_output / s_dataset
                print(f"Chemin de sortie : {p_output}")
                # Copie du répertoire
                shutil.copytree(p_from, p_output)
                print("Exportation terminée.")
            else:
                raise GpfSdkError(f"Jeu de données '{s_dataset}' introuvable.")
        else:
            l_children: List[str] = []
            for p_child in p_root.iterdir():
                if p_child.is_dir():
                    l_children.append(p_child.name)
            print("Jeux de données disponibles :\n   * {}".format("\n   * ".join(l_children)))

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def workflow(self) -> None:
        """Vérifie ou exécute un workflow."""
        p_root = Config.data_dir_path / "workflows"
        # Si demandé, on exporte un workflow d'exemple
        if self.o_args.name is not None:
            Config().om.warning("La commande 'workflow' pour récupérer un exemple de workflow est dépréciée, merci d'utiliser 'example' à la place.")
            s_workflow = str(self.o_args.name)
            print(f"Exportation du workflow '{s_workflow}'...")
            p_from = p_root / s_workflow
            if p_from.exists():
                p_output = Path(self.o_args.file) if self.o_args.file is not None else Path(s_workflow)
                if p_output.exists() and p_output.is_dir():
                    p_output = p_output / s_workflow
                print(f"Chemin de sortie : {p_output}")
                # Copie du répertoire
                shutil.copyfile(p_from, p_output)
                print("Exportation terminée.")
            else:
                raise GpfSdkError(f"Workflow '{s_workflow}' introuvable.")
        else:
            l_children: List[str] = []
            for p_child in p_root.iterdir():
                if p_child.is_file():
                    l_children.append(p_child.name)
            print("Jeux de données disponibles :\n   * {}".format("\n   * ".join(l_children)))

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def delete(self) -> None:
        """suppression d'une entité par son type et son id"""
        Config().om.warning("La commande 'delete' est dépréciée, merci d'utiliser la commande liée au type de l'entité à supprimer.")
        # création du workflow pour l'action de suppression
        d_action = {
            "type": "delete-entity",
            "entity_type": self.o_args.type,
            "entity_id": self.o_args.id,
            "cascade": self.o_args.cascade,
            "confirm": not self.o_args.force,
        }
        o_action_delete = DeleteAction("contexte", d_action)
        o_action_delete.run(self.o_args.datastore)

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def annexe(self) -> None:
        """Gestion des annexes"""
        Config().om.warning("Le téléversement d'annexes via la commande 'annexe' est déprécié, merci d'utiliser 'delivery' à la place.")
        if self.o_args.file is not None:
            # on livre les données selon le fichier descripteur donné
            d_res = Delivery.upload_annexe_from_descriptor_file(self.o_args.file, self.o_args.datastore)
            Delivery.display_bilan_upload_file(d_res)

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def static(self) -> None:
        """Gestion des fichiers statics"""
        Config().om.warning("Le téléversement de fichiers statiques via la commande 'static' est déprécié, merci d'utiliser 'delivery' à la place.")
        if self.o_args.file is not None:
            # on livre les données selon le fichier descripteur donné
            d_res = Delivery.upload_static_from_descriptor_file(self.o_args.file, self.o_args.datastore)
            Delivery.display_bilan_upload_file(d_res)

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def metadata(self) -> None:
        """Gestion des metadata"""
        Config().om.warning("Le téléversement de métadonnées via la commande 'metadata' est déprécié, merci d'utiliser 'delivery' à la place.")
        if self.o_args.file is not None:
            # on livre les données selon le fichier descripteur donné
            d_res = Delivery.upload_metadata_from_descriptor_file(self.o_args.file, self.o_args.datastore)
            Delivery.display_bilan_upload_file(d_res)

    # TODO : deprecated (v0.1.35) à retirer (v1.0.0)
    def key(self) -> None:
        """Gestion des clefs"""
        Config().om.warning("La création de clefs via la commande 'key' est déprécié, merci d'utiliser 'delivery' à la place.")
        if self.o_args.file is not None:
            Config().om.info("Création de clefs ...", green_colored=True)
            d_res = Delivery.create_key_from_file(self.o_args.file)
            # affichage
            Delivery.display_bilan_creation(d_res)


def main(program_name: Optional[str] = None) -> None:
    """Fonction principale d'appel en script.

    Args:
        program_name (Optional[str], optional): nom du programme (utile car deux voies d'accès...). Defaults to None.
    """
    try:
        Main(program_name)
        sys.exit(0)
    except GpfSdkError as e_gpf_api_error:
        Config().om.debug(traceback.format_exc())
        Config().om.critical(e_gpf_api_error.message)
    except NotFoundError as e_error:
        # gestion "globale" des NotFoundError
        Config().om.debug(traceback.format_exc())
        Config().om.critical(f"L'élément demandé n'existe pas ({e_error.message}). Contactez le support si vous n'êtes pas à l'origine de la demande. URL : {e_error.method} {e_error.url}.")
    except ConflictError as e_error:
        # gestion "globale" des ConflictError (ConfigurationAction et OfferingAction
        # possèdent chacune leur propre gestion)
        Config().om.debug(traceback.format_exc())
        Config().om.critical("La requête envoyée à l'Entrepôt génère un conflit. N'avez-vous pas déjà effectué l'action que vous essayez de faire ?")
        Config().om.error(e_error.message)
    except requests.Timeout as e_error:
        # gestion "globale" des timeout
        Config().om.debug(traceback.format_exc())
        Config().om.critical(f"Requête trop longe, timeout. URL : {str(e_error.request.method)+' ' +str(e_error.request.url) if e_error.request else ''}.")
    except NotImplementedError as e_error:
        Config().om.debug(traceback.format_exc())
        Config().om.critical(f"Fonctionnalité non implémentée : {e_error.args[0]}.")
    except Exception as e_exception:
        print(e_exception)
        Config().om.critical("Erreur non spécifiée :")
        Config().om.error(traceback.format_exc())
        Config().om.critical("Erreur non spécifiée.")
    sys.exit(1)
