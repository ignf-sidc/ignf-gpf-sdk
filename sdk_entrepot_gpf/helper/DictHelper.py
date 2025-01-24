import re
from typing import Dict, Any

from sdk_entrepot_gpf.io.Config import Config


class DictHelper:
    """Classe regroupant les fonctions pour gérer les dictionnaires."""

    @staticmethod
    def get(key_value: Dict[str, Any], js_key: str, raise_error: bool = True) -> Any:
        """Fonction permettant de récupérer une valeur dans un dictionnaire complexe avec une récupération de style JS.

        Args:
            key_value (Dict[str, Any]): dictionnaire dont on veut récupérer l'info
            string (str): pattern type JS pour récupérer la valeur du dictionnaire
            raise_error (bool): raise/logs error or not. Default to True.

        Returns:
            Any: valeur demandée
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
                if raise_error:
                    Config().om.error(f"Impossible de résoudre la clef '{js_key}' : sous-clef '{s_key}' non trouvée, clefs possibles à ce niveau : {', '.join(o_val.keys())}")
                    raise e_error
                return None
        return o_val
