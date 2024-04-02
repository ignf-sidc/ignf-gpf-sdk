import re
import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from sdk_entrepot_gpf.io.Config import Config


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
        """fonction permettant de récupérer une valeur dans un dictionnaire complexe avec une récupération de style JS.
        La valeur est convertie en str (json) si elle n'est pas de type str.

        Args:
            key_value (Dict[str, Any]): dictionnaire dont on veut récupérer l'info
            string (str): pattern type JS pour récupérer la valeur du dictionnaire

        Returns:
            str: valeur demandée
        """
        o_val = key_value
        l_keys = js_key.split(".")
        # On itère selon les morceaux
        for s_key in l_keys:
            try:
                # traitement du cas des array (cle[0], cle[1], cle[-1], ...)
                o_match = re.search(r"(.*)\[(-?\d*)\]$", s_key)
                if o_match:
                    o_val = o_val[o_match.group(1)][int(o_match.group(2))]
                else:
                    o_val = o_val[s_key]
            except KeyError as e_error:
                Config().om.error(f"Impossible de résoudre la clef '{js_key}' : sous-clef '{s_key}' non trouvée, clefs possibles à ce niveau : {', '.join(o_val.keys())}")
                raise e_error
        return o_val if isinstance(o_val, str) else json.dumps(o_val)
