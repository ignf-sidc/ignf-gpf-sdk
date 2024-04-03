from typing import Any, Dict, List
from sdk_entrepot_gpf.store.Errors import StoreEntityError

from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.TagInterface import TagInterface
from sdk_entrepot_gpf.store.interface.CommentInterface import CommentInterface
from sdk_entrepot_gpf.store.interface.EventInterface import EventInterface
from sdk_entrepot_gpf.store.interface.FullEditInterface import FullEditInterface
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester


class Configuration(TagInterface, CommentInterface, EventInterface, FullEditInterface, StoreEntity):
    """Classe Python représentant l'entité Configuration (configuration)."""

    _entity_name = "configuration"
    _entity_title = "configuration"

    STATUS_UNPUBLISHED = "UNPUBLISHED"
    STATUS_PUBLISHED = "PUBLISHED"
    STATUS_SYNCHRONIZING = "SYNCHRONIZING"

    def api_list_offerings(self) -> List[Offering]:
        """Liste les Offering liées à cette Configuration.
        Returns:
            List[Offering]: liste des Offering trouvées
        """

        # Génération du nom de la route
        s_route = f"{self._entity_name}_list_offerings"
        # Requête "get"
        o_response = ApiRequester().route_request(
            s_route,
            method=ApiRequester.GET,
            route_params={"datastore": self.datastore, self._entity_name: self.id},
        )
        # Instanciation de chaque élément renvoyé dans la liste
        l_offerings: List[Offering] = [Offering(i, datastore=self.datastore) for i in o_response.json()]

        return l_offerings

    def api_add_offering(self, data_offering: Dict[str, Any]) -> Offering:
        """Ajoute une Offering à cette Configuration.
        Args:
            data_offering (Dict[str, Any]): données pour la création de l'Offering
        Returns:
            Offering: représentation Python de l'Offering créée
        """
        return Offering.api_create(data_offering, route_params={self._entity_name: self.id, "datastore": self.datastore})

    def get_liste_deletable_cascade(self) -> List[StoreEntity]:
        """liste les entités à supprimé lors d'une suppression en cascade de la Configuration en supprimant en cascade les offres liées (et uniquement les offres, pas les données stockées).

        Returns:
            List[StoreEntity]: liste des entités qui seront supprimé
        """
        l_entities: List[StoreEntity] = []
        l_offering = self.api_list_offerings()
        l_entities += l_offering
        l_entities.append(self)
        return l_entities

    def edit(self, data_edit: Dict[str, Any]) -> None:
        """Mise à jour totale de l'entité en fusionnant le nouveau dictionnaire (prioritaire) et l'ancien.
        Pour les configurations, il faut en plus fusionner le sous dictionnaire "type_infos" et la liste "used_data" qu'il contient.
        Si la nouvelle liste et l'ancienne liste n'ont pas la même taille, une exception est levée.

        Args:
            data_edit (Dict[str, Any]): nouvelles valeurs de propriétés
        """
        d_origine_data = self.get_store_properties()

        # fusion de type_infos et de type_infos.used_data
        if "type_infos" in data_edit:  # il peut ne pas y avoir de "type_infos" dans data_edit
            if "used_data" in data_edit["type_infos"]:  # il peut ne pas y avoir de "used_data" dans data_edit["type_infos"]
                l_used_data = []
                if len(d_origine_data["type_infos"]["used_data"]) != len(data_edit["type_infos"]["used_data"]):
                    s_message = "Edition impossible, le nombre de 'used_data' ne correspond pas."
                    raise StoreEntityError(s_message)
                for i in range(len(d_origine_data["type_infos"]["used_data"])):
                    l_used_data.append({**d_origine_data["type_infos"]["used_data"][i], **data_edit["type_infos"]["used_data"][i]})
                data_edit["type_infos"]["used_data"] = l_used_data
            data_edit["type_infos"] = {**d_origine_data["type_infos"], **data_edit["type_infos"]}

        # le reste est géré par la classe parente
        FullEditInterface.edit(self, data_edit)
