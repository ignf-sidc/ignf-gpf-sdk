from typing import List, Optional

from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.PartialEditInterface import PartialEditInterface
from sdk_entrepot_gpf.store.interface.ReUploadFileInterface import ReUploadFileInterface
from sdk_entrepot_gpf.store.interface.DownloadInterface import DownloadInterface
from sdk_entrepot_gpf.store.interface.CreatedByUploadFileInterface import CreatedByUploadFileInterface


class Metadata(CreatedByUploadFileInterface, DownloadInterface, PartialEditInterface, ReUploadFileInterface, StoreEntity):
    """Classe Python représentant l'entité Metadonnées (metadata).

    Cette classe permet d'effectuer les actions spécifiques liées aux métadonnées : création,
    remplacement, mise à jour, suppression.
    """

    _entity_name = "metadata"
    _entity_title = "métadonnée"

    @staticmethod
    def publish(file_identifiers: List[str], endpoint_id: str, datastore: Optional[str] = None) -> None:
        """Publie des métadonnées selon leurs fileIdentifier sur un point d'accès METADATA

        Args:
            fileIdentifier (List[str]): liste des fileIdentifier des métadonnées à publier
            endpoint_id (str): id du endpoint METADATA
            datastore (Optional[str], optional): Identifiant du datastore
        """

        # Génération du nom de la route
        s_route = f"{Metadata._entity_name}_publish"

        # Requête
        ApiRequester().route_request(
            s_route,
            route_params={"datastore": datastore},
            data={"file_identifiers": file_identifiers, "endpoint": endpoint_id},
            method=ApiRequester.POST,
        )

    @staticmethod
    def unpublish(file_identifiers: List[str], endpoint_id: str, datastore: Optional[str] = None) -> None:
        """Dépublication des métadonnées selon leurs fileIdentifier sur un point d'accès METADATA

        Args:
            fileIdentifier (List[str]): liste des fileIdentifier des métadonnées à publier
            endpoint_id (str): id du endpoint METADATA
            datastore (Optional[str], optional): Identifiant du datastore
        """

        # Génération du nom de la route
        s_route = f"{Metadata._entity_name}_unpublish"

        # Requête
        ApiRequester().route_request(
            s_route,
            route_params={"datastore": datastore},
            data={"file_identifiers": file_identifiers, "endpoint": endpoint_id},
            method=ApiRequester.POST,
        )

    def __str__(self) -> str:
        # Affichage à destination d'un utilisateur.
        # On affiche l'id et le nom si possible.

        # Liste pour stocker les infos à afficher
        l_infos = []
        # Ajout de l'id
        l_infos.append(f"id={self.id}")
        l_infos.append(f"type={self['type']}")
        l_infos.append(f"file_identifier={self['file_identifier']}")
        # Retour
        return f"{self.__class__.__name__}({', '.join(l_infos)})"
