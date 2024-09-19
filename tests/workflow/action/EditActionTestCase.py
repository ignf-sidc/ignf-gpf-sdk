#!/usr/bin/env python3

# cSpell:ignore operateur

from typing import Any, Dict
from unittest.mock import MagicMock, call, patch
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.interface.TagInterface import TagInterface
from sdk_entrepot_gpf.store.interface.CommentInterface import CommentInterface
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.EditAction import EditAction

from tests.GpfTestCase import GpfTestCase


class EditActionTestCase(GpfTestCase):
    """Tests EditAction class.

    cmd : python3 -m unittest -b tests.workflow.action.EditActionTestCase
    """

    def test_run_ko(self) -> None:
        """test pour la fonction run() sortie en erreur"""
        s_datastore = "datastore"

        # problème de avec le workflow : entity_type non présent
        d_action: Dict[str, Any] = {"type": "edit-entity"}
        o_action_delete = EditAction("contexte", d_action)
        with self.assertRaises(StepActionError) as o_err:
            o_action_delete.run(s_datastore)
        self.assertEqual('La clef "entity_type" est obligatoire pour cette action', o_err.exception.message)

        # problème de avec le workflow : entity_type non valide
        d_action = {"type": "edit-entity", "entity_type": "non valide"}
        o_action_delete = EditAction("contexte", d_action)
        with self.assertRaises(StepActionError) as o_err:
            o_action_delete.run(s_datastore)
        self.assertEqual(f"Type {d_action['entity_type']} non reconnu. Types valides : {', '.join(EditAction.UPDATABLE_TYPES)}", o_err.exception.message)

        # problème de avec le workflow : entity_type non valide
        d_action = {"type": "edit-entity", "entity_type": "offering"}
        o_action_delete = EditAction("contexte", d_action)
        with self.assertRaises(StepActionError) as o_err:
            o_action_delete.run(s_datastore)
        self.assertEqual('La clef "entity_id" est obligatoire pour cette action.', o_err.exception.message)

    def test_run_ok(self) -> None:  # pylint: disable=too-many-locals,too-many-statements
        """test pour la fonction run() sortie sans erreur"""
        s_datastore = "datastore"
        s_entity_id = "entity_id"
        for c_classe in [Upload, StoredData, Configuration, Offering]:
            # ne fait rien
            o_entity = MagicMock(spec=c_classe)
            d_action: Dict[str, Any] = {"type": "edit-entity", "entity_type": c_classe.entity_name(), "entity_id": s_entity_id}
            o_action_delete = EditAction("contexte", d_action)
            with patch.object(c_classe, "api_get", return_value=o_entity) as o_mock_api_get:
                o_action_delete.run(s_datastore)
            o_mock_api_get.assert_called_once_with(s_entity_id, datastore=s_datastore)
            o_entity.edit.assert_not_called()
            if isinstance(o_entity, TagInterface):
                o_entity.api_add_tags.assert_not_called()
            if isinstance(o_entity, CommentInterface):
                o_entity.api_add_comment.assert_not_called()

            # edition entity seule
            o_entity = MagicMock(spec=c_classe)
            d_action = {"type": "edit-entity", "entity_type": c_classe.entity_name(), "entity_id": s_entity_id, "body_parameters": {"key": "val"}}
            o_action_delete = EditAction("contexte", d_action)
            with patch.object(c_classe, "api_get", return_value=o_entity) as o_mock_api_get:
                o_action_delete.run(s_datastore)
            o_mock_api_get.assert_called_once_with(s_entity_id, datastore=s_datastore)
            o_entity.edit.assert_called_once_with(d_action["body_parameters"])
            if isinstance(o_entity, TagInterface):
                o_entity.api_add_tags.assert_not_called()
            if isinstance(o_entity, CommentInterface):
                o_entity.api_add_comment.assert_not_called()

            # edition entity + comments + tags
            o_entity = MagicMock(spec=c_classe)
            d_action = {
                "type": "edit-entity",
                "entity_type": c_classe.entity_name(),
                "entity_id": s_entity_id,
                "body_parameters": {"key": "val"},
                "tags": {"key1": "val1", "key2": "val2"},
                "comments": ["comm1", "comm2"],
            }
            o_action_delete = EditAction("contexte", d_action)
            with patch.object(c_classe, "api_get", return_value=o_entity) as o_mock_api_get:
                o_action_delete.run(s_datastore)
            o_mock_api_get.assert_called_once_with(s_entity_id, datastore=s_datastore)
            o_entity.edit.assert_called_once_with(d_action["body_parameters"])
            if isinstance(o_entity, TagInterface):
                o_entity.api_add_tags.assert_called_once_with(d_action["tags"])
            if isinstance(o_entity, CommentInterface):
                # o_entity.api_add_comment.
                self.assertEqual(o_entity.api_add_comment.call_args_list, [call({"text": s_comm}) for s_comm in d_action["comments"]])
