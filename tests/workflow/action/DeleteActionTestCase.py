#!/usr/bin/env python3

# cSpell:ignore operateur

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from sdk_entrepot_gpf.io.Errors import NotFoundError
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.DeleteAction import DeleteAction

from tests.GpfTestCase import GpfTestCase


class DeleteActionTestCase(GpfTestCase):
    """Tests DeleteAction class.

    cmd : python3 -m unittest -b tests.workflow.action.DeleteActionTestCase
    """

    def test_run_ko(self) -> None:
        """test pour la fonction run() sortie en erreur"""
        s_datastore = "datastore"

        # problème de avec le workflow : entity_type non présent
        d_action: Dict[str, Any] = {"type": "delete-entity"}
        o_action_delete = DeleteAction("contexte", d_action)
        with self.assertRaises(StepActionError) as o_err:
            o_action_delete.run()
        self.assertEqual('La clef "entity_type" est obligatoire pour cette action', o_err.exception.message)

        # problème de avec le workflow : entity_type non valide
        d_action = {"type": "delete-entity", "entity_type": "non valide"}
        o_action_delete = DeleteAction("contexte", d_action)
        with self.assertRaises(StepActionError) as o_err:
            o_action_delete.run()
        self.assertEqual(f"Type {d_action['entity_type']} non reconnu. Types valides : {', '.join(DeleteAction.DELETABLE_TYPES)}", o_err.exception.message)

        # problème de avec le workflow : il manque "entity_id", "filter_infos", "filter_tags"
        d_action = {"type": "delete-entity", "entity_type": "offering"}
        o_action_delete = DeleteAction("contexte", d_action)
        with self.assertRaises(StepActionError) as o_err:
            o_action_delete.run()
        self.assertEqual('Il faut au moins une des clefs suivantes : "entity_id", "filter_infos", "filter_tags" pour cette action.', o_err.exception.message)

        s_entity_id = "entity_id"
        for c_classe in [Upload, StoredData, Configuration, Offering]:
            print(c_classe.entity_name())
            # rien trouvé avec les filtres
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "filter_infos": {"nom": "name"}, "filter_tags": {"tag1": "val1"}}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_list", return_value=[]) as o_mock_api_list:
                with self.assertRaises(StepActionError) as o_err:
                    o_action_delete.run(s_datastore)
            self.assertEqual("Aucune entité trouvée pour la suppression", o_err.exception.message)
            o_mock_api_list.assert_called_once_with(d_action.get("filter_infos"), d_action.get("filter_tags"), datastore=s_datastore)

            # rien trouvé avec "entity_id"
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "entity_id": s_entity_id}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_get", side_effect=NotFoundError("", "", None, None, "")) as o_mock_api_list:
                with self.assertRaises(StepActionError) as o_err:
                    o_action_delete.run(s_datastore)
            self.assertEqual("Aucune entité trouvée pour la suppression", o_err.exception.message)
            o_mock_api_list.assert_called_once_with(s_entity_id, datastore=s_datastore)

        d_action = {"type": "delete-entity", "entity_type": "offering", "filter_infos": {"nom": "name"}, "filter_tags": {"tag1": "val1"}, "if_multi": "error"}
        o_action_delete = DeleteAction("contexte", d_action)
        l_entities = [MagicMock(), MagicMock(), MagicMock()]
        with patch.object(Offering, "api_list", return_value=l_entities) as o_mock_api_list:
            with self.assertRaises(StepActionError) as o_err:
                o_action_delete.run(s_datastore)
        self.assertEqual(f"Plusieurs entités trouvées pour la suppression : {l_entities}", o_err.exception.message)
        o_mock_api_list.assert_called_once_with(d_action.get("filter_infos"), d_action.get("filter_tags"), datastore=s_datastore)

    def test_run_ok(self) -> None:  # pylint: disable=too-many-locals,too-many-statements
        """test pour la fonction run() sortie sans erreur"""
        s_datastore = "datastore"
        s_entity_id = "entity_id"
        for c_classe in [Upload, StoredData, Configuration, Offering]:
            # Aucune entité mais c'est OK
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "filter_infos": {"nom": "name"}, "filter_tags": {"tag1": "val1"}, "if_multi": "error", "not_found_ok": True}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_list", return_value=[]) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities", return_value=[]) as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_api_list.assert_called_once_with(d_action.get("filter_infos"), d_action.get("filter_tags"), datastore=s_datastore)
            o_mock_delete.assert_not_called()

            # suppression avec entity_id
            o_entity = MagicMock()
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "entity_id": s_entity_id}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_get", return_value=o_entity) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities", return_value=[]) as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_api_list.assert_called_once_with(s_entity_id, datastore=s_datastore)
            o_mock_delete.assert_called_once_with([o_entity], DeleteAction.question_before_delete)
            o_entity.get_liste_deletable_cascade.assert_not_called()

            # suppression avec entity_id en cascade
            o_entity = MagicMock()
            l_cascade = [MagicMock(), MagicMock()]
            o_entity.get_liste_deletable_cascade.return_value = l_cascade
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "entity_id": s_entity_id, "cascade": True}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_get", return_value=o_entity) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities") as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_api_list.assert_called_once_with(s_entity_id, datastore=s_datastore)
            o_mock_delete.assert_called_once_with(l_cascade, DeleteAction.question_before_delete)
            o_entity.get_liste_deletable_cascade.assert_called_once_with()

            # suppression avec les filtres
            o_entity_1 = MagicMock()
            o_entity_2 = MagicMock()
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "filter_infos": {"nom": "name"}, "filter_tags": {"tag1": "val1"}}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_list", return_value=[o_entity_1, o_entity_2]) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities", return_value=[]) as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_delete.assert_called_once_with([o_entity_1, o_entity_2], DeleteAction.question_before_delete)
            o_mock_api_list.assert_called_once_with(d_action.get("filter_infos"), d_action.get("filter_tags"), datastore=s_datastore)
            o_entity_1.get_liste_deletable_cascade.assert_not_called()
            o_entity_2.get_liste_deletable_cascade.assert_not_called()

            # suppression avec les filtres cascade
            o_entity_1 = MagicMock()
            l_cascade = [MagicMock(), MagicMock()]
            o_entity_1.get_liste_deletable_cascade.return_value = l_cascade
            o_entity_2 = MagicMock()
            o_entity_2.get_liste_deletable_cascade.return_value = l_cascade
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "filter_infos": {"nom": "name"}, "filter_tags": {"tag1": "val1"}, "cascade": True}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_list", return_value=[o_entity_1, o_entity_2]) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities", return_value=[]) as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_delete.assert_called_once_with(l_cascade * 2, DeleteAction.question_before_delete)
            o_mock_api_list.assert_called_once_with(d_action.get("filter_infos"), d_action.get("filter_tags"), datastore=s_datastore)
            o_entity_1.get_liste_deletable_cascade.assert_called_once_with()
            o_entity_2.get_liste_deletable_cascade.assert_called_once_with()

            # suppression avec les filtres avec "if_multi": "first"
            o_entity_1 = MagicMock()
            o_entity_2 = MagicMock()
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "filter_infos": {"nom": "name"}, "filter_tags": {"tag1": "val1"}, "if_multi": "first"}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_list", return_value=[o_entity_1, o_entity_2]) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities", return_value=[]) as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_delete.assert_called_once_with([o_entity_1], DeleteAction.question_before_delete)
            o_mock_api_list.assert_called_once_with(d_action.get("filter_infos"), d_action.get("filter_tags"), datastore=s_datastore)
            o_entity_1.get_liste_deletable_cascade.assert_not_called()
            o_entity_2.get_liste_deletable_cascade.assert_not_called()

            # suppression avec entity_id
            o_entity = MagicMock()
            d_action = {"type": "delete-entity", "entity_type": c_classe.entity_name(), "entity_id": s_entity_id, "confirm": False}
            o_action_delete = DeleteAction("contexte", d_action)
            with patch.object(c_classe, "api_get", return_value=o_entity) as o_mock_api_list:
                with patch.object(StoreEntity, "delete_liste_entities", return_value=[]) as o_mock_delete:
                    o_action_delete.run(s_datastore)
            o_mock_api_list.assert_called_once_with(s_entity_id, datastore=s_datastore)
            o_mock_delete.assert_called_once_with([o_entity], DeleteAction.print_before_delete)
            o_entity.get_liste_deletable_cascade.assert_not_called()

    def test_question_before_delete(self) -> None:
        """test de question_before_delete"""
        # on force le type pour pylint
        l_entity: List[StoreEntity] = [MagicMock(spec=StoreEntity), MagicMock(spec=StoreEntity)]
        # réponse oui
        with patch("builtins.input", lambda: "o"):
            l_res = DeleteAction.question_before_delete(l_entity)
        self.assertListEqual(l_entity, l_res)

        # réponse non
        with patch("builtins.input", lambda: "n"):
            l_res = DeleteAction.question_before_delete(l_entity)
        self.assertListEqual([], l_res)

    def test_print_before_delete(self) -> None:
        """test de print_before_delete"""
        # on force le type pour pylint
        l_entity: List[StoreEntity] = [MagicMock(), MagicMock()]
        l_res = DeleteAction.print_before_delete(l_entity)
        self.assertListEqual(l_entity, l_res)
