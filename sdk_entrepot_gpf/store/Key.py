from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.interface.PartialEditInterface import PartialEditInterface
from sdk_entrepot_gpf.store.interface.ReUploadFileInterface import ReUploadFileInterface
from sdk_entrepot_gpf.store.interface.DownloadInterface import DownloadInterface


class Key(DownloadInterface, PartialEditInterface, ReUploadFileInterface, StoreEntity):
    """Classe Python représentant l'entité Clef (key).

    Cette classe permet d'effectuer les actions spécifiques liées aux clefs : création,
    remplacement, mise à jour, suppression.
    """

    _entity_name = "key"
    _entity_title = "clef"

    TYPE_HASH = "HASH"
    TYPE_HEADER = "HEADER"
    TYPE_BASIC = "BASIC"
    TYPE_OAUTH2 = "OAUTH2"
