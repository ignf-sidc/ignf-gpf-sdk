from typing import Any, Dict, Optional

from sdk_entrepot_gpf.store.Access import Access
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.Errors import ConflictError


class AccessAction(ActionAbstract):
    """Classe dédiée à la création des accès.

    Attributes:
        __workflow_context (str): nom du contexte du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __access (Optional[Access]): représentation Python de l'accès créé
    """

    def __init__(self, workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional["ActionAbstract"] = None) -> None:
        super().__init__(workflow_context, definition_dict, parent_action)
        # Autres attributs
        # Pour le moment on stocke un booléen indiquant si l'accès a été créé car l'API renvoie une réponse vide...
        # Quand l'API aura évoluée, faire comme pour les autres Actions de création d'entité.
        self.__access_created: Optional[bool] = None
        self.__access: Optional[Access] = None

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Création d'un accès...")
        # Ajout de l'Offering
        self.__create_access(datastore)

        # si on n'a pas réussi à créer l'accès on plante
        if not self.__access_created:  # self.access is None
            raise StepActionError("Erreur à la création de l'accès.")

        # Affichage (TODO : afficher l'accès)
        Config().om.info("Accès créé.", green_colored=True)

    def __create_access(self, datastore: Optional[str]) -> None:
        """Création de l'Access sur l'API à partir des paramètres de définition de l'action.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        """
        # Création en gérant une erreur de type ConflictError (si la Configuration existe déjà selon les critères de l'API)
        try:
            # TODO : self.__access = ...
            self.__access_created = Access.api_create(
                self.definition_dict["body_parameters"],
                route_params={"datastore": datastore, **self.definition_dict["url_parameters"]},
            )
        except ConflictError as e:
            raise StepActionError(f"Impossible de créer l'offre il y a un conflict : \n{e.message}") from e

    @property
    def access(self) -> Optional[Access]:
        return self.__access
