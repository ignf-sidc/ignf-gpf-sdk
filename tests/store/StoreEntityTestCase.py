import json
import time
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

from sdk_entrepot_gpf.store.Errors import StoreEntityError
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from tests.GpfTestCase import GpfTestCase


class StoreEntityTestCase(GpfTestCase):
    """Tests StoreEntity class.

    cmd : python3 -m unittest -b tests.store.StoreEntityTestCase
    """

    def test_init_getters(self) -> None:
        """Vérifie le bon fonctionnement du constructeur et des getters."""
        # Donnée renvoyée par l'API
        d_api_data = {
            "_id": "123456789",
            "name": "nom",
            "key": "value",
            "tags": {"tag_key": "tag_value"},
        }
        # Instanciation d'une Store entity
        o_store_entity = StoreEntity(d_api_data, "datastore_1")

        # Vérifications
        # On a bien un comportement de dictionnaire
        self.assertEqual(o_store_entity["key"], "value")
        # Le getter "id" est ok
        self.assertEqual(o_store_entity.id, "123456789")
        # Le getter "datastore" est ok
        self.assertEqual(o_store_entity.datastore, "datastore_1")
        # Le getter "get_store_properties" est ok
        self.assertDictEqual(o_store_entity.get_store_properties(), d_api_data)
        # Le getter "get" est ok
        self.assertEqual(o_store_entity.get("_id"), "123456789")
        self.assertEqual(o_store_entity.get("name"), "nom")
        self.assertEqual(o_store_entity.get("tags.tag_key"), "tag_value")
        # Le getter "to_json" est ok
        s_json = o_store_entity.to_json()
        self.assertIsInstance(s_json, str)
        self.assertEqual(s_json, json.dumps(d_api_data))
        s_json = o_store_entity.to_json(indent=4)
        self.assertIsInstance(s_json, str)
        self.assertEqual(s_json, json.dumps(d_api_data, indent=4))
        # La représentation est ok
        self.assertEqual(str(o_store_entity), "StoreEntity(id=123456789, name=nom)")
        self.assertEqual(str(StoreEntity({"_id": "123456789"})), "StoreEntity(id=123456789)")
        self.assertEqual(repr(o_store_entity), "StoreEntity(id=123456789, name=nom)")
        self.assertEqual(repr(StoreEntity({"_id": "123456789"})), "StoreEntity(id=123456789)")
        # Getter nom/intitulé
        self.assertEqual(StoreEntity.entity_name(), StoreEntity._entity_name)  # pylint:disable=protected-access
        self.assertEqual(StoreEntity.entity_title(), StoreEntity._entity_title)  # pylint:disable=protected-access

    def test_filter_dict_from_str(self) -> None:
        """Vérifie le bon fonctionnement de filter_dict_from_str."""
        # On teste avec ou sans espace
        d_tests = {
            "cle1=valeur1, cle2=valeur2, cle3=valeur3": {"cle1": "valeur1", "cle2": "valeur2", "cle3": "valeur3"},
            "cle1=valeur1, cle2 = valeur2, cle3=valeur3": {"cle1": "valeur1", "cle2": "valeur2", "cle3": "valeur3"},
            " cle1=valeur1,cle2=valeur2,cle3=valeur3 ": {"cle1": "valeur1", "cle2": "valeur2", "cle3": "valeur3"},
        }
        # On itère sur la liste de tests
        for s_key, d_value in d_tests.items():
            d_parsed = StoreEntity.filter_dict_from_str(s_key)
            self.assertIsInstance(d_parsed, dict)
            self.assertDictEqual(d_value, d_parsed, s_key)
        # Test si erreur
        with self.assertRaises(StoreEntityError) as o_arc:
            StoreEntity.filter_dict_from_str("pas de signe égal")
        self.assertEqual(o_arc.exception.message, "filter_tags_dict_from_str : le filtre 'pas de signe égal' ne contient pas le caractère '='")

    def test_api_get_1(self) -> None:
        """Vérifie le bon fonctionnement de api_get si tout va bien, sans choix du datastore."""
        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json={"_id": "123456789"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue la création d'un objet
            o_store_entity = StoreEntity.api_get("1234")
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_get",
                route_params={"datastore": None, StoreEntity.entity_name(): "1234"},
            )
            # Vérifications sur o_store_entity
            self.assertIsInstance(o_store_entity, StoreEntity)
            self.assertEqual(o_store_entity.id, "123456789")

    def test_api_get_2(self) -> None:
        """Vérifie le bon fonctionnement de api_get si tout va bien, avec choix du datastore."""
        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json={"_id": "123456789"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue la création d'un objet
            o_store_entity = StoreEntity.api_get("1234", "datastore1")
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_get",
                route_params={"datastore": "datastore1", StoreEntity.entity_name(): "1234"},
            )
            # Vérifications sur o_store_entity
            self.assertIsInstance(o_store_entity, StoreEntity)
            self.assertEqual(o_store_entity.id, "123456789")
            self.assertEqual(o_store_entity.datastore, "datastore1")

    def test_api_create_1(self) -> None:
        """Vérifie le bon fonctionnement de api_create sans route_params."""
        # on créé un store entity dans l'api (avec un dictionnaire)
        # on vérifie que la fct de creation a bien instancié le store entity avec le dictionnaire envoyé
        # 1/ on vérifie l'appel ApiRequester.route_request
        # 2/ on vérifie l'objet instancié

        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json={"_id": "123456789"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
            # On effectue la création d'un objet
            o_store_entity = StoreEntity.api_create({"key_1": "value_1"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_create",
                route_params=None,
                method=ApiRequester.POST,
                data={"key_1": "value_1"},
            )
            # Vérifications sur o_store_entity
            self.assertIsInstance(o_store_entity, StoreEntity)
            self.assertEqual(o_store_entity.id, "123456789")
            self.assertEqual(o_store_entity.datastore, None)

    def test_api_create_2(self) -> None:
        """Vérifie le bon fonctionnement de api_create avec route_params et datastore nul."""
        # on créé un store entity dans l'api (avec un dictionnaire)
        # on vérifie que la fct de creation a bien instancié le store entity avec le dictionnaire envoyé
        # 1/ on vérifie l'appel ApiRequester.route_request
        # 2/ on vérifie l'objet instancié

        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json={"_id": "123456789"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
            # On effectue la création d'un objet
            o_store_entity = StoreEntity.api_create({"key_1": "value_1"}, route_params={"toto": "titi"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_create",
                route_params={"toto": "titi"},
                method=ApiRequester.POST,
                data={"key_1": "value_1"},
            )
            # Vérifications sur o_store_entity
            self.assertIsInstance(o_store_entity, StoreEntity)
            self.assertEqual(o_store_entity.id, "123456789")
            self.assertEqual(o_store_entity.datastore, None)

    def test_api_create_3(self) -> None:
        """Vérifie le bon fonctionnement de api_create avec route_params et datastore non nul"""
        # on créé un store entity dans l'api (avec un dictionnaire)
        # on vérifie que la fct de creation a bien instancié le store entity avec le dictionnaire envoyé
        # 1/ on vérifie l'appel ApiRequester.route_request
        # 2/ on vérifie l'objet instancié (id et datastore)

        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json={"_id": "123456789"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
            # On effectue la création d'un objet
            o_store_entity = StoreEntity.api_create({"key_1": "value_1"}, route_params={"datastore": "datastore1", "toto": "titi"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_create",
                route_params={"datastore": "datastore1", "toto": "titi"},
                method=ApiRequester.POST,
                data={"key_1": "value_1"},
            )
            # Vérifications sur o_store_entity
            self.assertIsInstance(o_store_entity, StoreEntity)
            self.assertEqual(o_store_entity.id, "123456789")
            self.assertEqual(o_store_entity.datastore, "datastore1")

    def test_api_list_multi_pages(self) -> None:
        """Vérifie le bon fonctionnement de api_list si plusieurs pages.
        Ici on ne spécifie pas le datastore.
        """
        # On a deux réponses : indiquant qu'il y a 12 entités au total
        l_responses = [
            GpfTestCase.get_response(json=[{"_id": str(i)} for i in range(1, 11)], headers={"Content-Range": "1-10/12"}),
            GpfTestCase.get_response(json=[{"_id": str(i)} for i in range(11, 13)], headers={"Content-Range": "11-12/12"}),
        ]
        # 1 : par défaut on va faire une seconde requête pour tout récupérer
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", side_effect=l_responses) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = StoreEntity.api_list(infos_filter={"k_info": "v_info"}, tags_filter={"k_tag": "v_tag"})
            # Vérification sur o_mock_request
            # Fonction appelée 3 fois
            self.assertEqual(o_mock_request.call_count, 2)
            # Paramètres ok, avec pages de 1 à 2
            self.assertListEqual(
                o_mock_request.call_args_list,
                [
                    call("store_entity_list", route_params={"datastore": None}, params={"k_info": "v_info", "tags[k_tag]": "v_tag", "page": 1, "limit": 10}),
                    call("store_entity_list", route_params={"datastore": None}, params={"k_info": "v_info", "tags[k_tag]": "v_tag", "page": 2, "limit": 10}),
                ],
            )
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 12)
            for i, o_entity in enumerate(l_entities, start=1):
                self.assertIsInstance(o_entity, StoreEntity)
                self.assertEqual(o_entity.id, str(i))

        # 2 : si on demande une page précisé (la 1) on ne fait pas d'autre requête
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", side_effect=l_responses) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = StoreEntity.api_list(infos_filter={"k_info": "v_info"}, tags_filter={"k_tag": "v_tag"}, page=1)
            # Vérification sur o_mock_request
            # Fonction appelée 1 fois
            self.assertEqual(o_mock_request.call_count, 1)
            # Paramètres ok, avec page 1 uniquement
            self.assertListEqual(
                o_mock_request.call_args_list,
                [
                    call("store_entity_list", route_params={"datastore": None}, params={"k_info": "v_info", "tags[k_tag]": "v_tag", "page": 1, "limit": 10}),
                ],
            )
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 10)
            for i, o_entity in enumerate(l_entities, start=1):
                self.assertIsInstance(o_entity, StoreEntity)
                self.assertEqual(o_entity.id, str(i))

    def test_api_list_no_loop(self) -> None:
        """Vérifie le bon fonctionnement de api_list si on demande tout mais qu'on ne doit pas boucler.
        On ne doit pas boucler si Content-Range indique qu'on a tout récupéré, ou qu'il n'est pas défini ou qu'il est non parsable.
        Ici, on spécifie un datastore.
        """
        # On a une réponse renvoyant 2 entités et indiquant qu'il y a 2 entités au total
        o_response = GpfTestCase.get_response(json=[{"_id": "1"}, {"_id": "2"}], headers={"Content-Range": "1-2/2"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = StoreEntity.api_list(datastore="datastore1", infos_filter={"k_info": "v_info"}, tags_filter={"k_tag": "v_tag"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_list",
                route_params={"datastore": "datastore1"},
                params={"k_info": "v_info", "tags[k_tag]": "v_tag", "page": 1, "limit": 10},
            )
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 2)
            for i, o_entity in enumerate(l_entities, start=1):
                self.assertIsInstance(o_entity, StoreEntity)
                self.assertEqual(o_entity.id, str(i))

        # On a une réponse renvoyant 2 entités et sans Content-Range
        o_response = GpfTestCase.get_response(json=[{"_id": "1"}, {"_id": "2"}])
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = StoreEntity.api_list(datastore="datastore1", infos_filter={"k_info": "v_info"}, tags_filter={"k_tag": "v_tag"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_list",
                route_params={"datastore": "datastore1"},
                params={"k_info": "v_info", "tags[k_tag]": "v_tag", "page": 1, "limit": 10},
            )
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 2)
            for i, o_entity in enumerate(l_entities, start=1):
                self.assertIsInstance(o_entity, StoreEntity)
                self.assertEqual(o_entity.id, str(i))

        # On a une réponse renvoyant 2 entités et avec un content-range non parsable
        o_response = GpfTestCase.get_response(json=[{"_id": "1"}, {"_id": "2"}], headers={"Content-Range": "non_parsable"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester(), "route_request", return_value=o_response) as o_mock_request:
            # On effectue le listing d'une entité
            l_entities = StoreEntity.api_list(datastore="datastore1", infos_filter={"k_info": "v_info"}, tags_filter={"k_tag": "v_tag"})
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_list",
                route_params={"datastore": "datastore1"},
                params={"k_info": "v_info", "tags[k_tag]": "v_tag", "page": 1, "limit": 10},
            )
            # Vérifications sur l_entities
            self.assertIsInstance(l_entities, list)
            self.assertEqual(len(l_entities), 2)
            for i, o_entity in enumerate(l_entities, start=1):
                self.assertIsInstance(o_entity, StoreEntity)
                self.assertEqual(o_entity.id, str(i))

    def test_api_delete(self) -> None:
        """Vérifie le bon fonctionnement de api_delete."""
        # on créé une instance puis on la supprime
        # 1/ on vérifie l'appel ApiRequester.route_request
        # 2/ avec le mock, pas besoin de vérifier que l'instance (SUR l'api) n'existe plus

        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester, "route_request", return_value=None) as o_mock_request:
            # On effectue la suppression d'une entité
            # On instancie une entité à supprimer
            o_store_entity = StoreEntity({"_id": "id_à_supprimer"})
            # On appelle la fonction api_delete
            o_store_entity.api_delete()
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with(
                "store_entity_delete",
                route_params={"datastore": None, "store_entity": "id_à_supprimer"},
                method=ApiRequester.DELETE,
            )

    def test_api_update(self) -> None:
        """Vérifie le bon fonctionnement de api_update."""
        # Infos de l'entité avant la maj et après
        d_old_data = {"_id": "id_à_maj", "name": "ancien nom"}
        d_new_data = {"_id": "id_à_maj", "name": "nouveau nom"}
        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json=d_new_data)
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
            # On effectue la suppression d'une entité
            # On instancie une entité à mettre à jour
            o_store_entity = StoreEntity(d_old_data)
            # Les info de l'entité sont celles à mettre à jour
            self.assertDictEqual(o_store_entity.get_store_properties(), d_old_data)
            # On appelle la fonction api_update
            o_store_entity.api_update()
            # Vérification sur o_mock_request
            o_mock_request.assert_called_once_with("store_entity_get", route_params={"datastore": None, "store_entity": "id_à_maj"})
            # Vérification que les infos de l'entité sont maj
            self.assertDictEqual(o_store_entity.get_store_properties(), d_new_data)

    def test_eq(self) -> None:
        """Vérifie le bon fonctionnement de eq."""
        # Instanciation d'une Store entity
        o_store_entity_1 = StoreEntity({"_id": "1"})
        o_store_entity_2 = StoreEntity({"_id": "2"})
        o_store_entity_3 = StoreEntity({"_id": "1"})

        # on vérifie que le test sur deux objets identiques renvoie bien true
        self.assertEqual(o_store_entity_1, o_store_entity_3)
        # on vérifie qu'à l'inverse le test sur deux instances différentes renvoie false
        self.assertNotEqual(o_store_entity_1, o_store_entity_2)
        # on vérifie que le set se comporte comme attendu
        self.assertEqual(len(set([o_store_entity_1, o_store_entity_2, o_store_entity_3])), 2)
        # on vérifie que le test sur deux types différents est également false
        self.assertNotEqual(o_store_entity_1, 1)
        self.assertNotEqual(o_store_entity_1, "str")

    def test_str(self) -> None:
        """Vérifie le bon fonctionnement de eq."""
        # Instanciation de StoreEntities
        o_store_entity_1 = StoreEntity({"_id": "1"})
        o_store_entity_2 = StoreEntity({"_id": "2", "name": "name_2"})
        o_store_entity_3 = StoreEntity({"_id": "3", "name": "name_3", "layer_name": "layer_name_3"})
        o_store_entity_4 = StoreEntity({"_id": "4", "layer_name": "layer_name_4"})

        # on vérifie que le str est ok
        self.assertEqual(str(o_store_entity_1), "StoreEntity(id=1)")
        self.assertEqual(str(o_store_entity_2), "StoreEntity(id=2, name=name_2)")
        self.assertEqual(str(o_store_entity_3), "StoreEntity(id=3, name=name_3, layer_name=layer_name_3)")
        self.assertEqual(str(o_store_entity_4), "StoreEntity(id=4, layer_name=layer_name_4)")

    def test_get_datetime(self) -> None:
        """Vérifie le bon fonctionnement de _get_datetime."""
        # Instanciation de StoreEntities
        o_store_entity = StoreEntity({"_id": "1", "datetime": "2022-09-20T10:45:04.396Z"})

        # Cas sans la clef demandée
        with patch.object(o_store_entity, "api_update", return_value=None) as o_mock_update:
            o_datetime = o_store_entity._get_datetime("key")  # pylint:disable=protected-access
            # Vérifications
            self.assertIsNone(o_datetime)
            o_mock_update.assert_called_once()

        # Cas avec la clef demandée
        with patch.object(o_store_entity, "api_update", return_value=None) as o_mock_update:
            o_datetime = o_store_entity._get_datetime("datetime")  # pylint:disable=protected-access
            # Vérifications
            self.assertIsNotNone(o_datetime)
            o_mock_update.assert_not_called()

    def test_delete_cascade(self) -> None:
        """test de delete_cascade"""
        o_store_entity = StoreEntity({"_id": "1", "datetime": "2022-09-20T10:45:04.396Z"})

        # test sans before_delete
        with patch.object(StoreEntity, "delete_liste_entities", return_value=None) as o_mock_delete:
            o_store_entity.delete_cascade()
            o_mock_delete.assert_called_once_with([o_store_entity], None)

        # test avec before_delete
        with patch.object(StoreEntity, "delete_liste_entities", return_value=None) as o_mock_delete:
            o_mock = MagicMock()
            o_mock.before_delete_function.return_value = [o_store_entity]
            o_store_entity.delete_cascade(o_mock.before_delete_function)
            o_mock_delete.assert_called_once_with([o_store_entity], o_mock.before_delete_function)

    @patch.object(time, "sleep", return_value=None)
    def test_delete_liste_entities(self, o_mock_sleep: Mock) -> None:
        """test de delete_liste_entities"""

        o_mock_1 = MagicMock()
        o_mock_2 = MagicMock()
        o_mock_3 = MagicMock()

        def reset_mock() -> None:
            """reset des mock de la fonction"""
            o_mock_1.reset_mock()
            o_mock_2.reset_mock()
            o_mock_3.reset_mock()
            o_mock_sleep.reset_mock()

        # suppression d'un élément sans before_delete
        StoreEntity.delete_liste_entities([o_mock_1])
        o_mock_1.api_delete.assert_called_once_with()
        self.assertEqual(1, o_mock_sleep.call_count)
        reset_mock()

        # suppression de plusieurs éléments sans before_delete
        l_entity: List[StoreEntity] = [o_mock_1, o_mock_2]
        StoreEntity.delete_liste_entities(l_entity)
        o_mock_1.api_delete.assert_called_once_with()
        o_mock_2.api_delete.assert_called_once_with()
        self.assertEqual(2, o_mock_sleep.call_count)
        reset_mock()

        # suppression avec before_delete, sans modification
        o_mock_function = MagicMock()
        o_mock_function.before_delete_function.return_value = l_entity
        StoreEntity.delete_liste_entities(l_entity, o_mock_function.before_delete_function)
        o_mock_function.before_delete_function.assert_called_once_with(l_entity)
        o_mock_1.api_delete.assert_called_once_with()
        o_mock_2.api_delete.assert_called_once_with()
        self.assertEqual(2, o_mock_sleep.call_count)
        reset_mock()

        # suppression avec before_delete, avec modification
        o_mock_function = MagicMock()
        o_mock_function.before_delete_function.return_value = [o_mock_1, o_mock_3]
        StoreEntity.delete_liste_entities(l_entity, o_mock_function.before_delete_function)
        o_mock_function.before_delete_function.assert_called_once_with(l_entity)
        o_mock_1.api_delete.assert_called_once_with()
        o_mock_2.api_delete.assert_not_called()
        o_mock_3.api_delete.assert_called_once_with()
        self.assertEqual(2, o_mock_sleep.call_count)
        reset_mock()

        # suppression avec before_delete, avec annulation liste vide ou None
        for o_return in [[], None]:  # type:ignore
            o_mock_function = MagicMock()
            o_mock_function.before_delete_function.return_value = o_return
            StoreEntity.delete_liste_entities(l_entity, o_mock_function.before_delete_function)
            o_mock_function.before_delete_function.assert_called_once_with(l_entity)
            o_mock_1.api_delete.assert_not_called()
            o_mock_2.api_delete.assert_not_called()
            o_mock_3.api_delete.assert_not_called()
            self.assertEqual(0, o_mock_sleep.call_count)
            reset_mock()

    def test_edit(self) -> None:
        """test de edit"""
        o_store_entity = StoreEntity({"_id": "1"})
        with self.assertRaises(StoreEntityError) as o_arc:
            o_store_entity.edit({"key": "val"})
        self.assertEqual("Il est impossible d'éditer cette entité.", o_arc.exception.message)
