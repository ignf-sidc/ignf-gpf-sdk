from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import requests


from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Errors import ConflictError
from sdk_entrepot_gpf.store.CheckExecution import CheckExecution
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.io.Dataset import Dataset
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.Errors import UploadFileError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract


class UploadAction:
    """Classe permettant d'accompagner la création d'une livraison.

    Attributes:
        __dataset (Dataset): dataset contenant les info de la livraison à créer
        __upload (Optional[Upload]): livraison représentant l'entité créée sur l'entrepôt
        __behavior (str): comportement à adopter si la livraison existe déjà sur l'entrepôt
    """

    BEHAVIOR_STOP = "STOP"
    BEHAVIOR_DELETE = "DELETE"
    BEHAVIOR_CONTINUE = "CONTINUE"
    BEHAVIORS = [BEHAVIOR_STOP, BEHAVIOR_CONTINUE, BEHAVIOR_DELETE]

    def __init__(self, dataset: Dataset, behavior: Optional[str] = None) -> None:
        self.__dataset: Dataset = dataset
        self.__upload: Optional[Upload] = None
        # On suit le comportement donnée en paramètre ou à défaut celui de la config
        self.__behavior: str = behavior if behavior is not None else Config().get_str("upload", "behavior_if_exists")

    def run(self, datastore: Optional[str]) -> Upload:
        """Crée la livraison décrite dans le dataset et livre les données avant de
        retourner la livraison créée.

        Args:
            datastore (Optional[str]): id du datastore à utiliser. Si None, le datastore sera récupéré dans la configuration.

        Raises:
            GpfSdkError: levée si création non effectuée

        Returns:
            livraison créée
        """
        Config().om.info("Création et complétion d'une livraison...")
        # Création de la livraison
        self.__create_upload(datastore)

        # Cas livraison fermé = déjà traité : on sort
        if self.upload and not self.upload.is_open():
            return self.upload

        # Ajout des tags
        self.__add_tags()
        # Ajout des commentaires
        self.__add_comments()
        # Envoie des fichiers de données
        self.__push_data_files()
        # Envoie des fichiers md5
        self.__push_md5_files()
        # Fermeture de la livraison
        self.__close()
        # Affiche et retourne la livraison
        if self.upload is not None:
            # Affichage
            Config().om.info(f"Livraison créée et complétée : {self.__upload}")
            Config().om.info("Création et complétion d'une livraison : terminé")
            # Retour
            return self.upload
        # On ne devrait pas arriver ici...
        raise GpfSdkError("Erreur à la création de la livraison.")

    def __create_upload(self, datastore: Optional[str]) -> None:
        """Crée l'upload après avoir vérifié s'il n'existe pas déjà...

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        """
        Config().om.info("Création d'une livraison...")
        # On tente de récupérer l'upload
        o_upload = self.find_upload(datastore)
        # S'il n'est pas null
        if o_upload is not None:
            # On sort en erreur si demandé
            if self.__behavior == self.BEHAVIOR_STOP:
                raise GpfSdkError(f"Impossible de créer la livraison, une livraison identique {o_upload} existe déjà.")
            # On supprime/recrée la livraison si demandé
            if self.__behavior == self.BEHAVIOR_DELETE:
                Config().om.warning(f"Une livraison identique {o_upload} va être supprimée puis recréée...")
                o_upload.api_delete()
                # on en crée une nouvelle (on utilise les champs de "upload_infos" du dataset)
                self.__upload = Upload.api_create(self.__dataset.upload_infos, route_params={"datastore": datastore})
                Config().om.warning(f"Livraison {self.__upload} recréée avec succès.")
            elif self.__behavior == self.BEHAVIOR_CONTINUE:
                # Sinon on continue avec cet upload pour le compléter (behavior == CONTINUE)
                # cas livraison fermé : message particulier
                if not o_upload.is_open():
                    Config().om.warning(f"Livraison identique {o_upload} trouvée et fermée, cette livraison ne sera pas mise à jour.")
                else:
                    Config().om.info(f"Livraison identique {o_upload} trouvée, le programme va la reprendre et la compléter.")
                self.__upload = o_upload
            else:
                raise GpfSdkError(f"Le comportement {self.__behavior} n'est pas reconnu, l'exécution de traitement est annulée.")
        else:
            # Si la livraison est nulle, on en crée une nouvelle (on utilise les champs de "upload_infos" du dataset)
            self.__upload = Upload.api_create(self.__dataset.upload_infos, route_params={"datastore": datastore})
            Config().om.info(f"Livraison {self.__upload['name']} créée avec succès.")

    def __add_tags(self) -> None:
        """Ajoute les tags."""
        if self.__upload is not None and self.__dataset.tags is not None:
            Config().om.info(f"Livraison {self.__upload['name']} : ajout des {len(self.__dataset.tags)} tags...")
            self.__upload.api_add_tags(self.__dataset.tags)
            Config().om.info(f"Livraison {self.__upload['name']} : les {len(self.__dataset.tags)} tags ont été ajoutés avec succès.")

    def __add_comments(self) -> None:
        """Ajoute les commentaires."""
        if self.__upload is not None:
            Config().om.info(f"Livraison {self.__upload['name']} : ajout des {len(self.__dataset.comments)} commentaires...")
            l_actual_comments = [d_comment["text"] for d_comment in self.__upload.api_list_comments() if d_comment]
            for s_comment in self.__dataset.comments:
                if s_comment not in l_actual_comments:
                    self.__upload.api_add_comment({"text": s_comment})
            Config().om.info(f"Livraison {self.__upload['name']} : les {len(self.__dataset.comments)} commentaires ont été ajoutés avec succès.")

    def __push_data_files(self) -> None:
        """Téléverse les fichiers de données (listés dans le dataset)."""
        if self.__upload is not None:
            # Liste les fichiers déjà téléversés sur l'entrepôt et récupère leur taille
            Config().om.info(f"Livraison {self.__upload['name']} : récupération de l'arborescence des données déjà téléversées...")
            i_file_upload = self.__push_files(
                list(self.__dataset.data_files.items()),
                self.__upload.api_push_data_file,
                self.__upload.api_delete_data_file,
            )

            Config().om.info(f"Livraison {self.__upload}: les {len(self.__dataset.data_files)} fichiers de données ont été ajoutés avec succès. ({i_file_upload} livrer lors de ce traitement)")

    def __push_md5_files(self) -> None:
        """Téléverse les fichiers de clefs (listés dans le dataset)."""
        if self.__upload is not None:
            i_file_upload = self.__push_files(
                [(p_file, "") for p_file in self.__dataset.md5_files],
                self.__normalise_api_push_md5_file,
                self.__upload.api_delete_md5_file,
            )
            Config().om.info(f"Livraison {self.__upload}: les {len(self.__dataset.md5_files)} fichiers md5 ont été ajoutés avec succès. ({i_file_upload} livrer lors de ce traitement)")

    def __normalise_api_push_md5_file(self, path: Path, nom: str) -> None:
        """fonction cachant api_push_md5_file pour avoir une fonction ayant les même entrées que api_push_data_file, utilisé comme paramétre de __push_files

        Args:
            path (Path): chemin le la chef MD5
            nom (str): non du ficher md5
        """
        if self.__upload is None:
            raise GpfSdkError(f"Aucune livraison de définie - impossible de livrer {nom}")
        self.__upload.api_push_md5_file(path)

    def __push_files(self, l_files: List[Tuple[Path, str]], f_api_push: Callable[[Path, str], None], f_api_delete: Callable[[str], None]) -> int:
        """pousse un ficher de données ou un ficher md5 sur le store. Gére la reprise de Livraison et les conflicts lors de la livraison.

        Args:
            l_files (List[Tuple[Path, str]]): liste de tuple Path du ficher à livre, nom du ficher sous la gpf
            f_api_push (Callable[[Path, str], None]): fonction pour livrer les données
            f_api_delete (Callable[[str], None]): fonction pour supprimé les données si livrer partiellement.

        Returns:
            int: nombre de ficher réellement téléverser durant l'action
        """
        if self.__upload is None:
            raise GpfSdkError("Aucune livraison de définie")
        # Liste les fichiers téléversés sur l'entrepôt et récupère leur taille
        l_arborescence = self.__upload.api_tree()
        d_destination_taille = UploadAction.parse_tree(l_arborescence)
        l_conflict = []
        i_file_upload = 0
        for p_file_path, s_api_path in l_files:
            # Regarde si le fichier du dataset est déjà dans la liste des fichiers téléversés sur l'entrepôt
            # NB: sur l'entrepot, tous les fichiers md5 sont à la racine
            s_data_api_path = f"{s_api_path}/{p_file_path.name}" if s_api_path else p_file_path.name
            Config().om.info(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}...")
            if s_data_api_path in d_destination_taille:
                # le fichier est déjà livré, on check sa taille :
                if d_destination_taille[s_data_api_path] == p_file_path.stat().st_size:
                    # le fichier a été complètement téléversé. On passe au fichier suivant.
                    Config().om.info(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: déjà livré")
                    continue

                # le fichier n'a pas été téléversé en totalité.
                # Si le mode "Append" n'est pas disponible sur le serveur, il faut supprimer le fichier à moitié téléversé.
                # Sinon il faudra reprendre le téléversement (!)
                f_api_delete(s_data_api_path)

            try:
                # livraison du fichier
                f_api_push(p_file_path, s_api_path)
                i_file_upload += 1
                Config().om.info(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: terminé")
            except requests.Timeout:
                Config().om.warning(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: timeout.")
                l_conflict.append((p_file_path, s_data_api_path))
            except ConflictError:
                Config().om.warning(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: conflict.")
                l_conflict.append((p_file_path, s_data_api_path))
        if l_conflict:
            Config().om.info(f"Livraison {self.__upload}: {len(l_conflict)} fichiers en conflict, vérification de leur livraisons...")
            l_error = self._check_file_uploaded(l_conflict)
            if l_error:
                raise UploadFileError(f"Livraison {self.__upload['name']} : Problème de livraison pour {len(l_error)} fichiers. Il faut relancer la livraison.", l_error)
        return i_file_upload

    def _check_file_uploaded(self, l_files: List[Tuple[Path, str]]) -> List[Tuple[Path, str]]:
        if self.__upload is None:
            raise GpfSdkError("Aucune livraison de définie")
        # on recharge la l'arborescence
        l_arborescence = self.__upload.api_tree()
        d_destination_taille = UploadAction.parse_tree(l_arborescence)
        l_error: List[Tuple[Path, str]] = []
        # vérifications
        for p_file_path, s_api_path in l_files:
            s_data_api_path = f"{s_api_path}/{p_file_path.name}" if s_api_path else p_file_path.name
            if s_data_api_path in d_destination_taille:
                # le fichier est déjà livré, on check sa taille :
                if d_destination_taille[s_data_api_path] == p_file_path.stat().st_size:
                    # le fichier a été complètement téléversé. On passe au fichier suivant.
                    Config().om.info(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: déjà livré")
                else:
                    Config().om.error(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: à re-livré, problème de taille")
                    l_error.append((p_file_path, s_api_path))
            else:
                Config().om.error(f"Livraison {self.__upload['name']} : livraison de {s_data_api_path}: Non trouvé dans la liste des fichiers livrer")
                l_error.append((p_file_path, s_api_path))
        return l_error

    def __close(self) -> None:
        """Ferme la livraison."""
        if self.__upload is not None:
            Config().om.info(f"Livraison {self.__upload['name']} : fermeture de la livraison...")
            self.__upload.api_close()
            Config().om.info(f"Livraison {self.__upload['name']} : livraison fermée avec succès. La livraison va maintenant être vérifiée par la Géoplateforme.")

    def find_upload(self, datastore: Optional[str]) -> Optional[Upload]:
        """Fonction permettant de lister un éventuel upload déjà existant à partir des critères d'unicité donnés.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.

        Returns:
            None si rien trouvé, sinon l'Upload trouvé
        """
        # Récupération des critères de filtre
        d_infos, d_tags = ActionAbstract.get_filters("upload", self.__dataset.upload_infos, self.__dataset.tags)
        # On peut maintenant filter les upload selon ces critères
        l_uploads = Upload.api_list(infos_filter=d_infos, tags_filter=d_tags, datastore=datastore)
        # S'il y a un ou plusieurs upload, on retourne le 1er :
        if l_uploads:
            return l_uploads[0]
        # sinon on retourne None
        return None

    @property
    def upload(self) -> Optional[Upload]:
        return self.__upload

    @staticmethod
    def monitor_until_end(upload: Upload, callback: Optional[Callable[[str], None]] = None, ctrl_c_action: Optional[Callable[[], bool]] = None) -> bool:
        """Attend que toute les vérifications liées à la Livraison indiquée
        soient terminées (en erreur ou en succès) avant de rendre la main.

        La fonction callback indiquée est exécutée à chaque vérification en lui passant en paramètre un
        message de suivi du nombre de vérifications par statut.

        Args:
            upload (Upload): Livraison à monitorer
            callback (Optional[Callable[[str], None]]): fonction de callback à exécuter avec le message de suivi.
            ctrl_c_action (Optional[Callable[[], bool]], optional): gestion du ctrl-C. Si None ou si la fonction renvoie True, il faut arrêter les vérifications.

        Returns:
            True si toutes les vérifications sont ok, sinon False
        """
        i_nb_sec_between_check = Config().get_int("upload", "nb_sec_between_check_updates")
        s_check_message_pattern = Config().get_str("upload", "check_message_pattern")
        b_success: Optional[bool] = None
        Config().om.info(f"Monitoring des vérifications toutes les {i_nb_sec_between_check} secondes...")
        while b_success is None:
            try:
                # On récupère les vérifications
                d_checks = upload.api_list_checks()
                # On peut déterminer b_success s'il n'y en a plus en attente et en cours
                if 0 == len(d_checks["asked"]) == len(d_checks["in_progress"]):
                    b_success = len(d_checks["failed"]) == 0
                # On affiche un rapport via la fonction de callback précisée
                s_message = s_check_message_pattern.format(
                    nb_asked=len(d_checks["asked"]),
                    nb_in_progress=len(d_checks["in_progress"]),
                    nb_passed=len(d_checks["passed"]),
                    nb_failed=len(d_checks["failed"]),
                )
                if callback is not None:
                    callback(s_message)
                # Si l'état est toujours indéterminé
                if b_success is None:
                    # On attend le temps demandé
                    time.sleep(i_nb_sec_between_check)

            except KeyboardInterrupt:
                # on appelle la callback de gestion du ctrl-C
                if ctrl_c_action is None or ctrl_c_action():
                    # on doit arrêter les vérifications :
                    # si les vérifications sont déjà terminées, on ne fait rien => transmission de l'interruption
                    d_checks = upload.api_list_checks()
                    if 0 == len(d_checks["asked"]) == len(d_checks["in_progress"]):
                        Config().om.warning("vérifications déjà terminées.")
                        raise

                    # arrêt des vérifications
                    Config().om.warning("Ctrl+C : vérifications en cours d’interruption, veuillez attendre...")
                    # suppression des vérifications non terminées
                    for d_check_exec in d_checks["in_progress"]:
                        CheckExecution(d_check_exec, upload.datastore).api_delete()
                    for d_check_exec in d_checks["asked"]:
                        # on doit attendre que l'exécution soit lancée pour n'annulée
                        o_check_exec = CheckExecution.api_get(d_check_exec["_id"], upload.datastore)
                        # on attend que l'exécution soit lancée
                        while o_check_exec["status"] == "WAITING":
                            time.sleep(1)
                            o_check_exec.api_update()
                        if o_check_exec["status"] == "PROGRESS":
                            o_check_exec.api_delete()

                    # On rouvre la livraison
                    upload.api_open()

                    # enfin, transmission de l'interruption
                    raise

        # Si on est sorti du while c'est que les vérifications sont terminées
        # On log le dernier rapport selon l'état et on sort
        if b_success:
            Config().om.info(s_message)
            return True
        Config().om.warning(s_message)
        return False

    @staticmethod
    def parse_tree(tree: List[Dict[str, Any]], prefix: str = "") -> Dict[str, int]:
        """Parse l'arborescence renvoyée par l'API en un dictionnaire associant le chemin de chaque fichier à sa taille.
        L'objectif est de permettre de facilement identifier quels sont les fichiers à (re)livrer.

        Args:
            tree (List[Dict[str, Any]]): arborescence à parser
            prefix (str): pré-fixe du chemin

        Returns:
            liste des fichiers envoyés et leur taille
        """
        # Création du dictionnaire pour stocker les fichiers et leur taille
        d_files: Dict[str, int] = {}
        # Parcours de l'arborescence
        for d_element in tree:
            # On complète le chemin
            if prefix != "":
                s_chemin = f"{prefix}/{d_element['name']}"
            else:
                s_chemin = str(d_element["name"])
            # Fichier ou dossier ?
            if d_element["type"].lower() == "file":
                # Fichier, on l'ajoute à notre dictionnaire
                d_files[s_chemin] = int(d_element["size"])
            elif d_element["type"].lower() == "directory":
                # Dossier, on itère dessus avec le nom du dossier comme préfixe
                d_sub_files = UploadAction.parse_tree(d_element["children"], prefix=s_chemin)
                # On fusionne ces fichiers à notre dict principal
                d_files = {**d_files, **d_sub_files}
            else:
                raise GpfSdkError(f"Type d'élément rencontré dans l'arborescence '{d_element['type']}' non géré. Contacter le support.")
        return d_files
