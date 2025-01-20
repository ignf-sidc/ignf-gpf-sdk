import sys
from typing import Callable, Optional

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store.Upload import Upload


def monitoring_upload(
    upload: Upload,
    message_ok: str,
    message_ko: str,
    callback: Optional[Callable[[str], None]] = None,
    ctrl_c_action: Optional[Callable[[], bool]] = None,
    mode_cartes: Optional[bool] = None,
) -> bool:
    """Monitoring de l'upload et affichage état de sortie

    Args:
        upload (Upload): upload à monitorer
        message_ok (str): message si les vérifications sont ok
        message_ko (str): message si les vérifications sont en erreur
        callback (Optional[Callable[[str], None]], optional): fonction de callback à exécuter avec le message de suivi.
        ctrl_c_action (Optional[Callable[[], bool]], optional): gestion du ctrl-C
        mode_cartes (Optional[bool]): Si le mode carte est activé
    Returns:
        bool: True si toutes les vérifications sont ok, sinon False
    """
    b_res = UploadAction.monitor_until_end(upload, callback, ctrl_c_action, mode_cartes)
    if b_res:
        Config().om.info(message_ok.format(upload=upload), green_colored=True)
    else:
        Config().om.error(message_ko.format(upload=upload))
    return b_res


def open_upload(upload: Upload) -> None:
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


def close_upload(upload: Upload, mode_cartes: bool) -> None:
    """fermeture d'une livraison

    Args:
        upload (Upload): livraison à fermé
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


def ctrl_c_action() -> bool:
    """fonction callback pour la gestion du ctrl-C
    Renvoie un booléen d'arrêt de traitement. Si True, on doit arrêter le traitement.
    """
    # issues/9 :
    # sortie => sortie du monitoring, ne pas arrêter le traitement
    # stopper l’exécution de traitement => stopper le traitement (et donc le monitoring) [par défaut] (raise une erreur d'interruption volontaire)
    # ignorer / "erreur de manipulation" => reprendre le suivi
    s_response = "rien"
    while s_response not in ["a", "s", "c", ""]:
        Config().om.info(
            "Vous avez taper ctrl-C. Que souhaitez-vous faire ?\n\
                            \t* 'a' : pour sortir et <Arrêter> le traitement [par défaut]\n\
                            \t* 's' : pour sortir <Sans arrêter> le traitement\n\
                            \t* 'c' : pour annuler et <Continuer> le traitement"
        )
        s_response = input().lower()

    if s_response == "s":
        Config().om.info("\t 's' : sortir <Sans arrêter> le traitement")
        sys.exit(0)

    if s_response == "c":
        Config().om.info("\t 'c' : annuler et <Continuer> le traitement")
        return False

    # on arrête le traitement
    Config().om.info("\t 'a' : sortir et <Arrêter> le traitement [par défaut]")
    return True


def ctrl_c_upload() -> bool:
    """fonction callback pour la gestion du ctrl-C
    Renvoie un booléen d'arrêt de traitement. Si True, on doit arrêter le traitement.
    """
    # issues/9 :
    # sortie => sortie du monitoring, ne pas arrêter le traitement
    # stopper l’exécution de traitement => stopper le traitement (et donc le monitoring) [par défaut] (raise une erreur d'interruption volontaire)
    # ignorer / "erreur de manipulation" => reprendre le suivi
    s_response = "rien"
    while s_response not in ["a", "s", "c", ""]:
        Config().om.info(
            "Vous avez taper ctrl-C. Que souhaitez-vous faire ?\n\
                            \t* 'a' : pour sortir et <Arrêter> les vérifications [par défaut]\n\
                            \t* 's' : pour sortir <Sans arrêter> les vérifications\n\
                            \t* 'c' : pour annuler et <Continuer> les vérifications"
        )
        s_response = input().lower()

    if s_response == "s":
        Config().om.info("\t 's' : sortir <Sans arrêter> les vérifications")
        sys.exit(0)

    if s_response == "c":
        Config().om.info("\t 'c' : annuler et <Continuer> les vérifications")
        return False

    # on arrête le traitement
    Config().om.info("\t 'a' : sortir et <Arrêter> les vérifications [par défaut]")
    return True
