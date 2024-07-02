from typing import Dict, Any
from unittest.mock import patch

from sdk_entrepot_gpf.store.Access import Access
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.AccessAction import AccessAction
from sdk_entrepot_gpf.io.Errors import ConflictError

from tests.GpfTestCase import GpfTestCase


class AccessActionTestCase(GpfTestCase):
    """Tests AccessAction class.

    cmd : python3 -m unittest -b tests.workflow.action.AccessActionTestCase
    """

    d_action: Dict[str, Any] = {
        "type": "access",
        "url_parameters": {
            "key": "key_id",
        },
        "body_parameters": {
            "permission": "permission_id",
            "offerings": ["offering_id"],
        },
    }

    def test_run_ok(self) -> None:
        """test de run quand tout va bien"""
        o_action = AccessAction("context", self.d_action)
        # Permet de vérifier qu'il n'y a pas encore d'accès
        self.assertIsNone(o_action.access)

        # fonctionnement OK
        # o_access = MagicMock() TODO à mettre après l'évolution de l'API
        with patch.object(Access, "api_create", return_value=True) as o_mock_create:
            o_action.run("datastore")
        # Permet de mocker l'appel à la création de la permission
        o_mock_create.assert_called_once_with(
            self.d_action["body_parameters"],
            route_params={"datastore": "datastore", **self.d_action["url_parameters"]},
        )
        # Permet de vérifier qu'après l'appel l'accès ajouté correspond à celui qui est créé
        # self.assertEqual(o_access, o_action.access) TODO à mettre après l'évolution de l'API

    def test_run_ko_1(self) -> None:
        """test de run quand une exception ConflictError est levée"""

        o_action = AccessAction("context", self.d_action)
        # Permet de vérifier qu'il n'y a pas encore d'accès
        self.assertIsNone(o_action.access)

        # fonctionnement OK
        # o_access = MagicMock() TODO à mettre après l'évolution de l'API
        with patch.object(Access, "api_create", side_effect=ConflictError("url", "method", {}, {}, "response")) as o_mock_create:
            with self.assertRaises(StepActionError) as o_arc:
                o_action.run("datastore")
        # Permet de mocker l'appel à la création de la permission
        o_mock_create.assert_called_once_with(
            self.d_action["body_parameters"],
            route_params={"datastore": "datastore", **self.d_action["url_parameters"]},
        )
        # Permet de vérifier que l'accès est toujours None
        self.assertIsNone(o_action.access)
        # Permet de vérifier le message d'exception
        self.assertEqual("Impossible de créer l'offre il y a un conflict : \nPas d'indication spécifique indiquée par l'API.", o_arc.exception.message)

    def test_run_ko_2(self) -> None:
        """test de run quand api_create ne renvoie pas ok"""

        o_action = AccessAction("context", self.d_action)
        # Permet de vérifier qu'il n'y a pas encore d'accès
        self.assertIsNone(o_action.access)

        # fonctionnement OK
        # o_access = MagicMock() TODO à mettre après l'évolution de l'API
        with patch.object(Access, "api_create", return_value=False) as o_mock_create:
            with self.assertRaises(StepActionError) as o_arc:
                o_action.run("datastore")
        # Permet de mocker l'appel à la création de la permission
        o_mock_create.assert_called_once_with(
            self.d_action["body_parameters"],
            route_params={"datastore": "datastore", **self.d_action["url_parameters"]},
        )
        # Permet de vérifier que l'accès est toujours None
        self.assertIsNone(o_action.access)
        # Permet de vérifier le message d'exception
        self.assertEqual("Erreur à la création de l'accès.", o_arc.exception.message)
