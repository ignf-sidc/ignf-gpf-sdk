from typing import Dict, Any
from unittest.mock import patch, MagicMock

from sdk_entrepot_gpf.store.Permission import Permission
from sdk_entrepot_gpf.workflow.action.PermissionAction import PermissionAction

from tests.GpfTestCase import GpfTestCase


# pylint:disable=too-many-arguments
# pylint:disable=too-many-locals
# pylint:disable=too-many-branches


class PermissionActionTestCase(GpfTestCase):
    """Tests PermissionAction class.

    cmd : python3 -m unittest -b tests.workflow.action.PermissionActionTestCase
    """

    def test_run(self) -> None:
        """test de run"""
        d_action: Dict[str, Any] = {
            "type": "permission",
            "body_parameters": {
                "name": "name_permission",
                "layer_name": "layer_name_permission",
            },
        }
        o_action = PermissionAction("context", d_action)
        # Permet de vérifier qu'il n'y a pas encore de permission
        self.assertIsNone(o_action.permission)

        # fonctionnement OK
        o_permission = MagicMock()
        with patch.object(Permission, "api_create", return_value=o_permission) as o_mock_create:
            o_action.run("datastore")
        # Permet de mocker l'appel à la création de la permission
        o_mock_create.assert_called_once_with(d_action["body_parameters"], route_params={"datastore": "datastore"})
        # Permet de vérifier qu'après l'appel la permission ajoutée correspond à celle qui est demandée
        self.assertEqual(o_permission, o_action.permission)
