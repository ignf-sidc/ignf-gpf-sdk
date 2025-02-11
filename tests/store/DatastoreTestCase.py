from unittest.mock import MagicMock, patch

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.store.Datastore import Datastore
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from tests.GpfTestCase import GpfTestCase


class DatastoreTestCase(GpfTestCase):
    """Tests Upload class.

    cmd : python3 -m unittest -b tests.store.DatastoreTestCase
    """

    json_request = {
        "communities_member": [
            {"community": {"datastore": "1", "name": "Datastore 1", "technical_name": "ds1"}},
            {"community": {"datastore": "2", "name": "Datastore 2", "technical_name": "ds2"}},
        ]
    }

    def test_api_list_all(self) -> None:
        """Vérifie le bon fonctionnement de api_list."""
        # On a une réponse renvoyant 2 entités
        o_response = GpfTestCase.get_response(json=DatastoreTestCase.json_request)
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = Datastore.api_list()
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with("user_get")
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 2)
            for i, o_entity in enumerate(l_entities, start=1):
                self.assertIsInstance(o_entity, Datastore)
                self.assertEqual(o_entity.id, str(i))
                self.assertEqual(o_entity["name"], DatastoreTestCase.json_request["communities_member"][i - 1]["community"]["name"])
                self.assertEqual(o_entity["technical_name"], DatastoreTestCase.json_request["communities_member"][i - 1]["community"]["technical_name"])

    def test_api_list_filer_name(self) -> None:
        """Vérifie le bon fonctionnement de api_list quand on fait un filtre sur le nom."""
        # On a une réponse renvoyant 2 entités et on ne doit en conserver qu'une
        o_response = GpfTestCase.get_response(json=DatastoreTestCase.json_request)
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = Datastore.api_list(infos_filter={"name": "Datastore 2"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with("user_get")
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 1)
            self.assertIsInstance(l_entities[0], Datastore)
            self.assertEqual(l_entities[0].id, "2")
            self.assertEqual(l_entities[0]["name"], "Datastore 2")
            self.assertEqual(l_entities[0]["technical_name"], "ds2")

    def test_api_list_filer_technical_name(self) -> None:
        """Vérifie le bon fonctionnement de api_list quand on fait un filtre sur le nom technique."""
        # On a une réponse renvoyant 2 entités et on ne doit en conserver qu'une
        o_response = GpfTestCase.get_response(json=DatastoreTestCase.json_request)
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = Datastore.api_list(infos_filter={"name": "ds1"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with("user_get")
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 1)
            self.assertIsInstance(l_entities[0], Datastore)
            self.assertEqual(l_entities[0].id, "1")
            self.assertEqual(l_entities[0]["name"], "Datastore 1")
            self.assertEqual(l_entities[0]["technical_name"], "ds1")

    def test_get_id(self) -> None:
        """test de get_id"""

        # datastore existant :
        s_uuid = "d2773f66-6b49-4e6d-bf14-cbe6f5ccd46d"
        s_nom_datastore = "nom"
        l_datastore = [MagicMock(id=s_uuid)]
        with patch.object(Datastore, "api_list", return_value=l_datastore) as o_api_list:
            # datastore avec le uuid :
            s_res = Datastore.get_id(s_uuid)
            self.assertEqual(s_uuid, s_res)
            o_api_list.assert_not_called()

            # datastore avec le nom :
            s_res = Datastore.get_id(s_nom_datastore)
            self.assertEqual(s_uuid, s_res)
            o_api_list.assert_called_once_with(infos_filter={"name": s_nom_datastore})

        # datastore non existant :
        with patch.object(Datastore, "api_list", return_value=[]) as o_api_list:
            with self.assertRaises(GpfSdkError) as o_arc:
                Datastore.get_id("non existant")
            self.assertEqual(o_arc.exception.message, "Le datastore demandé 'non existant' n'a pas été trouvé. Vérifier le nom indiqué.")
            o_api_list.assert_called_once_with(infos_filter={"name": "non existant"})
