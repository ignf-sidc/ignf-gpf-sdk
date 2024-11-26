from typing import List
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

        # Numéro de la page
        i_page = 1
        # Flag indiquant s'il faut requêter la prochaine page
        b_next_page = True
        # nombre de ligne
        i_limit = 2000
        # stockage de la liste des logs
        l_logs: List[str] = []

        # on veut toutes les pages
        while b_next_page:
            # On liste les entités à la bonne page
            o_response = ApiRequester().route_request(
                s_route,
                route_params={"datastore": self.datastore, self._entity_name: self.id},
                params={"page": i_page, "limit": i_limit},
            )
            # On les ajoute à la liste
            l_logs += o_response.json()
            # On regarde le Content-Range de la réponse pour savoir si on doit refaire une requête pour récupérer la fin
            b_next_page = ApiRequester.range_next_page(o_response.headers.get("Content-Range"), len(l_logs))
            # On passe à la page suivante
            i_page += 1

        # Les logs sont une liste de string, on concatène tout
        return "\n".join(l_logs)
