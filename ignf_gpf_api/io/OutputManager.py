import logging

from ignf_gpf_api.pattern.Singleton import Singleton
from ignf_gpf_api.io.Color import Color


class OutputManager(metaclass=Singleton):
    """Gestionnaire de sortie."""

    def __init__(self) -> None:
        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel(logging.INFO)

    def debug(self, message: str) -> None:
        """Ajout d'un message de type debug
        Args:
            message (str): message de type debug à journaliser
        """
        self.__logger.debug("DEBUG - %s", message)

    def info(self, message: str, green_colored: bool = False) -> None:
        """Ajout d'un message de type info

        Args:
            message (str): message de type info à journaliser
            green_colored (bool, optional): indique si le message doit être écrit en vert (par défaut False)
        """
        if green_colored is False:
            self.__logger.info("INFO - %s", message)
        else:
            self.__logger.info("%sINFO - %s%s", Color.GREEN, message, Color.END)

    def warning(self, message: str, yellow_colored: bool = True) -> None:
        """Ajout d'un message de type warning
        Args:
            message (str): message de type warning à journaliser
            yellow_colored (bool, optional): indique si le message doit être écrit en jaune (par défaut True)
        """
        if yellow_colored is False:
            self.__logger.warning("ALERTE - %s", message)
        else:
            self.__logger.warning("%sALERTE - %s%s", Color.YELLOW, message, Color.END)

    def error(self, message: str, red_colored: bool = True) -> None:
        """Ajout d'un message de type erreur
        Args:
            message (str): message de type erreur à journaliser
            red_colored (bool, optional): indique si le message doit être écrit en rouge (par défaut False)
        """
        if red_colored is False:
            self.__logger.error("ERREUR - %s", message)
        else:
            self.__logger.error("%sERREUR - %s%s", Color.RED, message, Color.END)

    def critical(self, message: str, red_colored: bool = True) -> None:
        """Ajout d'un message de type critique (apparaît en rouge dans la console)
        Args:
            message (str): message de type critique à journaliser
            red_colored (bool, optional): indique si le message doit être écrit en rouge (par défaut True)
        """
        if red_colored is False:
            self.__logger.critical("ERREUR FATALE - %s", message)
        else:
            self.__logger.critical("%sERREUR FATALE - %s%s", Color.RED, message, Color.END)
