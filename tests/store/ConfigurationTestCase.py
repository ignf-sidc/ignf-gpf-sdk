from typing import Any, Dict
from unittest.mock import MagicMock, patch

from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.store.Errors import StoreEntityError
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity

from tests.GpfTestCase import GpfTestCase


class ConfigurationTestCase(GpfTestCase):
    """Tests Configuration class.

    cmd : python3 -m unittest -b tests.store.ConfigurationTestCase
    """

    def test_list_offerings(self) -> None:
        """Vérifie le bon fonctionnement de api_list_offerings.
        Dans ce test, on suppose que le datastore est défini (cf. route_params).
        """

        # Instanciation d'une fausse réponse HTTP
        o_response = GpfTestCase.get_response(json=[{"_id": "offering_1"}, {"_id": "offering_2"}])

        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
            # Instanciation d'une Configuration
            o_configuration = Configuration({"_id": "123456789"}, "id_datastore")
            # Listing de ses Offres
            l_offerings = o_configuration.api_list_offerings()
            # on vérifie que route_request est appelé correctement
            o_mock_request.assert_called_once_with(
                "configuration_list_offerings",
                route_params={"datastore": "id_datastore", "configuration": "123456789"},
                method=ApiRequester.GET,
            )
            # on vérifie qu'on a bien récupéré une liste d'Offering
            self.assertIsInstance(l_offerings, list)
            self.assertIsInstance(l_offerings[0], Offering)
            self.assertIsInstance(l_offerings[1], Offering)
            self.assertEqual(l_offerings[0].id, "offering_1")
            self.assertEqual(l_offerings[1].id, "offering_2")

    def test_add_offering(self) -> None:
        """Vérifie le bon fonctionnement de api_add_offering.
        Dans ce test, le datastore n'est pas défini (cf. route_params).
        """

        d_data_offering = {"_id": "11111111"}

        # On mock la fonction api_create, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(StoreEntity, "api_create", return_value=Offering(d_data_offering)) as o_mock_create:
            # Instanciation d'une Configuration
            o_configuration = Configuration({"_id": "2222222"}, datastore="datastore")
            # Ajout d'une Offre
            o_offering = o_configuration.api_add_offering(d_data_offering)
            # on vérifie que api_create est appelé correctement
            o_mock_create.assert_called_once_with(
                d_data_offering,
                route_params={"configuration": "2222222", "datastore": "datastore"},
            )
            # on vérifie que l'entité renvoyée est cohérente
            self.assertIsInstance(o_offering, Offering)
            self.assertEqual(o_offering.id, "11111111")
            self.assertDictEqual(o_offering.get_store_properties(), d_data_offering)

    def test_delete_cascade(self) -> None:
        """test de delete_cascade"""
        o_configuration = Configuration({"_id": "2222222"})

        # Mock offerings
        o_mock_offering_1 = MagicMock()
        o_mock_offering_2 = MagicMock()

        # mock pour la fonction before_delete
        o_mock = MagicMock()
        o_mock.before_delete_function.return_value = [o_configuration]

        for f_before_delete in [None, o_mock.before_delete_function]:
            # Configuration sans offre
            with patch.object(Configuration, "api_list_offerings", return_value=[]) as o_mock_list:
                with patch.object(Configuration, "delete_liste_entities", return_value=None) as o_mock_delete:
                    o_configuration.delete_cascade(f_before_delete)
                    o_mock_delete.assert_called_once_with([o_configuration], f_before_delete)
                    o_mock_list.assert_called_once_with()

            # Configuration avec offres
            with patch.object(Configuration, "api_list_offerings", return_value=[o_mock_offering_1, o_mock_offering_2]) as o_mock_list:
                with patch.object(Configuration, "delete_liste_entities", return_value=None) as o_mock_delete:
                    o_configuration.delete_cascade(f_before_delete)
                    o_mock_delete.assert_called_once_with(
                        [
                            o_mock_offering_1,
                            o_mock_offering_2,
                            o_configuration,
                        ],
                        f_before_delete,
                    )
                    o_mock_list.assert_called_once_with()

    def test_edit(self) -> None:
        """test de edit"""
        # Test complet (clef existantes conservées, clef nouvelles ajoutées, clef éditées modifiées)
        d_entity: Dict[str, Any] = {
            "key": "val",
            "comm_key": "origine",
            "type_infos": {"kept_key": "kept_value", "other_key": "value_1", "used_data": [{"nom": "or-1"}, {"nom": "or-2"}, {"nom": "or-3"}]},
        }
        d_edit: Dict[str, Any] = {"_id": "1", "comm_key": "edit", "type_infos": {"other_key": "value_2", "new_key": "n k", "used_data": [{"nom": "val_new"}, {}, {"new": "val"}]}}
        d_fusion: Dict[str, Any] = {
            **d_entity,
            **d_edit,
            **{"type_infos": {"kept_key": "kept_value", "new_key": "n k", "other_key": "value_2", "used_data": [{"nom": "val_new"}, {"nom": "or-2"}, {"nom": "or-3", "new": "val"}]}},
        }
        o_entity = Configuration(d_entity)
        with patch.object(Configuration, "api_full_edit", return_value=None) as o_mock_api_edit:
            o_entity.edit(d_edit)
            o_mock_api_edit.assert_called_once_with(d_fusion)

        # le nombre de used_data ne correspond pas
        d_edit = {"_id": "1", "comm_key": "edit", "type_infos": {"used_data": [{"nom": "val_new"}]}}
        with self.assertRaises(StoreEntityError) as o_raise:
            o_entity.edit(d_edit)
        s_message = "Edition impossible, le nombre de 'used_data' ne correspond pas."
        self.assertEqual(s_message, o_raise.exception.message)

        # Ok si pas de type_infos (dans d_edit)
        o_entity = Configuration(d_entity)
        d_edit = {"_id": "1", "comm_key": "edit", "new_key": "new_key"}
        with patch.object(Configuration, "api_full_edit", return_value=None) as o_mock_api_edit:
            o_entity.edit(d_edit)
            o_mock_api_edit.assert_called_once_with({**d_entity, **d_edit})

        # Ok si pas de type_infos.used_data (dans d_edit)
        o_entity = Configuration(d_entity)
        d_edit = {"_id": "1", "comm_key": "edit", "new_key": "new_key", "type_infos": {"new_key": "new_key", "other_key": "value_2"}}
        with patch.object(Configuration, "api_full_edit", return_value=None) as o_mock_api_edit:
            o_entity.edit(d_edit)
            o_mock_api_edit.assert_called_once_with({**d_entity, **d_edit})
