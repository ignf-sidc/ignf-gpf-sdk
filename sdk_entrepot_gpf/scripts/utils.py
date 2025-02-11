import sys
from typing import Callable, Optional

from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store.Upload import Upload


class Utils:
    """Classe proposant des méthodes utilitaires pour les scripts."""

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
