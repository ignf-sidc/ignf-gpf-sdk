from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester


class LogsInterface(StoreEntity):
    """Interface de StoreEntity pour gérer les logs (logs)."""

    def api_logs(self) -> str:
        """Récupère les logs de cette entité sur l'API.

        Returns:
            str: les logs récupérés
        """
        # Génération du nom de la route
        s_route = f"{self._entity_name}_logs"
        # Requête "get"
        o_response = ApiRequester().route_request(
            s_route,
            route_params={"datastore": self.datastore, self._entity_name: self.id},
        )
        s_log = ""
        try:
            # Les logs sont une liste de string, on concatène tout
            s_log = "\n".join(o_response.json())
        except Exception:
            pass
        return s_log
