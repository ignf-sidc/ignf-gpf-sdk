import time
from typing import Any, Dict, Optional

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.Errors import ConflictError


class OfferingAction(ActionAbstract):
    """Classe dédiée à la création des Offering.

    Attributes:
        __workflow_context (str): nom du contexte du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __offering (Optional[Offering]): représentation Python de la Offering créée
    """

    def __init__(self, workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional["ActionAbstract"] = None, behavior: Optional[str] = None) -> None:
        super().__init__(workflow_context, definition_dict, parent_action)
        # Autres attributs
        self.__offering: Optional[Offering] = None
        # comportement (écrit dans la ligne de commande par l'utilisateur), sinon celui par défaut (dans la config) qui vaut CONTINUE
        self.__behavior: str = behavior if behavior is not None else Config().get_str("offering", "behavior_if_exists")

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Création d'une offre...")
        # Ajout de l'Offering
        self.__create_offering(datastore)
        # Affichage
        o_offering = self.offering

        # si on n'a pas réussi a trouver/créer l'offering on plante
        if o_offering is None:
            raise StepActionError("Erreur à la création de l'offre.")

        # Récupération des liens
        o_offering.api_update()
        Config().om.info(f"Offre créée : {self.__offering}\n   - " + "\n   - ".join(o_offering.get_url()), green_colored=True)
        # vérification du status.
        Config().om.info("vérification du statut ...")
        while True:
            o_offering.api_update()
            s_status = o_offering["status"]
            if s_status == Offering.STATUS_PUBLISHED:
                Config().om.info("Création d'une offre : terminé")
                break
            if s_status == Offering.STATUS_UNSTABLE:
                raise StepActionError("Création d'une offre : terminé en erreur.")
            # on fixe à 1 seconde, normalement quasiment instantané
            time.sleep(1)

    def __create_offering(self, datastore: Optional[str]) -> None:
        """Création de l'Offering sur l'API à partir des paramètres de définition de l'action.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        """
        o_offering = self.find_offering(datastore)
        if o_offering is not None:
            if self.__behavior == self.BEHAVIOR_STOP:
                raise GpfSdkError(f"Impossible de créer l'offre, une offre équivalente {o_offering} existe déjà.")
            if self.__behavior == self.BEHAVIOR_DELETE:
                Config().om.warning(f"Une donnée offre équivalente à {o_offering} va être supprimée puis recréée.")
                # Suppression de la donnée stockée
                o_offering.api_delete()
                Config().om.debug("Offre supprimée.")
                # on force à None pour que la création soit faite
                self.__offering = None
            # Comportement "on continue l'exécution"
            elif self.__behavior == self.BEHAVIOR_CONTINUE:
                Config().om.info(f"Offre {o_offering} déjà existante, complétion uniquement.")
                self.__offering = o_offering
                return
            else:
                raise GpfSdkError(
                    f"Le comportement {self.__behavior} n'est pas reconnu ({self.BEHAVIOR_STOP}|{self.BEHAVIOR_DELETE}|{self.BEHAVIOR_CONTINUE}), l'exécution de traitement n'est pas possible."
                )
        # Création en gérant une erreur de type ConflictError (si la Configuration existe déjà selon les critères de l'API)
        try:
            self.__offering = Offering.api_create(self.definition_dict["body_parameters"], route_params={"datastore": datastore, **self.definition_dict["url_parameters"]})
        except ConflictError as e:
            raise StepActionError(f"Impossible de créer l'offre il y a un conflict : \n{e.message}") from e

    def find_configuration(self, datastore: Optional[str] = None) -> Optional[Configuration]:
        """Fonction permettant de récupérer la Configuration associée à l'Offering qui doit être crée par cette Action.

        C'est à dire la Configuration indiquée dans `url_parameters` du `definition_dict` de cette Action.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        Returns:
            Configuration
        """
        # Récupération de l'id de la configuration et du endpoint
        s_configuration_id = self.definition_dict["url_parameters"]["configuration"]
        # Instanciation Configuration
        o_configuration = Configuration.api_get(s_configuration_id, datastore=datastore)
        # Retour
        return o_configuration

    def find_offering(self, datastore: Optional[str] = None) -> Optional[Offering]:
        """Fonction permettant de récupérer l'Offering qui devrait être créée (si elle existe déjà).

        C'est à dire une offering associée à la Configuration indiquée dans `url_parameters` et au endpoint indiqué dans `body_parameters`.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        Returns:
            Offre retrouvée
        """
        # Récupération de l'id de la configuration et du endpoint
        s_configuration_id = self.definition_dict["url_parameters"]["configuration"]
        s_endpoint_id = self.definition_dict["body_parameters"]["endpoint"]
        # Instanciation Configuration
        o_configuration = Configuration.api_get(s_configuration_id, datastore=datastore)
        # Listing des Offres associées à cette Configuration
        l_offerings = o_configuration.api_list_offerings()
        # Pour chaque offering
        for o_offering in l_offerings:
            # On récupère toutes les infos
            o_offering.api_update()
            # On regarde si elle est associée au bon endpoint
            if o_offering["endpoint"]["_id"] == s_endpoint_id:
                # On a notre offering, on sort !
                return o_offering
        # sinon on retourne None
        return None

    @property
    def offering(self) -> Optional[Offering]:
        return self.__offering
