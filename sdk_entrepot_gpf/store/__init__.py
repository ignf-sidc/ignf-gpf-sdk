"""Classes représentant les entités de l'Entrepôt."""

from sdk_entrepot_gpf.store.Annexe import Annexe
from sdk_entrepot_gpf.store.Check import Check
from sdk_entrepot_gpf.store.CheckExecution import CheckExecution
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.Datastore import Datastore
from sdk_entrepot_gpf.store.Endpoint import Endpoint
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.Processing import Processing
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.store.Static import Static
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Tms import Tms
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.User import User
from sdk_entrepot_gpf.store.Access import Access
from sdk_entrepot_gpf.store.Key import Key
from sdk_entrepot_gpf.store.Permission import Permission

# lien entre le nom/type texte et la classe
TYPE__ENTITY = {
    Annexe.entity_name(): Annexe,
    Check.entity_name(): Check,
    CheckExecution.entity_name(): CheckExecution,
    Configuration.entity_name(): Configuration,
    Datastore.entity_name(): Datastore,
    Endpoint.entity_name(): Endpoint,
    Offering.entity_name(): Offering,
    Processing.entity_name(): Processing,
    ProcessingExecution.entity_name(): ProcessingExecution,
    Static.entity_name(): Static,
    StoredData.entity_name(): StoredData,
    Tms.entity_name(): Tms,
    Upload.entity_name(): Upload,
    User.entity_name(): User,
    Access.entity_name(): Access,
    Key.entity_name(): Key,
    Permission.entity_name(): Permission,
}
