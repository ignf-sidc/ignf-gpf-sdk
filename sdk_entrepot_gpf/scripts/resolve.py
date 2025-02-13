from typing import Dict, Optional

from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.resolver.DateResolver import DateResolver
from sdk_entrepot_gpf.workflow.resolver.DictResolver import DictResolver
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver
from sdk_entrepot_gpf.workflow.resolver.StoreEntityResolver import StoreEntityResolver
from sdk_entrepot_gpf.workflow.resolver.UserResolver import UserResolver


class ResolveCli:
    """Classe pour résoudre des chaînes de caractères via le cli."""

    def __init__(
        self,
        datastore: Optional[str],
        resolve: str,
        params: Dict[str, str],
    ) -> None:
        """Si un id est précisé, on récupère l'entité et on fait d'éventuelles actions.
        Sinon on liste les entités avec éventuellement des filtres.

        Args:
            datastore (Optional[str], optional): datastore à considérer
            resolve (str): chaîne à résoudre
            params (Dict[str, str]): paramètres complémentaires
        """
        self.datastore = datastore
        self.resolve = resolve
        self.params = params

        self.try_resolve()

    @staticmethod
    def init_resolvers(params: Optional[Dict[str, str]]) -> None:
        """Initialise les résolveurs standards.

        Args:
            params (Optional[Dict[str, str]]): clefs-valeurs pour le résolveur "params"
        """
        # Résolveurs basiques
        GlobalResolver().add_resolver(StoreEntityResolver("store_entity"))
        GlobalResolver().add_resolver(UserResolver("user"))
        GlobalResolver().add_resolver(DateResolver("datetime"))
        if params is not None:
            # Résolveur params qui permet d'accéder aux paramètres supplémentaires passés par l'utilisateur
            GlobalResolver().add_resolver(DictResolver("params", params))

    def try_resolve(self) -> None:
        """Lancement de l'étape indiquée."""
        # On définit des résolveurs
        ResolveCli.init_resolvers(self.params)
        # et on résout !
        s_resolved = GlobalResolver().resolve(self.resolve, datastore=self.datastore)
        Config().om.info(f"Chaîne résolue :\n{s_resolved}")
