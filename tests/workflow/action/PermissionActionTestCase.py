from typing import Dict, Any
from unittest.mock import patch, MagicMock

from sdk_entrepot_gpf.store.Permission import Permission
from sdk_entrepot_gpf.workflow.action.PermissionAction import PermissionAction

from tests.GpfTestCase import GpfTestCase


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
        self.assertListEqual(o_action.permissions, [])

        # fonctionnement OK
        l_permissions = [MagicMock()]
        with patch.object(Permission, "api_create_list", return_value=l_permissions) as o_mock_create:
            o_action.run("datastore")
        # Permet de mocker l'appel à la création de la permission
        o_mock_create.assert_called_once_with(d_action["body_parameters"], route_params={"datastore": "datastore"})
        # Permet de vérifier qu'après l'appel la permission ajoutée correspond à celle qui est demandée
        self.assertEqual(l_permissions, o_action.permissions)
