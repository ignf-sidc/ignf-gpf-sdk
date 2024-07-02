from typing import Dict, Optional, Type, Any
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester

from sdk_entrepot_gpf.store.StoreEntity import StoreEntity, T
from sdk_entrepot_gpf.store.Errors import StoreEntityError


class Access(StoreEntity):
    """Classe Python représentant l'entité Access (accès)."""

    _entity_name = "Access"
    _entity_title = "accès"

    # On doit redéfinir la fonction car l'API ne renvoie rien... A retirer quand ça sera bon.
    @classmethod
    def api_create(cls: Type[T], data: Optional[Dict[str, Any]], route_params: Optional[Dict[str, Any]] = None) -> bool:  # type:ignore
        """Crée un de nouvel accès dans l'API.

        Args:
            data: Données nécessaires pour la création.
            route_params: Paramètres de résolution de la route.

        Returns:
            bool: True si entité créée
        """
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
        return o_response.status_code == 204

    def api_update(self) -> None:
        return None

    @classmethod
    def api_get(cls: Type[T], id_: str, datastore: Optional[str] = None) -> T:
        raise NotImplementedError("Impossible de récupérer un accès.")

    def api_delete(self) -> None:
        """Supprime l'entité de l'API."""
        raise StoreEntityError("Impossible de supprimer un Access")
