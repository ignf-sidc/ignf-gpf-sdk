from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.PartialEditInterface import PartialEditInterface
from sdk_entrepot_gpf.store.interface.ReUploadFileInterface import ReUploadFileInterface
from sdk_entrepot_gpf.store.interface.DownloadInterface import DownloadInterface
from sdk_entrepot_gpf.store.interface.CreatedByUploadFileInterface import CreatedByUploadFileInterface


class Static(CreatedByUploadFileInterface, DownloadInterface, PartialEditInterface, ReUploadFileInterface, StoreEntity):
    """Classe Python représentant l'entité Fichier statique (static).

    Cette classe permet d'effectuer les actions spécifiques liées aux fichiers statiques : création,
    remplacement, mise à jour, suppression.
    """

    _entity_name = "static"
    _entity_title = "fichier statique"
    _entity_titles = "fichiers statiques"

    TYPE_GEOSERVER_FTL = "GEOSERVER-FTL"
    TYPE_GEOSERVER_STYLE = "GEOSERVER-STYLE"
    TYPE_ROK4_STYLE = "ROK4-STYLE"
    TYPE_DERIVATION_SQL = "DERIVATION-SQL"
