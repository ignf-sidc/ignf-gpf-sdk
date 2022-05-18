from http import HTTPStatus
from io import BufferedReader
import json
from pathlib import Path
from typing import Dict, Tuple
import unittest
from unittest.mock import patch
import requests
import requests_mock

from ignf_gpf_api.io.Config import Config
from ignf_gpf_api.Errors import GpfApiError
from ignf_gpf_api.auth.Authentifier import Authentifier
from ignf_gpf_api.io.ApiRequester import ApiRequester
from ignf_gpf_api.io.Errors import RouteNotFoundError

# pylint:disable=protected-access


class ApiRequesterTestCase(unittest.TestCase):
    """Tests ApiRequester class.

    cmd : python3 -m unittest -b tests.io.ApiRequesterTestCase
    """

    # On va mocker la classe d'authentification globalement
    o_mock_authentifier = patch.object(Authentifier, "get_access_token_string", return_value="test_token")
    config_path = Path(__file__).parent.parent / "_config"

    # Paramètres de requêtes
    url = "https://api.test.io/"
    param = {
        "param_key_1": "value_1",
        "param_key_2": 2,
        "param_keys[]": ["pk1", "pk2", "pk3"],
    }
    encoded_param = "?param_key_1=value_1&param_key_2=2&param_keys%5B%5D=pk1&param_keys%5B%5D=pk2&param_keys%5B%5D=pk3"
    data = {
        "data_key_1": "value_1",
        "data_key_2": 2,
    }
    files: Dict[str, Tuple[str, BufferedReader]] = {}
    response = {"key": "value"}

    @classmethod
    def setUpClass(cls) -> None:
        # On détruit le Singleton Config
        Config._instance = None
        # On charge une config spéciale pour les tests d'authentification
        o_config = Config()
        o_config.read(ApiRequesterTestCase.config_path / "test_resquester.ini")
        # On mock la classe d'authentification
        cls.o_mock_authentifier.start()

    @classmethod
    def tearDownClass(cls) -> None:
        # On ne mock plus la classe d'authentification
        cls.o_mock_authentifier.stop()

    def test_route_request_ok(self) -> None:
        """Test de route_request quand la route existe."""
        # Instanciation d'une fausse réponse HTTP
        with requests_mock.Mocker() as o_mock:
            o_mock.post("http://test.com/")
            o_api_response = requests.request("POST", "http://test.com/")
        # Instanciation du ApiRequester
        o_api_requester = ApiRequester()
        # On mock la fonction request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(o_api_requester, "url_request", return_value=o_api_response) as o_mock_request:
            # On effectue une requête
            o_fct_response = o_api_requester.route_request("test_create", {"id": 42}, ApiRequester.POST, params=self.param, data=self.data, files=self.files)
            # Vérification sur o_mock_request
            s_url = "https://api.test.io/api/v1/datastores/TEST_DATASTORE/create/42"
            o_mock_request.assert_called_once_with(s_url, ApiRequester.POST, self.param, self.data, self.files)
            # Vérification sur la réponse renvoyée par la fonction : ça doit être celle renvoyée par url_request
            self.assertEqual(o_fct_response, o_api_response)

    def test_route_request_ko(self) -> None:
        """Test de route_request quand la route n'existe pas."""
        # Instanciation du ApiRequester
        o_api_requester = ApiRequester()
        # On veut vérifier que l'exception RouteNotFoundError est levée avec le bon nom de route non trouvée
        with self.assertRaises(RouteNotFoundError) as o_arc:
            # On effectue une requête
            o_api_requester.route_request("non_existing")
        # Vérifications
        self.assertEqual(o_arc.exception.route_name, "non_existing")

    def test_request_get(self) -> None:
        """Test de request dans le cadre d'une requête get."""
        # Instanciation du ApiRequester
        o_api_requester = ApiRequester()
        # On mock...
        with requests_mock.Mocker() as o_mock:
            # Une requête réussie
            o_mock.get(self.url, json=self.response)
            # On effectue une requête
            o_response = o_api_requester.url_request(self.url, ApiRequester.GET, params=self.param, data=self.data)
            # Vérification sur la réponse
            self.assertDictEqual(o_response.json(), self.response)
            # On a dû faire une requête
            self.assertEqual(o_mock.call_count, 1, "o_mock.call_count == 1")
            # Vérifications sur l'historique (enfin ici y'a une requête...)
            o_history = o_mock.request_history
            # Requête 1 : vérification de l'url
            self.assertEqual(o_history[0].url, self.url + self.encoded_param, "check url")
            # Requête 1 : vérification du type
            self.assertEqual(o_history[0].method.lower(), "get", "method == get")
            # Requête 1 : vérification du corps de requête
            s_text = json.dumps(self.data)
            self.assertEqual(o_history[0].text, s_text, "check text")

    def test_request_post(self) -> None:
        """Test de request dans le cadre d'une requête post."""
        # Instanciation du ApiRequester
        o_api_requester = ApiRequester()
        # On mock...
        with requests_mock.Mocker() as o_mock:
            # Une requête réussie
            o_mock.post(self.url, json=self.response)
            # On effectue une requête
            o_response = o_api_requester.url_request(self.url, ApiRequester.POST, params=self.param, data=self.data)
            # Vérification sur la réponse
            self.assertDictEqual(o_response.json(), self.response)
            # On a dû faire une requête
            self.assertEqual(o_mock.call_count, 1, "o_mock.call_count == 1")
            # Vérifications sur l'historique (enfin ici y'a une requête...)
            o_history = o_mock.request_history
            # Requête 1 : vérification de l'url
            self.assertEqual(o_history[0].url, self.url + self.encoded_param, "check url")
            # Requête 1 : vérification du type
            self.assertEqual(o_history[0].method.lower(), "post", "method == post")
            # Requête 1 : vérification du corps de requête
            s_text = json.dumps(self.data)
            self.assertEqual(o_history[0].text, s_text, "check text")

    def test_request_internal_server_error(self) -> None:
        """Test de request dans le cadre de 3 erreurs internes de suite."""
        # Instanciation du ApiRequester
        o_api_requester = ApiRequester()
        # On mock...
        with requests_mock.Mocker() as o_mock:
            # Une requête non réussie
            o_mock.post(
                self.url,
                [
                    {"status_code": HTTPStatus.INTERNAL_SERVER_ERROR},
                    {"status_code": HTTPStatus.INTERNAL_SERVER_ERROR},
                    {"status_code": HTTPStatus.INTERNAL_SERVER_ERROR},
                    {"status_code": HTTPStatus.INTERNAL_SERVER_ERROR},
                ],
            )
            # On s'attend à une exception
            with self.assertRaises(GpfApiError) as o_arc:
                # On effectue une requête
                o_api_requester.url_request(self.url, ApiRequester.POST, params=self.param, data=self.data)
            # On doit avoir un message d'erreur
            self.assertEqual(o_arc.exception.message, "L'exécution d'une requête a échoué après 3 tentatives")
            # On a dû faire 4 requêtes
            self.assertEqual(o_mock.call_count, 3, "o_mock.call_count == 3")
