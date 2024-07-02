from typing import Dict, List, Optional, Type, Any
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester

from sdk_entrepot_gpf.store.StoreEntity import StoreEntity, T
from sdk_entrepot_gpf.store.Errors import StoreEntityError


class Access(StoreEntity):
    """Classe Python représentant l'entité Access (accès)."""

    _entity_name = "Access"
    _entity_title = "accès"

    # On doit redéfinir la fonction car l'API ne renvoie rien... A retirer quand ça sera bon.
    @classmethod
    def api_create(cls: Type[T], data: Optional[Dict[str, Any]], route_params: Optional[Dict[str, Any]] = None) -> bool:
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

    @classmethod
    def api_list(cls: Type[T], infos_filter: Optional[Dict[str, str]] = None, tags_filter: Optional[Dict[str, str]] = None, page: Optional[int] = None, datastore: Optional[str] = None) -> List[T]:
        """Liste les accès de l'API respectant les paramètres donnés.

        Args:
            infos_filter: Filtres sur les attributs sous la forme `{"nom_attribut": "valeur_attribut"}`
            tags_filter: Filtres sur les tags sous la forme `{"nom_tag": "valeur_tag"}`
            page: Numéro page à récupérer, toutes si None.
            datastore: Identifiant du datastore

        Returns:
            List[T]: liste des entités retournées
        """
        # Gestion des paramètres nuls
        infos_filter = infos_filter if infos_filter is not None else {}
        tags_filter = tags_filter if tags_filter is not None else {}

        # Requête
        o_response = ApiRequester().route_request("datastore_get", route_params={"datastore": datastore})

        # Liste pour stocker les Access correspondants
        l_access: List[T] = []

        # Pour chaque access en dictionnaire
        for d_access in o_response.json():
            # On suppose qu'il est ok
            b_ok = True
            # On vérifie s'il respecte les critères d'attributs (car l'API ne permet pas de filter...)
            for k, v in infos_filter.items():
                if str(d_access.get(k)) != str(v):
                    b_ok = False
                    break
            # S'il est ok au final, on l'ajoute
            if b_ok:
                l_access.append(cls(d_access))
        # A la fin, on renvoie la liste
        return l_access

    def api_update(self) -> None:
        return None

    @classmethod
    def api_get(cls: Type[T], id_: str, datastore: Optional[str] = None) -> T:
        raise NotImplementedError("Impossible de récupérer un accès.")

    def api_delete(self) -> None:
        """Supprime l'entité de l'API."""
        raise StoreEntityError("Impossible de supprimer un Access")
