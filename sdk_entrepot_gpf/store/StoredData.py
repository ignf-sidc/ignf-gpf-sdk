from typing import List

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.TagInterface import TagInterface
from sdk_entrepot_gpf.store.interface.EventInterface import EventInterface
from sdk_entrepot_gpf.store.interface.CommentInterface import CommentInterface
from sdk_entrepot_gpf.store.interface.SharingInterface import SharingInterface
from sdk_entrepot_gpf.store.interface.PartialEditInterface import PartialEditInterface


class StoredData(TagInterface, CommentInterface, SharingInterface, EventInterface, PartialEditInterface, StoreEntity):
    """Classe Python représentant l'entité StoredData (donnée stockée)."""

    _entity_name = "stored_data"
    _entity_title = "donnée stockée"
    _entity_titles = "données stockées"
    _entity_fields = "name,type,visibility,srs,status"

    STATUS_CREATED = "CREATED"
    STATUS_GENERATING = "GENERATING"
    STATUS_MODIFYING = "MODIFYING"
    STATUS_GENERATED = "GENERATED"
    STATUS_DELETED = "DELETED"
    STATUS_UNSTABLE = "UNSTABLE"

    def get_liste_deletable_cascade(self) -> List[StoreEntity]:
        """liste les entités à supprimer lors d'une suppression en cascade des configurations liées et des offres liées à chaque configuration.

        Returns:
            List[StoreEntity]: liste des entités qui seront supprimées
        """
        # suppression d'une stored_data : offering et configuration liées puis la stored_data
        l_entities: List[StoreEntity] = []

        # liste des configurations
        l_configuration = Configuration.api_list({"stored_data": self.id})
        for o_configuration in l_configuration:
            # pour chaque configuration on récupère les offerings
            l_offering = o_configuration.api_list_offerings()
            l_entities += l_offering
            l_entities.append(o_configuration)
        # ajout de la stored_data
        l_entities.append(self)
        return l_entities
