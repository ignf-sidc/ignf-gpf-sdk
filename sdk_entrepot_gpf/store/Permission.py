from typing import Any, Dict, List, Optional, Type

from sdk_entrepot_gpf.store.StoreEntity import StoreEntity, T
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.store.interface.PartialEditInterface import PartialEditInterface


class Permission(PartialEditInterface, StoreEntity):
    """Classe Python représentant l'entité des permissions."""

    _entity_name = "permission"
    _entity_title = "permission"

    @classmethod
    def api_create(cls: Type[T], data: Optional[Dict[str, Any]], route_params: Optional[Dict[str, Any]] = None) -> T:
        raise NotImplementedError("Pour les Permissions, utiliser api_create_list")

    @classmethod
    def api_create_list(cls: Type[T], data: Optional[Dict[str, Any]], route_params: Optional[Dict[str, Any]] = None) -> List[T]:
        """Crée une liste de nouvelles entités dans l'API.

        Args:
            data: Données nécessaires pour la création.
            route_params: Paramètres de résolution de la route.

        Returns:
            List[StoreEntity]: Entités créées
        """
        s_datastore: Optional[str] = None
        # Test du dictionnaire route_params
        if isinstance(route_params, dict) and "datastore" in route_params:
            s_datastore = route_params.get("datastore")

        # Génération du nom de la route
        s_route = f"{cls._entity_name}_create"
        # Requête
        o_response = ApiRequester().route_request(
            s_route,
            route_params=route_params,
            method=ApiRequester.POST,
            data=data,
        )
        # Instanciation
        return [cls(x, datastore=s_datastore) for x in o_response.json()]
