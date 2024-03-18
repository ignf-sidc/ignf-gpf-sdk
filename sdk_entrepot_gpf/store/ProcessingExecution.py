from datetime import datetime
from typing import Optional

from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.CsfInterface import CsfInterface
from sdk_entrepot_gpf.store.interface.LogsInterface import LogsInterface
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester


class ProcessingExecution(CsfInterface, LogsInterface, StoreEntity):
    """Classe Python représentant l'entité ProcessingExecution (exécution d'un traitement).

    Cette classe permet d'effectuer les actions spécifiques liées aux exécution de traitement : création,
    lancement, gestion de l'exécution, récupération du log, etc.
    """

    _entity_name = "processing_execution"
    _entity_title = "exécution d'un traitement"

    STATUS_CREATED = "CREATED"
    STATUS_WAITING = "WAITING"
    STATUS_PROGRESS = "PROGRESS"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILURE = "FAILURE"
    STATUS_ABORTED = "ABORTED"

    def api_launch(self) -> None:
        """Lance l'exécution du traitement sur l'API."""
        # Génération du nom de la route
        s_route = f"{self._entity_name}_launch"

        # Requête
        ApiRequester().route_request(
            s_route,
            method=ApiRequester.POST,
            route_params={self._entity_name: self.id, "datastore": self.datastore},
        )

    def api_abort(self) -> None:
        """Annule l'exécution du traitement sur l'API."""
        # Génération du nom de la route
        s_route = f"{self._entity_name}_abort"

        # Requête
        ApiRequester().route_request(
            s_route,
            method=ApiRequester.POST,
            route_params={self._entity_name: self.id, "datastore": self.datastore},
        )

    @property
    def launch(self) -> Optional[datetime]:
        """Récupère la datetime de lancement de l'exécution du traitement.

        Returns:
            datetime: datetime de lancement de l'exécution du traitement
        """
        return self._get_datetime("launch")
