import os
import configparser
import pathlib
from pathlib import Path
from typing import Any, Iterable, List, Optional, Union

from sdk_entrepot_gpf.pattern.Singleton import Singleton
from sdk_entrepot_gpf.io.OutputManager import OutputManager
from sdk_entrepot_gpf.io.Errors import ConfigReaderError
import toml


class Config(metaclass=Singleton):
    """Lit le fichier de configuration (classe Singleton).
    Attributes:
        __config (dict[str, Any]): full/entière configuration sous forme de dictionnaire
        __ini_file_path (string): Chemin vers le fichier de configuration BaGI
    """

    conf_dir_path = Path(__file__).parent.parent.absolute() / "_conf"
    data_dir_path = Path(__file__).parent.parent.absolute() / "_data"
    ini_file_path = conf_dir_path / "default.ini"

    def __init__(self) -> None:
        """A l'instanciation, le fichier par défaut est lu.

        Il faudra ensuite surcharger les paramètres en lisant d'autres fichiers via la méthode `read`.

        Raises:
            ConfigReaderError: levée si le fichier de configuration par défaut n'est pas trouvé
        """
        self.__output_manager: OutputManager = OutputManager()

        if not Config.ini_file_path.exists():
            raise ConfigReaderError("Fichier de configuration par défaut {ConfigReader.ini_file_path} non trouvé.")

        self.__config: dict[str, Any] = {}
        self.read(Config.ini_file_path)

        # Définition du niveau de log pour l'OutputManager par défaut
        s_level: str = self.get_str("logging", "log_level", "INFO")
        self.__output_manager.set_log_level(s_level)

    def set_output_manager(self, output_manager: Any) -> None:
        self.__output_manager = output_manager

    @property
    def om(self) -> OutputManager:
        return self.__output_manager

    def read(self, filenames: Union[str, Path, Iterable[Union[str, Path]]]) -> List[str]:
        """Permet de surcharger la configuration en lisant un ou plusieurs nouveau(x) fichier(s) de configuration.

        Les derniers fichiers ont la priorité. Si un fichier n'est pas trouvé, aucune erreur n'est levée.
        La fonction retourne la liste des fichiers lus.

        Args:
            filenames (Union[str, Path, Iterable[Union[str, Path]]]): Chemin ou liste des chemins vers le ou les fichier(s) à lire

        Returns:
            liste des fichiers trouvés et lus
        """
        if isinstance(filenames, (str, bytes, os.PathLike)):
            filenames = [filenames]
        # Ouverture des fichiers existants
        configs = []
        read_files = []
        for file_path in filenames:
            if os.path.exists(file_path):
                ext = pathlib.Path(file_path).suffix
                if ext == ".ini":
                    # Fichier ini
                    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
                    config.read(file_path, encoding="utf-8")
                    try:
                        config_1 = {s: dict(config.items(s)) for s in config.sections()}
                    except configparser.InterpolationSyntaxError as e_err:
                        raise ConfigReaderError(f"Veuillez vérifier la config, les caractères spéciaux doivent être doublés. ({e_err.message}) ") from e_err
                    configs.append(config_1)
                    read_files.append(file_path)
                elif ext == ".toml":
                    # Fichier toml
                    config_2 = toml.load(file_path)
                    configs.append(config_2)
                    read_files.append(file_path)
                else:
                    # Fichier non géré
                    raise ValueError(f"L'extension {ext} n'est pas gérée par la classe Config.")
        # Fusion des configurations
        full_config: dict[str, Any] = {}
        for config_3 in configs:
            full_config = Config.merge(full_config, config_3)
        self.__config = full_config

        return read_files

    @staticmethod
    def merge(old: Any, new: Any) -> Any:
        """Fusionne récursivement new dans old avec une priorité sur new.

        Args:
            old (Any): old object
            new (Any): new object

        Returns:
            Any: old surchargé par new
        """

        # new est du même type ou d'un type héritant de old
        if isinstance(new, type(old)):
            if isinstance(old, dict):
                # ce sont des dictionnaires
                merged: dict[str, Any] = old.copy()
                for key, value in new.items():
                    if key in old:
                        merged[key] = Config.merge(old[key], value)
                    else:
                        merged[key] = value
                return merged
            if isinstance(old, list):
                # ce sont des listes
                l_merged: list[set[Any]] = list(set(old + new))
                return l_merged
        # C'est autre chose : on conserve new
        return new

    # TODO à terme supprimer cette fonction
    def get_parser(self) -> configparser.ConfigParser:
        """Retourne le config_parser.

        Returns:
            le config parser
        """
        return self.__config_parser

    def get_config(self) -> dict[str, Any]:
        """Retourne la config entière.

        Returns:
            la full config
        """
        return self.__config

    def get(self, section: str, option: str, fallback: Optional[str] = None) -> Optional[str]:
        """Récupère la valeur associée au paramètre demandé.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[str], optional): valeur par défaut.

        Returns:
            Optional[str]: la valeur du paramètre
        """
        return self.__config.get(section, {option: fallback}).get(option, fallback)

    def get_str(self, section: str, option: str, fallback: Optional[str] = None) -> str:
        """Récupère la valeur du paramètre demandé.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[str], optional): valeur par défaut. Defaults to None.

        Returns:
            Optional[str]: la valeur du paramètre
        """
        ret = self.get(section, option, fallback=fallback)  # type: ignore
        if ret == None:
            return None
        else:
            return str(ret)

    def get_int(self, section: str, option: str, fallback: Optional[int] = None) -> int:
        """Récupère la valeur associée au paramètre demandé, convertie en `int`.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[int], optional): valeur par défaut.

        Returns:
            la valeur du paramètre
        """
        try:
            ret = self.get(section, option, fallback=fallback)  # type: ignore
            if ret == None:
                return None
            else:
                return int(ret)
        except ValueError as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), entier non reconnu. ({e_err.message}) ") from e_err

    def get_float(self, section: str, option: str, fallback: Optional[float] = None) -> float:
        """Récupère la valeur associée au paramètre demandé, convertie en `float`.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[float], optional): valeur par défaut.

        Returns:
            la valeur du paramètre
        """
        try:
            ret = self.get(section, option, fallback=fallback)  # type: ignore
            if ret == None:
                return None
            else:
                return float(ret)
        except ValueError as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), nombre flottant non reconnu. ({e_err.message}) ") from e_err

    def get_bool(self, section: str, option: str, fallback: Optional[bool] = None) -> bool:
        """Récupère la valeur associée au paramètre demandé, convertie en `bool`.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[bool], optional): valeur par défaut.

        Returns:
            la valeur du paramètre
        """
        try:
            ret = self.get(section, option, fallback=fallback)  # type: ignore
            if ret == None:
                return None
            else:
                return bool(ret)
        except TypeError as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), booléen non reconnu. ({e_err.message}) ") from e_err

    def get_temp(self) -> Path:
        """Récupère le chemin racine du dossier temporaire à utiliser.

        Returns:
            chemin racine du dossier temporaire à utiliser
        """
        return Path(self.get_str("miscellaneous", "tmp_workdir"))
