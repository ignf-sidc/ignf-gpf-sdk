from typing import List
from sdk_entrepot_gpf.store.Errors import StoreEntityError
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

    def api_logs_filter(self, substring: str) -> List[str]:
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
        result: List[str] = []
        for line in l_logs:
            if line.__contains__(substring):
                result.append(line)
        return result

    def api_logs_pages_filter(self, first_page: int = 1, last_page: int = 0, line_per_page: int = 1000, filter: str = "") -> List[str]:
        s_route = f"{self._entity_name}_logs"
        # stockage de la liste des logs
        l_logs: List[str] = []
        o_response = ApiRequester().route_request(
            s_route,
            route_params={"datastore": self.datastore, self._entity_name: self.id},
            params={"page": 1, "limit": line_per_page},
        )
        # On récupère le nombre de page en fonction du nombre de ligne par page.
        i_total_page = ApiRequester.range_total_page(o_response.headers.get("Content-Range"), line_per_page)
        print(i_total_page)
        if abs(first_page) > i_total_page + 1:
            raise StoreEntityError("La première page est en dehors des limites " + str(i_total_page))
        if abs(last_page) > i_total_page + 1:
            raise StoreEntityError("La dernière page est en dehors des limites " + str(i_total_page))
        # On initialise la première page
        if first_page > 0:
            i_firstpage = first_page
        elif first_page < 0:
            i_firstpage = i_total_page + first_page
        else:
            i_firstpage = 1
        # On initialise la dernière page
        if last_page > 0:
            i_lastpage = last_page
        elif last_page < 0:
            i_lastpage = i_total_page + last_page
        else:
            i_lastpage = i_total_page
        print(i_firstpage)
        print(i_lastpage)
        if i_firstpage > i_lastpage:
            raise StoreEntityError("La dernière page doit être superieur a la première")

        # on récupère les pages souhaitées
        while i_firstpage <= i_lastpage:
            # On liste les entités à la bonne page
            o_response = ApiRequester().route_request(
                s_route,
                route_params={"datastore": self.datastore, self._entity_name: self.id},
                params={"page": i_firstpage, "limit": line_per_page},
            )
            # On les ajoute à la liste
            l_logs += o_response.json()
            # On passe à la page suivante
            i_firstpage += 1
        l_result: List[str] = []
        for s_line in l_logs:
            if filter in s_line or filter == "":
                l_result.append(s_line)
        return l_result
