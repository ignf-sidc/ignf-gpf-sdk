from typing import Any, Dict, Optional
from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.Errors import ConflictError


class ConfigurationAction(ActionAbstract):
    """Classe dédiée à la création des Configuration.

    Attributes:
        __workflow_context (str): nom du context du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __configuration (Optional[Configuration]): représentation Python de la configuration créée
    """

    def __init__(
        self, workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional["ActionAbstract"] = None, behavior: Optional[str] = None, compatibility_cartes: Optional[bool] = None
    ) -> None:
        super().__init__(workflow_context, definition_dict, parent_action)
        # Autres attributs
        self.__configuration: Optional[Configuration] = None
        # comportement (écrit dans la ligne de commande par l'utilisateur), sinon celui par défaut (dans la config) qui vaut CONTINUE
        self.__behavior: str = behavior if behavior is not None else Config().get_str("configuration", "behavior_if_exists")
        self.__mode_cartes: Optional[bool] = compatibility_cartes if compatibility_cartes is not None else Config().get_bool("compatibility_cartes", "activate")

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Création et complétion d'une configuration...", force_flush=True)
        # Création de la Configuration
        self.__create_configuration(datastore)
        # Ajout des tags sur la Configuration
        self.__add_tags()
        # Ajout des commentaires sur la Configuration
        self.__add_comments()
        # Affichage
        Config().om.info(f"Configuration créée et complétée : {self.configuration}")
        Config().om.info("Création et complétion d'une configuration : terminé")

    def __create_configuration(self, datastore: Optional[str]) -> None:
        """Création de la Configuration sur l'API à partir des paramètres de définition de l'action.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        """
        # On regarde si on trouve quelque chose avec la fonction find
        o_configuration = self.find_configuration(datastore)
        if o_configuration is not None:
            if self.__behavior == self.BEHAVIOR_STOP:
                raise GpfSdkError(f"Impossible de créer la configuration, une configuration équivalente {o_configuration} existe déjà.")
            if self.__behavior == self.BEHAVIOR_DELETE:
                Config().om.warning(f"Une donnée configuration équivalente à {o_configuration} va être supprimée puis recréée.")
                # Suppression de la donnée stockée
                o_configuration.api_delete()
                # on force à None pour que la création soit faite
                self.__configuration = None
            # Comportement "on continue l'exécution"
            elif self.__behavior == self.BEHAVIOR_CONTINUE:
                Config().om.info(f"Configuration {o_configuration} déjà existante, complétion uniquement.")
                self.__configuration = o_configuration
                return
            else:
                raise GpfSdkError(
                    f"Le comportement {self.__behavior} n'est pas reconnu ({self.BEHAVIOR_STOP}|{self.BEHAVIOR_DELETE}|{self.BEHAVIOR_CONTINUE}), l'exécution de traitement n'est pas possible."
                )
        # Création en gérant une erreur de type ConflictError (si la Configuration existe déjà selon les critères de l'API)
        try:
            Config().om.info("Création de la configuration...", force_flush=True)
            self.__configuration = Configuration.api_create(self.definition_dict["body_parameters"], route_params={"datastore": datastore})
            Config().om.info(f"Configuration {self.__configuration['name']} créée avec succès.")
        except ConflictError as e:
            raise StepActionError(f"Impossible de créer la configuration il y a un conflict : \n{e.message}") from e

    def __add_tags(self) -> None:
        """Ajout des tags sur la Configuration."""
        if not self.configuration or not self.definition_dict:
            # uniquement pour le type, dans les fait le programme sort en erreur avant d'arivé ici
            return
        if self.__mode_cartes and "datasheet_name" not in self.definition_dict.get("tags", {}):
            # tag datasheet_name obligatoire en mode cartes
            raise GpfSdkError("Mode compatibility_cartes activé, il faut obligatoirement définir le tag 'datasheet_name'")
        # on vérifie que la configuration et definition_dict ne sont pas null et on vérifie qu'il y'a bien une clé tags
        if self.definition_dict.get("tags"):
            Config().om.info(f"Configuration {self.configuration['name']} : ajout des {len(self.definition_dict['tags'])} tags...")
            self.configuration.api_add_tags(self.definition_dict["tags"])
            Config().om.info(f"Configuration {self.configuration['name']} : les {len(self.definition_dict['tags'])} tags ont été ajoutés avec succès.")

    def __add_comments(self) -> None:
        """Ajout des commentaires sur la Configuration."""
        # on vérifie que la configuration et definition_dict ne sont pas null et on vérifie qu'il y'a bien une clé comments
        if self.configuration and self.definition_dict and "comments" in self.definition_dict and self.definition_dict["comments"] != {}:
            # récupération des commentaires déjà ajoutés
            l_actual_comments = [d_comment["text"] for d_comment in self.configuration.api_list_comments() if d_comment]
            Config().om.info(f"Configuration {self.configuration['name']} : ajout des {len(self.definition_dict['comments'])} commentaires...")
            for s_comment in self.definition_dict["comments"]:
                # si le commentaire n'existe pas déjà on l'ajoute
                if s_comment not in l_actual_comments:
                    self.configuration.api_add_comment({"text": s_comment})
            Config().om.info(f"Configuration {self.configuration['name']} : les {len(self.definition_dict['comments'])} commentaires ont été ajoutés avec succès.")

    def find_configuration(self, datastore: Optional[str]) -> Optional[Configuration]:
        """Fonction permettant de récupérer une Configuration ressemblant à celle qui devrait être créée
        en fonction des filtres définis dans la Config.

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        Returns:
            configuration retrouvée
        """
        # Récupération des critères de filtre
        d_infos, d_tags = ActionAbstract.get_filters("configuration", self.definition_dict["body_parameters"], self.definition_dict.get("tags", {}))
        # On peut maintenant filtrer les stored data selon ces critères
        l_configuration = Configuration.api_list(infos_filter=d_infos, tags_filter=d_tags, datastore=datastore)
        # S'il y a une ou plusieurs, on retourne la 1ère :
        if l_configuration:
            return l_configuration[0]
        # sinon on retourne None
        return None

    @property
    def configuration(self) -> Optional[Configuration]:
        return self.__configuration
