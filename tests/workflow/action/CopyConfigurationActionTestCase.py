from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.CopyConfigurationAction import CopyConfigurationAction
from sdk_entrepot_gpf.workflow.action.ConfigurationAction import ConfigurationAction

from tests.GpfTestCase import GpfTestCase


# pylint:disable=too-many-arguments
# pylint:disable=too-many-locals
# pylint:disable=too-many-branches


class CopyConfigurationActionTestCase(GpfTestCase):
    """Tests CopyConfigurationAction class.

    cmd : python3 -m unittest -b tests.workflow.action.CopyConfigurationActionTestCase
    """

    def test_run(self) -> None:
        """test de run"""
        # manque des paramétres
        l_dict_definition: List[Dict[str, Any]] = [{}, {"body_parameters": {}}, {"body_parameters": {"name": "nouveau name"}}, {"body_parameters": {"layer_name": "nouveau layer_name"}}]
        for d_definition in l_dict_definition:
            o_action = CopyConfigurationAction("contexte", d_definition, None, "CONTINUE")
            with self.assertRaises(StepActionError) as o_mock_err:
                o_action.run("datastore")
            self.assertEqual('Les clefs "name" et "layer_name" sont obligatoires dans "body_parameters"', o_mock_err.exception.message)

        d_definition = {"url_parameters": {"configuration": "123"}, "body_parameters": {"layer_name": "nouveau layer_name", "name": "nouveau name"}}
        o_action = CopyConfigurationAction("contexte", d_definition, None, "CONTINUE")

        # fonctionnement OK
        o_mock_base_config = MagicMock()
        o_mock_base_config.get_store_properties.return_value = {"layer_name": "ancien layer_name", "name": "ancien name", "autre": "prame", "key": ["l1", "l2"]}
        d_new_config = {"layer_name": "nouveau layer_name", "name": "nouveau name", "autre": "prame", "key": ["l1", "l2"]}
        with patch.object(ConfigurationAction, "run", return_value=None) as o_mock_run:
            with patch.object(Configuration, "api_get", return_value=o_mock_base_config) as o_mock_get:
                o_action.run("datastore")

        o_mock_run.assert_called_once_with("datastore")
        o_mock_get.assert_called_once_with("123", datastore="datastore")
        o_mock_base_config.get_store_properties.assert_called_once_with()
        self.assertDictEqual(d_new_config, o_action.definition_dict["body_parameters"])
