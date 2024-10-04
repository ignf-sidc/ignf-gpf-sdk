from typing import Optional
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.ConfigurationAction import ConfigurationAction


class CopyConfigurationAction(ConfigurationAction):
    """Classe dédiée à la copie des Configuration.

    Attributes:
        __workflow_context (str): nom du context du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __configuration (Optional[Configuration]): représentation Python de la configuration créée
    """

    def run(self, datastore: Optional[str] = None) -> None:
        # test d'on a bien les nouvelles valeurs de name et layer_name dans body_parameters
        if "body_parameters" not in self.definition_dict or "layer_name" not in self.definition_dict["body_parameters"] or "name" not in self.definition_dict["body_parameters"]:
            raise StepActionError('Les clefs "name" et "layer_name" sont obligatoires dans "body_parameters"')

        Config().om.info("Récupération du paramétrage de l'ancienne configuration...", force_flush=True)
        # on récupère la configuration à copier
        o_base_config = Configuration.api_get(self.definition_dict["url_parameters"]["configuration"], datastore=datastore)
        # stockage de l'ancien body_parameters
        d_parameter = {**self.definition_dict["body_parameters"]}
        # mise à jour de body_parameters pour la nouvelle configuration
        self.definition_dict["body_parameters"] = {**o_base_config.get_store_properties(), **d_parameter}

        # lancement de la création
        super().run(datastore)
