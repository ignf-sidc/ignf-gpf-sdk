from typing import Any, Dict

from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.resolver.AbstractResolver import AbstractResolver
from sdk_entrepot_gpf.workflow.resolver.Errors import ResolverError


class DictResolver(AbstractResolver):
    """Classe permettant de résoudre des paramètres clé -> valeur.

    Attributes:
        __name (str): nom de code du resolver
        __key_value (Dict[str, Any]): liste des paramètres à résoudre
    """

    def __init__(self, name: str, key_value: Dict[str, Any]) -> None:
        """Classe instanciée grâce au nom du résolveur et à la liste des correspondances à résoudre.

        La clé est la chaîne à remplacer et la valeur la chaîne de remplacement.

        Args:
            name (str): nom du résolveur
            key_value (Dict[str, Any]): liste de clé/valeur à utiliser
        """
        super().__init__(name)
        self.__key_value: Dict[str, Any] = key_value

    def resolve(self, string_to_solve: str, **kwargs: Any) -> str:
        """La chaîne à résoudre doit correspondre à une clef du dictionnaire.

        Args:
            string_to_solve (str): chaîne à résoudre.
            kwargs (Any): paramètres supplémentaires.

        Returns:

        Raises:
            ResolverError: levée si aucune clef ne correspond à la chaîne

        Returns:
            str: chaîne résolue
        """
        # La chaîne à résoudre est en fait la clé, donc il suffit de renvoyer la valeur associée
        try:
            return str(self.get(self.__key_value, string_to_solve))
        except KeyError as e:
            Config().om.error(f"Impossible de résoudre la clef '{string_to_solve}' pour le résolveur '{self.name}', clefs possibles au niveau 1 : {', '.join(self.__key_value.keys())}")
            # Sinon on lève une exception
            raise ResolverError(self.name, string_to_solve) from e
