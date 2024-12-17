from typing import Any, Dict

from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.workflow.resolver.AbstractResolver import AbstractResolver
from sdk_entrepot_gpf.workflow.resolver.Errors import ResolveUserError


class UserResolver(AbstractResolver):
    """Classe permettant de récupérer les informations sur l'utilisateur authentifié.

    La plu-value sur la classe DictRevolver est que les info de l'utilisateur sont
    directement récupérées par le constructeur de la classe (ça évite de gérer cela).

    Attributes :
        __name (str): nom de code du resolver
        __username_data (Dict[str, Any]): liste des infos de l'utilisateur authentifié
    """

    def __init__(self, name: str) -> None:
        """A l'instanciation, on récupère les infos de l'utilisateur via l'API et on les stocke.

        Args:
            name (str): nom du résolveur
        """
        super().__init__(name)
        # On récupère les infos sur l'API
        o_response = ApiRequester().route_request("user_get")
        self.__user_data: Dict[str, Any] = o_response.json()

    def resolve(self, string_to_solve: str, **kwargs: Any) -> Any:
        """Récupération de l'utilisateur courant et récupération d'une des ces informations.

        Args:
            string_to_solve (str): chaîne à résoudre (attribut du JSON retourné)
            kwargs (Any): paramètres supplémentaires.

        Raises:
            ResolveUserError: si l'attribut demandé n'existe pas

        Returns:
            valeur de l'attribut
        """
        # La chaîne à résoudre est en fait la clé, donc il suffit de renvoyer la valeur associée
        try:
            # Si l'utilisateur a demandé la clef "last_name" et qu'elle n'est pas défini,
            if string_to_solve == "last_name" and "last_name" not in self.__user_data:
                # on gère un truc propre pour pas que le tuto pose problème...
                return "last_name"
            # Sinon on renvoi la valeur demandée
            return str(self.get(self.__user_data, string_to_solve))
        except KeyError as e:
            # Sinon on lève une exception
            raise ResolveUserError(self.name, string_to_solve) from e
