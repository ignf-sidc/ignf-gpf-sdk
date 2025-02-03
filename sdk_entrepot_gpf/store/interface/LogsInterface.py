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

    def api_logs_filter(self, substring : str) -> List[str]:
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
        result : List[str] = []
        for line in l_logs:
            if(line.__contains__(substring)):
                result.append(line)
        return result

    def api_logs_pages_filter(self, first_page: int = 1, last_page: int = 0, line_per_page: int = 1000, filter : str = "") -> List[str]:
        s_route = f"{self._entity_name}_logs"
        # stockage de la liste des logs
        l_logs: List[str] = []

        o_response = ApiRequester().route_request(
                s_route,
                route_params={"datastore": self.datastore, self._entity_name: self.id},
                params={"page": 1, "limit": line_per_page},
            )
        #On récupère le nombre de page en fonction du nombre de ligne par page.
        total_page = ApiRequester.range_total_page(o_response.headers.get("Content-Range"), line_per_page)
        i_page = 1
        j_page = total_page
        if not (first_page < 0 and last_page > 0) and last_page > first_page:
            # Numéro de la page
            i_page = total_page + first_page % total_page
            j_page = total_page + last_page % total_page

        # on récupère les pages souhaitées
        while i_page <= j_page:
            # On liste les entités à la bonne page
            o_response = ApiRequester().route_request(
                s_route,
                route_params={"datastore": self.datastore, self._entity_name: self.id},
                params={"page": i_page, "limit": line_per_page},
            )
            # On les ajoute à la liste
            l_logs += o_response.json()
            # On passe à la page suivante
            i_page += 1
        result : List[str] = []
        for line in l_logs:
            if(line.__contains__(filter)):
                result.append(line)
        return result
