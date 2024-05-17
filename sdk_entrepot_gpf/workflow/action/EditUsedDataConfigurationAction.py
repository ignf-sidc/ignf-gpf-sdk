from typing import Any, Dict, List, Optional
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract


class EditUsedDataConfigurationAction(ActionAbstract):
    """Classe dédiée à la copie des Configuration.

    Attributes:
        __workflow_context (str): nom du context du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __configuration (Optional[Configuration]): représentation Python de la configuration créée
    """

    def run(self, datastore: Optional[str] = None) -> None:

        Config().om.info("Récupération du paramétrage de l'ancienne configuration...")
        # on récupère la configuration à copier
        o_base_config = Configuration.api_get(self.definition_dict["entity_id"], datastore=datastore)
        # stockage de l'ancien body_parameters
        d_parameter = {**o_base_config.get_store_properties()}
        l_new_use_data = d_parameter["type_infos"]["used_data"]
        # suppression des used_data
        for d_data_delete in self.definition_dict.get("delete_used_data", []):
            l_new_use_data = self._delete_used_data(d_data_delete, l_new_use_data)

        # ajout des used_data
        if self.definition_dict.get("append_used_data"):
            l_new_use_data.extend(self.definition_dict["append_used_data"])

        # enregistrement de la modification
        d_parameter["type_infos"]["used_data"] = l_new_use_data

        # suppression de la bbox pour qu'elle soit mise à jour avec les données
        if self.definition_dict.get("reset_bbox", False) and "bbox" in d_parameter["type_infos"]:
            del d_parameter["type_infos"]["bbox"]

        # lancement de la modification
        Config().om.info(f"Modification de la configuration {o_base_config} ...")

        o_base_config.api_full_edit(d_parameter)
        Config().om.info("Modification de la configuration : terminé")

    def _delete_used_data(self, d_data_delete: Dict[str, str], l_used_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        l_new_use_data = []
        for d_data in l_used_data:
            b_keep = True
            # Si on a une totale correspondance on supprime
            for s_key, s_val in d_data_delete.items():
                if d_data.get(s_key) == s_val:
                    b_keep = False
                else:
                    # on a une différence => on sort du for key-val et on garde la data
                    b_keep = True
                    break
            if b_keep:
                l_new_use_data.append(d_data)
        return l_new_use_data
