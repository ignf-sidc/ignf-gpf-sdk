from unittest.mock import patch, MagicMock

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.action.EditUsedDataConfigurationAction import EditUsedDataConfigurationAction

from tests.GpfTestCase import GpfTestCase


class EditUsedDataConfigurationActionTestCase(GpfTestCase):
    """Tests EditUsedDataConfigurationAction class.

    cmd : python3 -m unittest -b tests.workflow.action.EditUsedDataConfigurationActionTestCase
    """

    def test_run(self) -> None:
        """test de run"""
        s_uuid = "123"

        # ajout + suppression
        d_definition = {
            "type": "used_data-configurtion",
            "entity_id": s_uuid,
            "append_used_data": [{"data": "data"}],
            "delete_used_data": [{"param1": "val1"}, {"param2": "val2"}, {"param1": "val3", "param2": "val3"}],
        }
        o_action = EditUsedDataConfigurationAction("contexte", d_definition, None)
        o_mock_base_config = MagicMock()
        o_mock_base_config.get_store_properties.return_value = {
            "name": "nouveau name",
            "type_infos": {
                "used_data": [
                    {"param1": "val1", "autre": "val"},
                    {"param2": "val2", "autre": "val"},
                    {"param1": "val3", "param2": "val3", "autre": "val"},
                    {"param1": "val4", "param2": "val3", "autre": "val"},
                    {"param1": "val3", "param2": "val4", "autre": "val"},
                    {"param1": "val4", "param2": "val4", "autre": "val"},
                ],
            },
        }
        d_new_config = {
            "name": "nouveau name",
            "type_infos": {
                "used_data": [
                    {"param1": "val4", "param2": "val3", "autre": "val"},
                    {"param1": "val3", "param2": "val4", "autre": "val"},
                    {"param1": "val4", "param2": "val4", "autre": "val"},
                    {"data": "data"},
                ]
            },
        }
        with patch.object(Configuration, "api_get", return_value=o_mock_base_config) as o_mock_get:
            o_action.run("datastore")
        o_mock_get.assert_called_once_with(s_uuid, datastore="datastore")
        o_mock_base_config.get_store_properties.assert_called_once_with()
        o_mock_base_config.api_full_edit.assert_called_once_with(d_new_config)
