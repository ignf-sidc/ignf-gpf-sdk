import os
import configparser
import pathlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Union
import toml

from sdk_entrepot_gpf.pattern.Singleton import Singleton
from sdk_entrepot_gpf.io.OutputManager import OutputManager
from sdk_entrepot_gpf.io.Errors import ConfigReaderError


class Config(metaclass=Singleton):
    """Lit et compile les fichiers de configuration (classe Singleton).
    Attributes:
        __config (dict[str, Any]): configuration entière sous forme de dictionnaire (sections) de dictionnaires
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
            raise ConfigReaderError(f"Fichier de configuration par défaut {Config.ini_file_path} non trouvé.")

        self.__config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
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
            List[str]: liste des fichiers trouvés et lus
        """
        if isinstance(filenames, (str, bytes, os.PathLike)):
            filenames = [filenames]
        # liste des fichiers lus
        l_read_files = []
        # Ouverture des fichiers existants
        for p_file in filenames:
            if os.path.exists(p_file):
                s_ext = pathlib.Path(p_file).suffix
                if s_ext == ".ini":
                    # Lecture du fichier ini
                    self.__config.read(p_file, encoding="utf-8")
                    # on met à jour la liste des fichiers lus
                    l_read_files.append(str(p_file))
                elif s_ext == ".toml":
                    # Lecture du fichier toml
                    d_config = toml.load(p_file)
                    self.__config.read_dict(d_config, str(p_file))
                    # on met à jour la liste des fichiers lus
                    l_read_files.append(str(p_file))
                else:
                    # Fichier non géré
                    raise ValueError(f"L'extension {s_ext} n'est pas gérée par la classe Config.")

        return l_read_files

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
                d_merged: Dict[str, Any] = old.copy()
                for s_key, o_value in new.items():
                    if s_key in old:
                        d_merged[s_key] = Config.merge(old[s_key], o_value)
                    else:
                        d_merged[s_key] = o_value
                return d_merged
            if isinstance(old, list):
                # ce sont des listes
                l_merged: List[Set[Any]] = list(set(old + new))
                return l_merged
        # C'est d'un autre type : on conserve new
        return new

    def get_config(self) -> Dict[str, Dict[str, Any]]:
        """Retourne la config entière.

        Returns:
            Dict[str, Dict[str, Any]]: la full config
        """
        try:
            d_config = {s: dict(self.__config.items(s)) for s in self.__config.sections()}
        except configparser.InterpolationSyntaxError as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config, les caractères spéciaux doivent être doublés. ({e_err.message}) ") from e_err
        return d_config

    def get(self, section: str, option: str, fallback: Optional[Any] = None) -> Optional[str]:
        """Récupère la valeur associée au paramètre demandé.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[str], optional): valeur par défaut.

        Returns:
            Optional[str]: la valeur du paramètre
        """
        s_fallback = str(fallback) if fallback is not None else fallback
        try:
            s_ret = self.__config.get(section, option, fallback=s_fallback)
        except configparser.InterpolationSyntaxError as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config, les caractères spéciaux doivent être doublés. ({e_err.message}) ") from e_err

        if s_ret is None:
            return None
        return str(s_ret)

    def get_str(self, section: str, option: str, fallback: Optional[str] = None) -> str:
        """Récupère la valeur du paramètre demandé. Si la valeur est None, une exception est levée.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[str], optional): valeur par défaut. Defaults to None.

        Returns:
            str: la valeur du paramètre
        """
        s_ret = self.get(section, option, fallback=fallback)
        if s_ret is None:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), valeur non reconnue.")
        return str(s_ret)

    def get_int(self, section: str, option: str, fallback: Optional[int] = None) -> int:
        """Récupère la valeur associée au paramètre demandé, convertie en `int`. Si la valeur est None, une exception est levée.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[int], optional): valeur par défaut.

        Returns:
            int: la valeur du paramètre
        """
        try:
            s_ret = self.get(section, option, fallback=fallback)
            return int(s_ret)  # type:ignore
        except (ValueError, TypeError) as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), entier non reconnu ({s_ret}). ({e_err}) ") from e_err

    def get_float(self, section: str, option: str, fallback: Optional[float] = None) -> float:
        """Récupère la valeur associée au paramètre demandé, convertie en `float`. Si la valeur est None, une exception est levée.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[float], optional): valeur par défaut.

        Returns:
            float: la valeur du paramètre
        """
        try:
            s_ret = self.get(section, option, fallback=fallback)
            return float(s_ret)  # type:ignore
        except (ValueError, TypeError) as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), nombre flottant non reconnu ({s_ret}). ({e_err}) ") from e_err

    def get_bool(self, section: str, option: str, fallback: Optional[bool] = None) -> bool:
        """Récupère la valeur associée au paramètre demandé, convertie en `bool`. Si la valeur est None, une exception est levée.

        Args:
            section (str): section du paramètre
            option (str): option du paramètre
            fallback (Optional[bool], optional): valeur par défaut.

        Returns:
            bool: la valeur du paramètre
        """
        try:
            s_ret = self.get(section, option, fallback=fallback)
            return bool(s_ret and s_ret.lower() in ["y", "yes", "t", "true", "on", "1", "oui", "o"])
        except (TypeError, TypeError) as e_err:
            raise ConfigReaderError(f"Veuillez vérifier la config ([{section}-[{option}]]), booléen non reconnu ({s_ret}). ({e_err}) ") from e_err

    def get_temp(self) -> Path:
        """Récupère le chemin racine du dossier temporaire à utiliser.

        Returns:
            chemin racine du dossier temporaire à utiliser
        """
        return Path(self.get_str("miscellaneous", "tmp_workdir"))
