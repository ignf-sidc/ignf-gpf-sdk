import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from sdk_entrepot_gpf.helper.DictHelper import DictHelper


class AbstractResolver(ABC):
    """Classe abstraite permettant de résoudre le paramétrage des fichiers d'action.

    Vous pouvez créer vos propres classe de résolution en les héritant de
    celle-ci et en les ajoutant au GlobalResolver.

    Attributes:
        __name (str): nom de code du resolver
    """

    def __init__(self, name: str) -> None:
        super().__init__()
        self.__name: str = name

    @abstractmethod
    def resolve(self, string_to_solve: str, **kwargs: Any) -> str:
        """Résout la chaîne à traiter et retourne la chaîne obtenue.

        Args:
            string_to_solve (str): chaîne à résoudre
            kwargs (Any): paramètres supplémentaires.

        Returns:
            chaîne résolue
        """

    @property
    def name(self) -> str:
        return self.__name

    @staticmethod
    def get(key_value: Dict[str, Any], js_key: str) -> str:
        """Fonction permettant de récupérer une valeur dans un dictionnaire complexe avec une récupération de style JS.
        La valeur est convertie en str (json) si elle n'est pas de type str.

        Args:
            key_value (Dict[str, Any]): dictionnaire dont on veut récupérer l'info
            js_key (str): pattern type JS pour récupérer la valeur du dictionnaire

        Returns:
            str: valeur demandée
        """
        o_val = DictHelper.get(key_value, js_key)
        return o_val if isinstance(o_val, str) else json.dumps(o_val)
