from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.CsfInterface import CsfInterface
from sdk_entrepot_gpf.store.interface.LogsInterface import LogsInterface


class CheckExecution(CsfInterface, LogsInterface, StoreEntity):
    """Classe Python représentant l'entité CheckExecution (exécution d'une vérification)."""

    _entity_name = "check_execution"
    _entity_title = "exécution d'une vérification"

    STATUS_WAITING = "WAITING"
    STATUS_PROGRESS = "PROGRESS"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILURE = "FAILURE"
