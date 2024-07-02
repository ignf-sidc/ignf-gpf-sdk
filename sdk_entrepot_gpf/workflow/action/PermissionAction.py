from typing import Any, Dict, Optional

from sdk_entrepot_gpf.store.Permission import Permission
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.Errors import ConflictError


class PermissionAction(ActionAbstract):
    """Classe dédiée à la création des Permissions.

    Attributes:
        __workflow_context (str): nom du contexte du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __permission (Optional[Permission]): représentation Python de la permission créée
    """

    def __init__(self, workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional["ActionAbstract"] = None) -> None:
        super().__init__(workflow_context, definition_dict, parent_action)
        # Autres attributs
        self.__permission: Optional[Permission] = None

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Création d'une permission...")
        # Création de la permission
        self.__create_permission(datastore)
        Config().om.info(f"Permissions créées : {self.permission}")
        Config().om.info("Création d'une permission : terminée")

    def __create_permission(self, datastore: Optional[str]) -> None:
        """Création de la permission sur l'API à partir des paramètres de définition de l'action.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        """
        # Création en gérant une erreur de type ConflictError (si la Permission existe déjà selon les critères de l'API)
        try:
            self.__permission = Permission.api_create(self.definition_dict["body_parameters"], route_params={"datastore": datastore})
        except ConflictError as e:
            raise StepActionError(f"Impossible de créer la permission il y a un conflict : \n{e.message}") from e

    @property
    def permission(self) -> Optional[Permission]:
        return self.__permission
