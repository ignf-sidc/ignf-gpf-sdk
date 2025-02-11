import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper
from sdk_entrepot_gpf.io.Color import Color
from sdk_entrepot_gpf.io.DescriptorFileReader import DescriptorFileReader
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.UploadDescriptorFileReader import UploadDescriptorFileReader
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store.Annexe import Annexe
from sdk_entrepot_gpf.store.Key import Key
from sdk_entrepot_gpf.store.Metadata import Metadata
from sdk_entrepot_gpf.store.Static import Static
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.Errors import GpfSdkError

from sdk_entrepot_gpf.scripts.utils import Utils


class Delivery:
    """Classe pour manipuler les entités en cas d'utilisation cli."""

    def __init__(self, datastore: Optional[str], file: Path, behavior: str, check_before_close: bool, mode_cartes: bool) -> None:
        """Si un id est précisé, on récupère l'entité et on fait d'éventuelles actions.
        Sinon on liste les entités avec éventuellement des filtres.

        Args:
            datastore (Optional[str], optional): datastore à considérer
            file (Path): chemin du fichier descriptif à traiter
            behavior (str): comportement de gestion des conflits
            check_before_close (bool): si on doit revérifier la livraison avant sa fermeture
            mode_cartes (bool): activation du mode cartes.gouv
        """
        self.datastore = datastore
        self.file = file
        self.behavior = behavior
        self.check_before_close = check_before_close
        self.mode_cartes = mode_cartes
        # On ouvre le fichier indiqué
        self.data = JsonHelper.load(self.file)

        # On traite chaque type de livraison à effectuer selon les clefs parentes

        if "datasets" in self.data:
            Config().om.info("Téléversement de données...", green_colored=True)
            # on livre les données selon le fichier descripteur donné
            d_res = self.upload_from_descriptor_file(self.file, self.behavior, self.datastore, self.check_before_close, self.mode_cartes)
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

        if "annexe" in self.data:
            Config().om.info("Téléversement de fichiers annexes...", green_colored=True)
            d_res = self.upload_annexe_from_descriptor_file(self.file, self.datastore)
            self.display_bilan_upload_file(d_res)

        if "static" in self.data:
            Config().om.info("Téléversement de fichiers statiques...", green_colored=True)
            d_res = self.upload_static_from_descriptor_file(self.file, self.datastore)
            self.display_bilan_upload_file(d_res)

        if "metadata" in self.data:
            Config().om.info("Téléversement de métadonnées...", green_colored=True)
            d_res = self.upload_metadata_from_descriptor_file(self.file, self.datastore)
            self.display_bilan_upload_file(d_res)

        if "key" in self.data:
            Config().om.info("Création de clefs...", green_colored=True)
            d_res = self.create_key_from_file(self.file)
            self.display_bilan_creation(d_res)

    @staticmethod
    def upload_from_descriptor_file(
        file: Union[Path, str],
        behavior: Optional[str] = None,
        datastore: Optional[str] = None,
        check_before_close: bool = False,
        mode_cartes: Optional[bool] = None,
        callback: Optional[Callable[[str], None]] = print,
        ctrl_c_action: Optional[Callable[[], bool]] = Utils.ctrl_c_upload,
    ) -> Dict[str, Any]:
        """réalisation des livraisons (upload) décrites par le fichier indiqué

        Args:
            file (Union[Path, str]): chemin du fichier descripteur de livraison
            behavior (Optional[str]): comportement dans le cas où une livraison de même nom existe, comportment par défaut si None
            datastore (Optional[str]): datastore à utilisé, datastore par défaut si None
            check_before_close (bool): Vérification de l'arborescence de la livraison avant fermeture.
            mode_cartes (Optional[bool]): Si le mode carte est activé
            callback (Optional[Callable[[str], None]]): fonction de callback à exécuter avec le message de suivi.
            ctrl_c_action (Optional[Callable[[], bool]]): gestion du ctrl-C

        Returns:
            Dict[str, Any]: dictionnaire avec le résultat des livraisons :
                "ok" : liste des livraisons sans problèmes
                "upload_fail": dictionnaire {nom livraison : erreur remontée lors de la livraison}
                "check_fail": liste des livraisons dont les vérifications ont échoué
        """
        o_dfu = UploadDescriptorFileReader(Path(file))
        s_behavior = str(behavior).upper() if behavior is not None else None

        l_uploads: List[Upload] = []  # liste des uploads lancées
        d_upload_fail: Dict[str, Exception] = {}  # dictionnaire upload : erreur des uploads qui ont fail
        l_check_ko: List[Upload] = []  # liste des uploads dont les vérifications plantes

        # on fait toutes les livraisons
        Config().om.info(f"LIVRAISONS : ({len(o_dfu.datasets)})", green_colored=True)
        for o_dataset in o_dfu.datasets:
            s_nom = o_dataset.upload_infos["name"]
            Config().om.info(f"{Color.BLUE} * {s_nom}{Color.END}")
            try:
                o_ua = UploadAction(o_dataset, compatibility_cartes=mode_cartes, behavior=s_behavior)
                o_upload = o_ua.run(datastore, check_before_close=check_before_close)
                l_uploads.append(o_upload)
            except Exception as e:
                s_nom = o_dataset.upload_infos["name"]
                d_upload_fail[s_nom] = e
                Config().om.error(f"livraison {s_nom} : {e}")
                Config().om.debug(traceback.format_exc())

        # vérification des livraisons
        Config().om.info("Fin des livraisons.", green_colored=True)
        Config().om.info("Suivi des vérifications :", green_colored=True)
        l_check_ko = []
        l_check_ok = []
        for o_upload in l_uploads:
            Config().om.info(f"{Color.BLUE} * {o_upload}{Color.END}")
            b_res = Utils.monitoring_upload(
                o_upload,
                "Livraison {upload} créée avec succès.",
                "Livraison {upload} créée en erreur !",
                callback,
                ctrl_c_action,
                mode_cartes,
            )
            if b_res:
                l_check_ok.append(o_upload)
            else:
                l_check_ko.append(o_upload)
        Config().om.info("Fin des vérifications.", green_colored=True)

        return {
            "ok": l_check_ok,
            "upload_fail": d_upload_fail,
            "check_fail": l_check_ko,
        }

    @staticmethod
    def display_bilan_upload_file(d_res: Dict[str, Any]) -> None:
        """Affichage du bilan pour le téléversement de fichiers (annexe, static, metadata)

        Args:
            d_res (Dict[str, Any]): dictionnaire de résultat {'ok': liste des livraisons ok, 'upload_fail': dictionnaire 'fichier': erreur}
        """
        if d_res["upload_fail"]:
            Config().om.info("RÉCAPITULATIF DES PROBLÈMES :", green_colored=True)
            if d_res["upload_fail"]:
                Config().om.error(f"{len(d_res['upload_fail'])} téléversements échoués :\n" + "\n".join([f" * {s_nom} : {e_error}" for s_nom, e_error in d_res["upload_fail"].items()]))
            Config().om.error(f"BILAN : {len(d_res['ok'])} téléversements effectués sans erreur, {len(d_res['upload_fail'])} téléversements échouées")
            sys.exit(1)
        else:
            Config().om.info(f"BILAN : les {len(d_res['ok'])} téléversements se sont bien passées", green_colored=True)

    @staticmethod
    def upload_annexe_from_descriptor_file(file: Union[Path, str], datastore: Optional[str] = None) -> Dict[str, Any]:
        """réalisation des livraisons  d'annexe décrites par le fichier indiqué

        Args:
            file (Union[Path, str]): chemin du fichier descripteur de livraison d'annexes
            datastore (Optional[str]): datastore à utiliser, datastore par défaut si None

        Returns:
            Dict[str, Any]: dictionnaire avec le résultat de la livraison des annexes :
                "ok" : liste des annexes livrées sans problèmes
                "upload_fail": dictionnaire {nom annexe : erreur remontée lors de la livraison de l'annexe}
        """
        o_dfu = DescriptorFileReader(Path(file), "annexe")

        l_uploads: List[Annexe] = []  # liste des uploads effectué
        d_upload_fail: Dict[str, Exception] = {}  # dictionnaire "fichier archive" : erreur des uploads qui ont fail

        # on fait toutes les livraisons
        Config().om.info(f"LIVRAISON DES ARCHIVES : ({len(o_dfu.data)})", green_colored=True)
        for d_data in o_dfu.data:
            s_nom = d_data["file"]
            Config().om.info(f"{Color.BLUE} * {s_nom}{Color.END}")
            try:
                o_upload = Annexe.api_create(d_data, route_params={"datastore": datastore})
                l_uploads.append(o_upload)
            except Exception as e:
                d_upload_fail[s_nom] = e
                Config().om.debug(traceback.format_exc())
                Config().om.error(f"livraison {s_nom} : {e}")

        # vérification des livraisons
        Config().om.info("Fin des livraisons.", green_colored=True)
        return {"ok": l_uploads, "upload_fail": d_upload_fail}

    @staticmethod
    def upload_static_from_descriptor_file(file: Union[Path, str], datastore: Optional[str] = None) -> Dict[str, Any]:
        """réalisation des livraisons de fichier statique décrites par le fichier indiqué

        Args:
            file (Union[Path, str]): chemin du fichier descripteur de livraisons de fichier statique
            datastore (Optional[str]): datastore à utilisé, datastore par défaut si None

        Returns:
            Dict[str, Any]: dictionnaire avec le résultat des livraisons :
                "ok" : liste des livraisons sans problèmes
                "upload_fail": dictionnaire {nom fichier statique : erreur remontée lors de la livraison du fichier statique}
        """
        o_dfu = DescriptorFileReader(Path(file), "static")

        l_uploads: List[Static] = []  # liste des uploads effectué
        d_upload_fail: Dict[str, Exception] = {}  # dictionnaire "fichier statique" : erreur des uploads qui ont fail

        # on fait toutes les livraisons
        Config().om.info(f"LIVRAISON DES FICHIERS STATIQUES : ({len(o_dfu.data)})", green_colored=True)
        for d_data in o_dfu.data:
            s_nom = d_data["file"]
            Config().om.info(f"{Color.BLUE} * {s_nom}{Color.END}")
            try:
                o_upload = Static.api_create(d_data, route_params={"datastore": datastore})
                l_uploads.append(o_upload)
            except Exception as e:
                d_upload_fail[s_nom] = e
                Config().om.debug(traceback.format_exc())
                Config().om.error(f"livraison {s_nom} : {e}")

        # vérification des livraisons
        Config().om.info("Fin des livraisons.", green_colored=True)
        return {"ok": l_uploads, "upload_fail": d_upload_fail}

    @staticmethod
    def upload_metadata_from_descriptor_file(file: Union[Path, str], datastore: Optional[str] = None) -> Dict[str, Any]:
        """réalisation des livraisons de métadonnée décrites par le fichier indiqué

        Args:
            file (Union[Path, str]): chemin du fichier descripteur de livraisons de métadonnée
            datastore (Optional[str]): datastore à utiliser, datastore par défaut si None

        Returns:
            Dict[str, Any]: dictionnaire avec le résultat des livraisons des fichiers de métadonnée :
                "ok" : liste des livraisons de métadonnées réussies,
                "upload_fail": dictionnaire {nom métadonnée : erreur remontée lors de la livraison de la métadonnée}
        """
        o_dfu = DescriptorFileReader(Path(file), "metadata")

        l_uploads: List[Metadata] = []  # liste des uploads effectué
        d_upload_fail: Dict[str, Exception] = {}  # dictionnaire "fichier statique" : erreur des uploads qui ont fail

        # on fait toutes les livraisons
        Config().om.info(f"LIVRAISON DES FICHIERS DE MÉTADONNÉES : ({len(o_dfu.data)})", green_colored=True)
        for d_data in o_dfu.data:
            s_nom = d_data["file"]
            Config().om.info(f"{Color.BLUE} * {s_nom}{Color.END}")
            try:
                o_upload = Metadata.api_create(d_data, route_params={"datastore": datastore})
                l_uploads.append(o_upload)
            except Exception as e:
                d_upload_fail[s_nom] = e
                Config().om.debug(traceback.format_exc())
                Config().om.error(f"livraison {s_nom} : {e}")

        # vérification des livraisons
        Config().om.info("Fin des livraisons.", green_colored=True)
        return {"ok": l_uploads, "upload_fail": d_upload_fail}

    @staticmethod
    def create_key_from_file(file: Union[str, Path]) -> Dict[str, Any]:
        """création des clefs décrites par le fichier indiqué

        Args:
            file (Union[Path, str]): chemin du fichier descripteur des clefs

        Returns:
            Dict[str, Any]: dictionnaire avec le résultat des créations de clefs :
                "ok" : liste des clefs créées sans problèmes
                "fail": dictionnaire {nom clef : erreur remontée lors de la création}
        """

        l_data = JsonHelper.load(Path(file), file_not_found_pattern="Fichier descripteur de création {json_path} non trouvé.")["key"]

        l_keys: List[Key] = []
        d_fail: Dict[str, Exception] = {}

        # on fait toutes les livraisons
        Config().om.info(f"CRÉATION DES CLEFS : ({len(l_data)})", green_colored=True)
        for d_data in l_data:
            s_nom = d_data["name"]
            Config().om.info(f"{Color.BLUE} * {s_nom}{Color.END}")
            try:
                o_upload = Key.api_create(d_data)
                l_keys.append(o_upload)
            except Exception as e:
                d_fail[s_nom] = e
                Config().om.debug(traceback.format_exc())
                Config().om.error(f"clef {s_nom} : {e}")

        # vérification des livraisons
        Config().om.info("Fin de la création.", green_colored=True)
        return {"ok": l_keys, "fail": d_fail}

    @staticmethod
    def display_bilan_creation(d_res: Dict[str, Any]) -> None:
        """Affichage du bilan pour la création d'entité (key)

        Args:
            d_res (Dict[str, Any]): dictionnaire de résultat {'ok': liste des creation ok, 'fail': dictionnaire 'fichier': erreur}
        """
        if d_res["fail"]:
            Config().om.info("RÉCAPITULATIF DES PROBLÈMES :", green_colored=True)
            Config().om.error(f"{len(d_res['fail'])} création échouées :\n" + "\n".join([f" * {s_nom} : {e_error}" for s_nom, e_error in d_res["fail"].items()]))
            Config().om.error(f"BILAN : {len(d_res['ok'])} creation effectués sans erreur, {len(d_res['fail'])} creation échouées")
            sys.exit(1)
        else:
            Config().om.info(f"BILAN : les {len(d_res['ok'])} créations se sont bien passées", green_colored=True)
