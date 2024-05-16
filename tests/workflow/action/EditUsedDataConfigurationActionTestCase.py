from typing import Any, Dict
from unittest.mock import patch, MagicMock

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.action.EditUsedDataConfigurationAction import EditUsedDataConfigurationAction

from tests.GpfTestCase import GpfTestCase


class EditUsedDataConfigurationActionTestCase(GpfTestCase):
    """Tests EditUsedDataConfigurationAction class.

    cmd : python3 -m unittest -b tests.workflow.action.EditUsedDataConfigurationActionTestCase
    """

    i = 0

    def run_run(self, s_uuid: str, d_definition: Dict[str, Any], d_base_config: Dict[str, Any], d_new_config: Dict[str, Any]) -> None:
        """lancement des tests de EditUsedDataConfigurationAction.run

        Args:
            s_uuid (str): uuid
            d_definition (Dict[str, Any]): dictionnaire de l'action
            d_base_config (Dict[str, Any]): dictionnaire de la configuration à modifiée
            d_new_config (Dict[str, Any]): dictionnaire de la configuration après modification qui sera envoyé à la GPF
        """
        self.i += 1
        with self.subTest(i=self.i):
            o_action = EditUsedDataConfigurationAction("contexte", d_definition, None)
            o_mock_base_config = MagicMock()
            o_mock_base_config.get_store_properties.return_value = d_base_config

            with patch.object(Configuration, "api_get", return_value=o_mock_base_config) as o_mock_get:
                o_action.run("datastore")
            o_mock_get.assert_called_once_with(s_uuid, datastore="datastore")
            o_mock_base_config.get_store_properties.assert_called_once_with()
            o_mock_base_config.api_full_edit.assert_called_once_with(d_new_config)

    def test_run(self) -> None:
        """test de run"""
        s_uuid = "123"

        # ajout + suppression (pas de reset de la BBox)
        d_definition: Dict[str, Any] = {
            "type": "used_data-configuration",
            "entity_id": s_uuid,
            "append_used_data": [{"data": "data"}],
            "delete_used_data": [{"param1": "val1"}, {"param2": "val2"}, {"param1": "val3", "param2": "val3"}],
        }
        l_used_data = [
            {"param1": "val1", "autre": "val"},
            {"param2": "val2", "autre": "val"},
            {"param1": "val3", "param2": "val3", "autre": "val"},
            {"param1": "val4", "param2": "val3", "autre": "val"},
            {"param1": "val3", "param2": "val4", "autre": "val"},
            {"param1": "val4", "param2": "val4", "autre": "val"},
        ]
        d_base_config = {
            "name": "nouveau name",
            "type_infos": {
                "used_data": [*l_used_data],
                "bbox": {},
            },
        }
        d_new_config: Dict[str, Any] = {
            "name": "nouveau name",
            "type_infos": {
                "used_data": [
                    {"param1": "val4", "param2": "val3", "autre": "val"},
                    {"param1": "val3", "param2": "val4", "autre": "val"},
                    {"param1": "val4", "param2": "val4", "autre": "val"},
                    {"data": "data"},
                ],
                "bbox": {},
            },
        }

        # ajout + suppression (pas de reset de la BBox)
        self.run_run(s_uuid, d_definition, d_base_config, d_new_config)

        # maj de BBox + modif stored_data
        d_base_config["type_infos"] = {"used_data": [*l_used_data], "bbox": {}}
        self.run_run(s_uuid, d_definition, d_base_config, d_new_config)

        # maj de bbox demandé mais pas de bbox dans la config
        d_definition["reset_bbox"] = True
        del d_new_config["type_infos"]["bbox"]
        d_base_config["type_infos"] = {"used_data": [*l_used_data]}
        self.run_run(s_uuid, d_definition, d_base_config, d_new_config)

        # pas de modif stored_data
        d_base_config["type_infos"] = {"used_data": [*l_used_data], "bbox": {}}
        d_definition_2: Dict[str, Any] = {"type": "used_data-configuration", "entity_id": s_uuid}
        self.run_run(s_uuid, d_definition_2, d_base_config, d_base_config)

        # maj de BBox + pas modif stored_data
        d_definition_2["reset_bbox"] = True
        d_base_config["type_infos"] = {"used_data": [*l_used_data], "bbox": {}}
        d_new_config_2 = {"name": "nouveau name", "type_infos": {"used_data": [*l_used_data]}}
        self.run_run(s_uuid, d_definition_2, d_base_config, d_new_config_2)
