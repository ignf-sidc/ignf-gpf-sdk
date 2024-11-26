# mypy: disable-error-code="attr-defined"
import time
from typing import Any, Dict, List

from unittest.mock import PropertyMock, call, patch, MagicMock

from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.workflow.action.ProcessingExecutionAction import ProcessingExecutionAction
from sdk_entrepot_gpf.Errors import GpfSdkError
from tests.GpfTestCase import GpfTestCase

# cSpell:ignore datasheet vectordb creat


# pylint:disable=too-many-arguments
# pylint:disable=too-many-locals
# pylint:disable=too-many-branches
# pylint:disable=too-many-statements, too-many-lines
class ProcessingExecutionActionTestCase(GpfTestCase):
    """Tests ProcessingExecutionAction class.

    cmd : python3 -m unittest -b tests.workflow.action.ProcessingExecutionActionTestCase
    """

    i = 0

    def test_find_stored_data(self) -> None:
        """Test find_stored_data."""
        o_pe1 = ProcessingExecution({"_id": "pe_1"})
        o_pe2 = ProcessingExecution({"_id": "pe_2"})
        # création du dict décrivant l'action
        d_action: Dict[str, Any] = {
            "type": "processing-execution",
            "body_parameters": {
                "output": {
                    "stored_data": {"name": "name_stored_data"},
                },
            },
            "tags": {"tag": "val"},
        }
        # exécution de ProcessingExecutionAction
        o_ua = ProcessingExecutionAction("contexte", d_action)

        for s_datastore in [None, "datastore"]:
            ## execution sans datastore
            # Mock de ActionAbstract.get_filters et Upload.api_list
            with patch.object(ActionAbstract, "get_filters", return_value=({"info": "val"}, {"tag": "val"})) as o_mock_get_filters:
                with patch.object(StoredData, "api_list", return_value=[o_pe1, o_pe2]) as o_mock_api_list:
                    # Appel de la fonction find_stored_data
                    o_stored_data = o_ua.find_stored_data(s_datastore)
                    # Vérifications
                    o_mock_get_filters.assert_called_once_with("processing_execution", d_action["body_parameters"]["output"]["stored_data"], d_action["tags"])
                    o_mock_api_list.assert_called_once_with(infos_filter={"info": "val"}, tags_filter={"tag": "val"}, datastore=s_datastore)
                    self.assertEqual(o_stored_data, o_pe1)
        # pas de stored data trouvé
        with patch.object(ActionAbstract, "get_filters", return_value=({"info": "val"}, {"tag": "val"})) as o_mock_get_filters:
            with patch.object(StoredData, "api_list", return_value=[]) as o_mock_api_list:
                # Appel de la fonction find_stored_data
                o_stored_data = o_ua.find_stored_data(s_datastore)
                # Vérifications
                o_mock_get_filters.assert_called_once_with("processing_execution", d_action["body_parameters"]["output"]["stored_data"], d_action["tags"])
                o_mock_api_list.assert_called_once_with(infos_filter={"info": "val"}, tags_filter={"tag": "val"}, datastore=s_datastore)
                self.assertEqual(o_stored_data, None)

    # pylint: disable=protected-access
    def test_gestion_update_entity(self) -> None:
        """test de __gestion_update_entity"""
        s_datastore = "update"
        s_behavior = ProcessingExecutionAction.BEHAVIOR_STOP

        # cas non pris en compte
        l_action: List[Dict[str, Any]] = [
            {"body_parameters": {}},
            {"body_parameters": {"output": {}}},
            {"body_parameters": {"output": {"upload": {}}}},
            {"body_parameters": {"output": {"stored_data": {"name": ""}}}},
        ]
        for d_action in l_action:
            o_pea = ProcessingExecutionAction("contexte", d_action, behavior=s_behavior)
            with patch.object(StoredData, "api_get") as o_mock_api_get:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_not_called()

        # pas de stored_data
        s_id = "uuid"
        d_action = {"body_parameters": {"output": {"stored_data": {"_id": s_id}}, "processing": "id_processing", "inputs": {"stored_data": ["id_1", "id_2"]}, "parameters": {"param1": "val1"}}}
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=s_behavior)
        with patch.object(StoredData, "api_get", return_value=None) as o_mock_api_get:
            with self.assertRaises(GpfSdkError) as e_err:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
            o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
            self.assertEqual(e_err.exception.message, "La donnée en sortie est introuvable, impossible de faire la mise à jour.")

        # pas de traitement correspondant trouvé
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[]) as o_mock_api_list:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
        # les traitements ne correspondent pas
        o_pe_1 = MagicMock()  # input upload
        o_pe_1.get_store_properties.return_value = {"inputs": {"upload": [{"_id": "uuid"}]}}
        o_pe_2 = MagicMock()  # input stored_data not match
        o_pe_2.get_store_properties.return_value = {"inputs": {"stored_data": [{"_id": "uuid"}]}}
        o_pe_3 = MagicMock()  # input stored_data match + param not match
        o_pe_3.get_store_properties.return_value = {"inputs": {"stored_data": [{"_id": "id_1"}, {"_id": "id_2"}]}, "parameters": {"autre": "val"}}

        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3]) as o_mock_api_list:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
        o_pe_4 = MagicMock()  # input stored_data match + param not match
        o_pe_4.get_store_properties.return_value = {"inputs": {"stored_data": [{"_id": "id_1"}, {"_id": "id_2"}]}, "parameters": d_action["body_parameters"]["parameters"]}

        # BEHAVIOR_STOP
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                    o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                    d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                    o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
                    self.assertEqual(e_err.exception.message, f"Le traitement a déjà été lancée pour mettre à jour cette donnée {o_pe_4}.")

        # BEHAVIOR_DELETE
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=ProcessingExecutionAction.BEHAVIOR_DELETE)
        o_pe_4.get_store_properties.return_value = {
            "inputs": {"stored_data": [{"_id": "id_1"}, {"_id": "id_2"}]},
            "parameters": d_action["body_parameters"]["parameters"],
            "status": ProcessingExecution.STATUS_FAILURE,
        }
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
                self.assertIsNone(o_pea.processing_execution)
                self.assertIsNone(o_pea.stored_data)

        # BEHAVIOR_RESUME + STATUS_FAILURE
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
                self.assertIsNone(o_pea.processing_execution)
                self.assertIsNone(o_pea.stored_data)

        # BEHAVIOR_RESUME + not STATUS_FAILURE
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        o_pe_4.get_store_properties.return_value = {
            "inputs": {"stored_data": [{"_id": "id_1"}, {"_id": "id_2"}]},
            "parameters": d_action["body_parameters"]["parameters"],
            "status": ProcessingExecution.STATUS_CREATED,
        }
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
                self.assertEqual(o_pea.processing_execution, o_pe_4)
                self.assertEqual(o_pea.stored_data, o_mock_api_get.return_value)

        # BEHAVIOR_RESUME + not STATUS_FAILURE, stored_data unstable
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            o_mock_api_get.return_value.__getitem__.return_value = StoredData.STATUS_UNSTABLE
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                self.assertEqual(
                    e_err.exception.message,
                    (
                        f"Le traitement précédent a échoué sur la donnée stockée en sortie {o_mock_api_get.return_value}. "
                        "Impossible de lancer le traitement demandé : contactez le support de l'Entrepôt Géoplateforme "
                        "pour faire réinitialiser son statut."
                    ),
                )

        # BEHAVIOR_CONTINUE + not STATUS_FAILURE
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=ProcessingExecutionAction.BEHAVIOR_CONTINUE)
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                o_mock_api_get.assert_called_once_with(s_id, datastore=s_datastore)
                d_filter = {"output_stored_data": o_mock_api_get.return_value.id, "processing": d_action["body_parameters"]["processing"], "input_stored_data": "id_1"}
                o_mock_api_list.assert_called_once_with(d_filter, datastore=s_datastore)
                self.assertEqual(o_pea.processing_execution, o_pe_4)
                self.assertEqual(o_pea.stored_data, o_mock_api_get.return_value)
        # BEHAVIOR_CONTINUE + not STATUS_FAILURE, stored_data unstable
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=ProcessingExecutionAction.BEHAVIOR_CONTINUE)
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            o_mock_api_get.return_value.__getitem__.return_value = StoredData.STATUS_UNSTABLE
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                self.assertEqual(
                    e_err.exception.message,
                    (
                        f"Le traitement précédent a échoué sur la donnée stockée en sortie {o_mock_api_get.return_value}. "
                        "Impossible de lancer le traitement demandé : contactez le support de l'Entrepôt Géoplateforme "
                        "pour faire réinitialiser son statut."
                    ),
                )

        # behavior non valide
        s_behavior = "toto"
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior=s_behavior)
        with patch.object(StoredData, "api_get") as o_mock_api_get:
            o_mock_api_get.return_value.__getitem__.return_value = StoredData.STATUS_UNSTABLE
            with patch.object(ProcessingExecution, "api_list", return_value=[o_pe_1, o_pe_2, o_pe_3, o_pe_4]) as o_mock_api_list:
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_update_entity(s_datastore)  # type: ignore
                self.assertEqual(
                    e_err.exception.message, f"Le comportement {s_behavior} n'est pas reconnu ({'|'.join(ProcessingExecutionAction.BEHAVIORS)}), l'exécution de traitement n'est pas possible."
                )

    def test_init(self) -> None:
        """test de __init__"""
        d_action: Dict[str, Any] = {"type": "processing-execution"}

        # behavior défini et compatibility_cartes défini
        with patch.object(Config, "get_str", return_value="config") as o_mock_get_str:
            with patch.object(Config, "get_bool", return_value=False) as o_mock_get_bool:
                o_pe = ProcessingExecutionAction("contexte", d_action, behavior="STOP", compatibility_cartes=True)
                self.assertEqual(o_pe._ProcessingExecutionAction__behavior, "STOP")
                self.assertEqual(o_pe._ProcessingExecutionAction__mode_cartes, True)
                o_mock_get_str.assert_not_called()
                o_mock_get_bool.assert_not_called()

        # behavior config et compatibility_cartes défini
        with patch.object(Config, "get_str", return_value="config") as o_mock_get_str:
            with patch.object(Config, "get_bool", return_value=False) as o_mock_get_bool:
                o_pe = ProcessingExecutionAction("contexte", d_action, behavior=None, compatibility_cartes=True)
                self.assertEqual(o_pe._ProcessingExecutionAction__behavior, "config")
                self.assertEqual(o_pe._ProcessingExecutionAction__mode_cartes, True)
                o_mock_get_str.assert_called_once_with("processing_execution", "behavior_if_exists")
                o_mock_get_bool.assert_not_called()

        # behavior config et compatibility_cartes config
        with patch.object(Config, "get_str", return_value="config") as o_mock_get_str:
            with patch.object(Config, "get_bool", return_value=False) as o_mock_get_bool:
                o_pe = ProcessingExecutionAction("contexte", d_action, behavior=None, compatibility_cartes=None)
                self.assertEqual(o_pe._ProcessingExecutionAction__behavior, "config")
                self.assertEqual(o_pe._ProcessingExecutionAction__mode_cartes, False)
                o_mock_get_str.assert_called_once_with("processing_execution", "behavior_if_exists")
                o_mock_get_bool.assert_called_once_with("compatibility_cartes", "activate")

    # pylint: disable=protected-access
    def test_add_tags(self) -> None:
        """test de __add_tags"""
        o_processing_execution = MagicMock()
        d_def: Dict[str, Any] = {"type": "processing-execution"}
        o_pe = ProcessingExecutionAction("contexte", d_def)
        o_pe._ProcessingExecutionAction__mode_cartes = False
        o_pe._ProcessingExecutionAction__processing_execution = o_processing_execution
        o_pe._ProcessingExecutionAction__no_output = False

        # pas de tags
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_upload.return_value.api_add_tags.assert_not_called()
                o_mock_stored_data.return_value.api_add_tags.assert_not_called()
                # dict vide
                d_def["tags"] = {}
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_upload.return_value.api_add_tags.assert_not_called()
                o_mock_stored_data.return_value.api_add_tags.assert_not_called()

        # pas de output
        d_tags = {"key": "val"}
        d_def["tags"] = d_tags
        o_pe._ProcessingExecutionAction__no_output = True
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_upload.return_value.api_add_tags.assert_not_called()
                o_mock_stored_data.return_value.api_add_tags.assert_not_called()

        # sortie upload
        o_pe._ProcessingExecutionAction__no_output = False
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_upload.return_value.api_add_tags.assert_called_once_with(d_tags)
                o_mock_stored_data.return_value.api_add_tags.assert_not_called()

        # sortie stored_data
        o_pe._ProcessingExecutionAction__no_output = False
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None):
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_stored_data.return_value.api_add_tags.assert_called_once_with(d_tags)

        # autre type de sortie => Erreur
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None):
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock, return_value=None):
                with self.assertRaises(StepActionError) as o_err_step:
                    o_pe._ProcessingExecutionAction__add_tags()
                self.assertEqual(o_err_step.exception.message, "ni upload ni stored-data trouvé. Impossible d'ajouter les tags")

        # compatibility_cartes
        del d_def["tags"]
        o_pe._ProcessingExecutionAction__mode_cartes = True

        ## pas de tag ajouté (cas traitement non pris en compte)
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_upload.return_value.api_add_tags.assert_not_called()
                o_mock_stored_data.return_value.api_add_tags.assert_not_called()

        ## mise_en_base : manque datasheet_name
        d_def["tags"] = d_tags
        o_processing_execution.get_store_properties.return_value = {"processing": {"_id": "id_mise_en_base"}}
        o_pe._ProcessingExecutionAction__no_output = False
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                with self.assertRaises(GpfSdkError) as e_err_comp:
                    o_pe._ProcessingExecutionAction__add_tags()
                self.assertEqual(e_err_comp.exception.message, "Mode compatibility_cartes activé, il faut obligatoirement définir le tag 'datasheet_name'")
        ## mise_en_base : manque inputs
        d_def["tags"] = {**d_tags, "datasheet_name": "name"}
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                with self.assertRaises(GpfSdkError) as e_err_comp:
                    o_pe._ProcessingExecutionAction__add_tags()
                self.assertEqual(e_err_comp.exception.message, "Intégration de données vecteur livrées en base : input and output obligatoires")
        ## mise_en_base : manque stored_data sortie
        l_inputs_upload = [MagicMock(id=1), MagicMock(id=2)]
        o_pe._ProcessingExecutionAction__inputs_upload = l_inputs_upload
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock, return_value=None) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                with self.assertRaises(GpfSdkError) as e_err_comp:
                    o_pe._ProcessingExecutionAction__add_tags()
                self.assertEqual(e_err_comp.exception.message, "Intégration de données vecteur livrées en base : input and output obligatoires")
        ## mise_en_base : OK
        d_def["tags"] = {**d_tags, "datasheet_name": "name"}
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                # on appelle la méthode privée __add_tags :
                o_pe._ProcessingExecutionAction__add_tags()
                for o_upload in l_inputs_upload:
                    # test sur le nombre d'appels :
                    self.assertEqual(o_upload.api_add_tags.call_count, 2)
                    # test sur les paramètres passés :
                    d_traitement = {"proc_int_id": o_processing_execution.id, "vectordb_id": o_mock_stored_data.return_value.id}
                    d_etape = {"integration_progress": '{"send_files_api": "successful", "wait_checks": "successful","integration_processing": "in_progress"}', "integration_current_step": "2"}
                    o_upload.api_add_tags.assert_has_calls([call(d_traitement), call(d_etape)])
                o_mock_stored_data.return_value.api_add_tags.assert_called_once_with({**d_tags, "datasheet_name": "name", "uuid_upload": l_inputs_upload[0].id})

        ## pyramide_vecteur : manque datasheet_name
        d_def["tags"] = d_tags
        o_processing_execution.get_store_properties.return_value = {"processing": {"_id": "id_pyramide_vecteur"}}
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                with self.assertRaises(GpfSdkError) as e_err_comp:
                    o_pe._ProcessingExecutionAction__add_tags()
                self.assertEqual(e_err_comp.exception.message, "Mode compatibility_cartes activé, il faut obligatoirement définir le tag 'datasheet_name'")
        ## pyramide_vecteur : manque inputs
        d_def["tags"] = {**d_tags, "datasheet_name": "name"}
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                with self.assertRaises(GpfSdkError) as e_err_comp:
                    o_pe._ProcessingExecutionAction__add_tags()
            self.assertEqual(e_err_comp.exception.message, "Création de pyramide vecteur : input and output obligatoires")
        ## pyramide_vecteur : maque stored_data sortie
        l_inputs_stored_data = [MagicMock(id=1), MagicMock(id=2)]
        o_pe._ProcessingExecutionAction__inputs_stored_data = l_inputs_stored_data
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock, return_value=None) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                with self.assertRaises(GpfSdkError) as e_err_comp:
                    o_pe._ProcessingExecutionAction__add_tags()
            self.assertEqual(e_err_comp.exception.message, "Création de pyramide vecteur : input and output obligatoires")

        ## pyramide_vecteur : OK
        d_def["tags"] = {**d_tags, "datasheet_name": "name"}
        with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                o_pe._ProcessingExecutionAction__add_tags()
                o_mock_stored_data.return_value.api_add_tags.assert_called_once_with(
                    {**d_tags, "datasheet_name": "name", "vectordb_id": l_inputs_stored_data[0].id, "proc_pyr_creat_id": o_processing_execution.id}
                )

    def test_add_comments(self) -> None:
        """test de __add_comments"""
        d_def: Dict[str, Any] = {}
        o_pe = ProcessingExecutionAction("contexte", d_def)
        o_pe._ProcessingExecutionAction__no_output = False

        # pas de commentaires
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_comments()
                o_mock_upload.return_value.api_add_comment.assert_not_called()
                o_mock_stored_data.return_value.api_add_comment.assert_not_called()

        # pas de sortie
        l_comments = ["commentaire1", "commentaire2"]
        d_def["comments"] = l_comments
        o_pe._ProcessingExecutionAction__no_output = True
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_pe._ProcessingExecutionAction__add_comments()
                o_mock_upload.return_value.api_add_comment.assert_not_called()
                o_mock_stored_data.return_value.api_add_comment.assert_not_called()

        # commentaire sur l'upload, pas de commentaire initial
        o_pe._ProcessingExecutionAction__no_output = False
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_mock_upload.return_value.api_list_comments.return_value = []
                o_pe._ProcessingExecutionAction__add_comments()
                for s_comment in l_comments:
                    o_mock_upload.return_value.api_add_comment.assert_any_call({"text": s_comment})
                o_mock_stored_data.return_value.api_add_comment.assert_not_called()

        # commentaire sur l'upload, x commentaire initial
        l_init_comments = ["init1", "init2"]
        d_def["comments"] = l_comments + l_init_comments
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_mock_upload.return_value.api_list_comments.return_value = [{"text": s_comment} for s_comment in l_init_comments]
                o_pe._ProcessingExecutionAction__add_comments()
                for s_comment in l_comments:
                    o_mock_upload.return_value.api_add_comment.assert_any_call({"text": s_comment})
                o_mock_stored_data.return_value.api_add_comment.assert_not_called()

        # commentaire sur l'stored_data, pas de commentaire initial
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_mock_stored_data.return_value.api_list_comments.return_value = []
                o_pe._ProcessingExecutionAction__add_comments()
                for s_comment in l_comments:
                    o_mock_stored_data.return_value.api_add_comment.assert_any_call({"text": s_comment})

        # commentaire sur l'stored_data, x commentaire initial
        l_init_comments = ["init1", "init2"]
        d_def["comments"] = l_comments + l_init_comments
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None) as o_mock_upload:
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_stored_data:
                o_mock_stored_data.return_value.api_list_comments.return_value = [{"text": s_comment} for s_comment in l_init_comments]
                o_pe._ProcessingExecutionAction__add_comments()
                for s_comment in l_comments:
                    o_mock_stored_data.return_value.api_add_comment.assert_any_call({"text": s_comment})

        # aucune sortie valable
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None):
            with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock, return_value=None):
                with self.assertRaises(StepActionError) as e_err:
                    o_pe._ProcessingExecutionAction__add_comments()
                self.assertEqual(e_err.exception.message, "ni upload ni stored-data trouvé. Impossible d'ajouter les commentaires")

    def test_launch(self) -> None:
        """test de __launch"""
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_STOP)

        # aucune processing execution
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(StepActionError) as e_err:
                o_pea._ProcessingExecutionAction__launch()
            self.assertEqual(e_err.exception.message, "Aucune exécution de traitement trouvée. Impossible de lancer le traitement")

        def get_items_processing(key: str) -> Any:
            if key == "status":
                return "CREATED"
            return MagicMock()

        # pas encore lancé
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock) as o_mock_pe:
            o_mock_pe.return_value.__getitem__.side_effect = get_items_processing
            o_pea._ProcessingExecutionAction__launch()
            o_mock_pe.return_value.api_launch.assert_called_once_with()

        # déjà lancé behavior non compatible
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock):
            with self.assertRaises(StepActionError) as e_err:
                o_pea._ProcessingExecutionAction__launch()
            self.assertEqual(e_err.exception.message, "L'exécution de traitement est déjà lancée.")

        # déjà lancé behavior OK
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_CONTINUE)
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock) as o_mock_pe:
            o_pea._ProcessingExecutionAction__launch()
            o_mock_pe.return_value.api_launch.assert_not_called()
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock) as o_mock_pe:
            o_pea._ProcessingExecutionAction__launch()
            o_mock_pe.return_value.api_launch.assert_not_called()

    def test_gestion_new_output(self) -> None:
        """test de __gestion_new_output"""
        s_datastore = "datastore"
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_STOP)

        # pas de stored_data de trouvé
        with patch.object(ProcessingExecutionAction, "find_stored_data", return_value=None) as o_mock_find_stored_data:
            o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
            o_mock_find_stored_data.assert_called_once_with(s_datastore)

        # stored_data + behavior STOP
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            with self.assertRaises(GpfSdkError) as e_err:
                o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
                o_mock_find_stored_data.assert_called_once_with(s_datastore)
            self.assertEqual(e_err.exception.message, f"Impossible de créer l’exécution de traitement, une donnée stockée en sortie équivalente {o_mock_find_stored_data.return_value} existe déjà.")

        # behavior delete
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_DELETE)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
            o_mock_find_stored_data.assert_called_once_with(s_datastore)
            o_mock_find_stored_data.return_value.api_delete.assert_called_once_with()
            self.assertIsNone(o_pea.processing_execution)

        # behavior continue - unstable
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_CONTINUE)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            with patch.object(ProcessingExecution, "api_list") as o_mock_api_list:
                o_mock_find_stored_data.return_value.__getitem__.return_value = StoredData.STATUS_UNSTABLE
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
                o_mock_find_stored_data.assert_called_once_with(s_datastore)
                o_mock_api_list.assert_not_called()
                self.assertEqual(
                    e_err.exception.message, f"Le traitement précédent a échoué sur la donnée stockée en sortie {o_mock_find_stored_data.return_value}. Impossible de lancer le traitement demandé."
                )

        # behavior continue - stable - ProcessingExecution non trouvé
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_CONTINUE)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            l_pe: List[ProcessingExecution] = []
            with patch.object(ProcessingExecution, "api_list", return_value=l_pe) as o_mock_api_list:
                o_mock_find_stored_data.return_value.__getitem__.return_value = "OK"
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
                o_mock_find_stored_data.assert_called_once_with(s_datastore)
                self.assertEqual(o_pea.stored_data, o_mock_find_stored_data.return_value)
                o_mock_api_list.assert_called_once_with({"output_stored_data": o_mock_find_stored_data.return_value.id}, datastore=s_datastore)
                self.assertEqual(e_err.exception.message, f"Impossible de trouver l'exécution de traitement liée à la donnée stockée {o_mock_find_stored_data.return_value}")

        # behavior continue - stable - ProcessingExecution trouvé
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_CONTINUE)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            l_pe = [MagicMock(), MagicMock()]
            with patch.object(ProcessingExecution, "api_list", return_value=l_pe) as o_mock_api_list:
                o_mock_find_stored_data.return_value.__getitem__.return_value = "OK"
                o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
                o_mock_find_stored_data.assert_called_once_with(s_datastore)
                self.assertEqual(o_pea.stored_data, o_mock_find_stored_data.return_value)
                o_mock_api_list.assert_called_once_with({"output_stored_data": o_mock_find_stored_data.return_value.id}, datastore=s_datastore)
                self.assertEqual(o_pea.processing_execution, l_pe[0])

        # behavior resume - unstable
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            o_mock_find_stored_data.return_value.__getitem__.return_value = StoredData.STATUS_UNSTABLE
            o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
            o_mock_find_stored_data.assert_called_once_with(s_datastore)
            o_mock_find_stored_data.return_value.api_delete.assert_called_once_with()
            self.assertIsNone(o_pea.processing_execution)

        # behavior resume - stable - ProcessingExecution non trouvé
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            l_pe = []
            with patch.object(ProcessingExecution, "api_list", return_value=l_pe) as o_mock_api_list:
                o_mock_find_stored_data.return_value.__getitem__.return_value = "OK"
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
                o_mock_find_stored_data.assert_called_once_with(s_datastore)
                self.assertEqual(o_pea.stored_data, o_mock_find_stored_data.return_value)
                o_mock_api_list.assert_called_once_with({"output_stored_data": o_mock_find_stored_data.return_value.id}, datastore=s_datastore)
                self.assertEqual(e_err.exception.message, f"Impossible de trouver l'exécution de traitement liée à la donnée stockée {o_mock_find_stored_data.return_value}")

        # behavior resume - stable - ProcessingExecution trouvé
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            l_pe = [MagicMock(), MagicMock()]
            with patch.object(ProcessingExecution, "api_list", return_value=l_pe) as o_mock_api_list:
                o_mock_find_stored_data.return_value.__getitem__.return_value = "OK"
                o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
                o_mock_find_stored_data.assert_called_once_with(s_datastore)
                self.assertEqual(o_pea.stored_data, o_mock_find_stored_data.return_value)
                o_mock_api_list.assert_called_once_with({"output_stored_data": o_mock_find_stored_data.return_value.id}, datastore=s_datastore)
                self.assertEqual(o_pea.processing_execution, l_pe[0])

        # behavior non prévu
        s_behavior = "NON VALIDE"
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=s_behavior)
        with patch.object(ProcessingExecutionAction, "find_stored_data") as o_mock_find_stored_data:
            with self.assertRaises(GpfSdkError) as e_err:
                o_pea._ProcessingExecutionAction__gestion_new_output(s_datastore)
            self.assertEqual(
                e_err.exception.message, f"Le comportement {s_behavior} n'est pas reconnu ({'|'.join(ProcessingExecutionAction.BEHAVIORS)}), l'exécution de traitement n'est pas possible."
            )

    def test_create_processing_execution(self) -> None:
        """test de __create_processing_execution"""
        s_datastore = "datastore"
        d_definition_dict = {"body_parameters": {"key": "val"}}
        d_data: Dict[str, Any] = {}
        o_mock_processing_execution = MagicMock()
        o_mock_processing_execution.get_store_properties.return_value = d_data

        # output_new_entity, creation ProcessingExecution - inputs + output upload
        d_data["inputs"] = {
            "upload": [{"_id": f"{i}"} for i in range(3)],
            "stored_data": [{"_id": f"{i}"} for i in range(3)],
        }
        d_data["output"] = {"upload": {"_id": "out"}}
        o_pea = ProcessingExecutionAction("contexte", d_definition_dict, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock):
            with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__gestion_new_output") as o_mock_gestion_new_output:
                with patch.object(ProcessingExecution, "api_create", return_value=o_mock_processing_execution) as o_mock_pe_api_create:
                    with patch.object(Upload, "api_get") as o_mock_upload_api_get:
                        with patch.object(StoredData, "api_get") as o_mock_stored_data_api_get:
                            o_pea._ProcessingExecutionAction__create_processing_execution(s_datastore)
                            o_mock_gestion_new_output.assert_called_once_with(s_datastore)
                            o_mock_pe_api_create.assert_called_with(d_definition_dict["body_parameters"], {"datastore": s_datastore})
                            o_mock_processing_execution.get_store_properties.assert_called_once_with()
                            for d_input_upload in d_data["inputs"]["upload"]:
                                o_mock_upload_api_get.assert_any_call(d_input_upload["_id"], datastore=s_datastore)
                            self.assertEqual(o_pea.inputs_upload, [o_mock_upload_api_get.return_value] * len(d_data["inputs"]["upload"]))
                            for d_input_stored_data in d_data["inputs"]["stored_data"]:
                                o_mock_stored_data_api_get.assert_any_call(d_input_stored_data["_id"], datastore=s_datastore)
                            o_mock_upload_api_get.assert_any_call(d_data["output"]["upload"]["_id"], datastore=s_datastore)
                            self.assertEqual(o_pea.inputs_stored_data, [o_mock_stored_data_api_get.return_value] * len(d_data["inputs"]["stored_data"]))
                            self.assertFalse(o_pea.no_output)
                            self.assertEqual(o_pea.upload, o_mock_upload_api_get.return_value)
                            self.assertIsNone(o_pea.stored_data)

        o_mock_processing_execution.reset_mock()

        # pas output_new_entity, creation ProcessingExecution - output stored_data
        del d_data["inputs"]
        d_data["output"] = {"stored_data": {"_id": "out"}}
        o_pea = ProcessingExecutionAction("contexte", d_definition_dict, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        with patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=None):
            with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__gestion_new_output") as o_mock_gestion_new_output:
                with patch.object(ProcessingExecution, "api_create", return_value=o_mock_processing_execution) as o_mock_pe_api_create:
                    with patch.object(Upload, "api_get") as o_mock_upload_api_get:
                        with patch.object(StoredData, "api_get") as o_mock_stored_data_api_get:
                            o_pea._ProcessingExecutionAction__create_processing_execution(s_datastore)
                            o_mock_gestion_new_output.assert_not_called()
                            o_mock_pe_api_create.assert_called_with(d_definition_dict["body_parameters"], {"datastore": s_datastore})
                            o_mock_processing_execution.get_store_properties.assert_called_once_with()
                            o_mock_stored_data_api_get.assert_called_once_with(d_data["output"]["stored_data"]["_id"], datastore=s_datastore)
                            self.assertFalse(o_pea.no_output)
                            self.assertEqual(o_pea.stored_data, o_mock_stored_data_api_get.return_value)
                            o_mock_upload_api_get.assert_not_called()
                            self.assertIsNone(o_pea.upload)
                            self.assertIsNone(o_pea.inputs_stored_data)
                            self.assertIsNone(o_pea.inputs_upload)

        o_mock_processing_execution.reset_mock()

        # pas output_new_entity, pas creation ProcessingExecution - no output
        del d_data["output"]
        o_pea = ProcessingExecutionAction("contexte", d_definition_dict, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        o_pea._ProcessingExecutionAction__processing_execution = o_mock_processing_execution
        with patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=None):
            with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__gestion_new_output") as o_mock_gestion_new_output:
                with patch.object(ProcessingExecution, "api_create") as o_mock_pe_api_create:
                    with patch.object(Upload, "api_get") as o_mock_upload_api_get:
                        with patch.object(StoredData, "api_get") as o_mock_stored_data_api_get:
                            o_pea._ProcessingExecutionAction__create_processing_execution(s_datastore)
                            o_mock_gestion_new_output.assert_not_called()
                            o_mock_pe_api_create.assert_not_called()
                            o_mock_processing_execution.get_store_properties.assert_called_once_with()
                            self.assertTrue(o_pea.no_output)
                            self.assertIsNone(o_pea.stored_data)
                            self.assertIsNone(o_pea.upload)
                            o_mock_upload_api_get.assert_not_called()
                            o_mock_stored_data_api_get.assert_not_called()
                            self.assertIsNone(o_pea.inputs_stored_data)
                            self.assertIsNone(o_pea.inputs_upload)

        # pb sur les output : None
        d_data["output"] = None
        o_pea = ProcessingExecutionAction("contexte", d_definition_dict, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        o_pea._ProcessingExecutionAction__processing_execution = o_mock_processing_execution
        with patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(GpfSdkError) as e_err:
                o_pea._ProcessingExecutionAction__create_processing_execution(s_datastore)
            self.assertEqual(e_err.exception.message, "Erreur à la création de l'exécution de traitement : impossible de récupérer l'entité en sortie.")

        # pb sur les output : autre
        d_data["output"] = {"autre": "val"}
        o_pea = ProcessingExecutionAction("contexte", d_definition_dict, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)
        o_pea._ProcessingExecutionAction__processing_execution = o_mock_processing_execution
        with patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(StepActionError) as e_err_step:
                o_pea._ProcessingExecutionAction__create_processing_execution(s_datastore)
            self.assertEqual(e_err_step.exception.message, f"Aucune correspondance pour {d_data['output'].keys()}")

    def test_run(self) -> None:
        """test de run"""

        s_datastore = "datastore"
        o_pea = ProcessingExecutionAction("contexte", {}, behavior=ProcessingExecutionAction.BEHAVIOR_RESUME)

        with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__create_processing_execution") as o_mock_create_processing_execution:
            with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_tags") as o_mock_add_tags:
                with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_comments") as o_mock_add_comments:
                    with patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__launch") as o_mock_launch:
                        o_pea.run(s_datastore)
                        o_mock_create_processing_execution.assert_called_once_with(s_datastore)
                        o_mock_add_tags.assert_called_once_with()
                        o_mock_add_comments.assert_called_once_with()
                        o_mock_launch.assert_called_once_with()

    def monitoring_until_end_args(self, s_status_end: str, b_waits: bool, b_callback: bool) -> None:
        """lancement + test de ProcessingExecutionAction.monitoring_until_end() selon param

        Args:
            s_status_end (str): status de fin
            b_waits (bool): si on a des status intermédiaire
            b_callback (bool): si on a une fonction callback
        """

        l_status = [] if not b_waits else [ProcessingExecution.STATUS_CREATED, ProcessingExecution.STATUS_WAITING, ProcessingExecution.STATUS_PROGRESS]
        f_callback = MagicMock() if b_callback else None
        f_ctrl_c = MagicMock(return_value=True)

        # mock de o_mock_processing_execution
        o_mock_processing_execution = MagicMock(name="test")
        o_mock_processing_execution.get_store_properties.side_effect = [{"status": el} for el in l_status] + [{"status": s_status_end}] * 3
        o_mock_processing_execution.api_update.return_value = None

        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value=o_mock_processing_execution):
            with patch.object(time, "sleep", return_value=None):
                with patch.object(Config, "get_int", return_value=0):

                    # initialisation de ProcessingExecutionAction
                    o_pea = ProcessingExecutionAction("contexte", {})
                    s_return = o_pea.monitoring_until_end(f_callback, f_ctrl_c)

                    # vérification valeur de sortie
                    self.assertEqual(s_return, s_status_end)

                    # vérification de l'attente
                    ## update
                    self.assertEqual(o_mock_processing_execution.api_update.call_count, len(l_status) + 1)
                    ##log + callback
                    if f_callback is not None:
                        self.assertEqual(f_callback.call_count, len(l_status) + 1)
                        self.assertEqual(f_callback.mock_calls, [call(o_mock_processing_execution)] * (len(l_status) + 1))

                    f_ctrl_c.assert_not_called()

    def interrupt_monitoring_until_end_args(self, s_status_end: str, b_waits: bool, b_callback: bool, s_ctrl_c: str, b_upload: bool, b_stored_data: bool, b_new_output: bool) -> None:
        # cas interruption par l'utilisateur.
        """lancement + test de ProcessingExecutionAction.monitoring_until_end() + simulation ctrl+C pendant monitoring_until_end

        Args:
            s_status_end (str): status de fin
            b_waits (bool): si on a des status intermédiaire
            b_callback (bool): si on a une fonction callback
            s_ctrl_c (str): si on a une fonction callback pour gérer les ctrl_c et action du ctrl + C. option : "non", "pass", "delete"
            b_upload (bool): si sortie du traitement en upload
            b_stored_data (bool): si sortie du traitement en stored-data
            b_new_output (bool): si on a une nouvelle sortie (création) un ancienne (modification)

        """

        # print(
        #     "s_status_end", s_status_end,
        #     "b_waits", b_waits,
        #     "b_callback", b_callback,
        #     "s_ctrl_c", s_ctrl_c,
        #     "b_upload", b_upload,
        #     "b_stored_data", b_stored_data,
        #     "b_new_output", b_new_output,
        # )
        if b_waits:
            i_nb_call_back = 4
            l_status = [
                {"status": ProcessingExecution.STATUS_CREATED},
                {"status": ProcessingExecution.STATUS_WAITING},
                {"status": ProcessingExecution.STATUS_PROGRESS},
                {"raise": "KeyboardInterrupt"},
                {"status": ProcessingExecution.STATUS_PROGRESS},
                {"status": ProcessingExecution.STATUS_PROGRESS},
                {"status": s_status_end},
            ]
        else:
            i_nb_call_back = 2
            l_status = [{"status": ProcessingExecution.STATUS_PROGRESS}, {"raise": "KeyboardInterrupt"}, {"status": s_status_end}]

        f_callback = MagicMock() if b_callback else None
        if s_ctrl_c == "delete":
            f_ctrl_c = MagicMock(return_value=True)
        elif s_ctrl_c == "pass":
            f_ctrl_c = MagicMock(return_value=False)
        else:
            f_ctrl_c = None

        d_definition_dict: Dict[str, Any] = {"body_parameters": {"output": {}}}
        d_output = {"name": "new"} if b_new_output else {"_id": "ancien"}
        if b_upload:
            o_mock_upload = MagicMock()
            o_mock_upload.api_delete.return_value = None
            o_mock_stored_data = None
            d_definition_dict["body_parameters"]["output"]["upload"] = d_output
        elif b_stored_data:
            o_mock_upload = None
            o_mock_stored_data = MagicMock()
            o_mock_stored_data.api_delete.return_value = None
            d_definition_dict["body_parameters"]["output"]["stored_data"] = d_output
        else:
            o_mock_upload = None
            o_mock_stored_data = None

        i_iter = 0

        def status() -> Dict[str, Any]:
            """fonction pour mock de get_store_properties (=> status)

            Raises:
                KeyboardInterrupt: simulation du Ctrl+C

            Returns:
                Dict[str, Any]: dict contenant le status
            """
            nonlocal i_iter
            s_el = l_status[i_iter]

            i_iter += 1
            if "raise" in s_el:
                raise KeyboardInterrupt()
            return s_el

        # mock de o_mock_processing_execution
        o_mock_processing_execution = MagicMock(name="test")
        o_mock_processing_execution.get_store_properties.side_effect = status
        o_mock_processing_execution.api_update.return_value = None
        o_mock_processing_execution.api_abort.return_value = None

        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock) as o_mock_pe:
            with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_u:
                with patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_sd:
                    with patch.object(time, "sleep", return_value=None):
                        with patch.object(Config, "get_int", return_value=0):

                            o_mock_pe.return_value = o_mock_processing_execution
                            o_mock_u.return_value = o_mock_upload
                            o_mock_sd.return_value = o_mock_stored_data

                            # initialisation de ProcessingExecutionAction
                            o_pea = ProcessingExecutionAction("contexte", d_definition_dict)

                            # ctrl+C mais continue
                            if s_ctrl_c == "pass":
                                s_return = o_pea.monitoring_until_end(f_callback, f_ctrl_c)

                                # vérification valeur de sortie
                                self.assertEqual(s_return, s_status_end)

                                # vérification de l'attente
                                ## update
                                self.assertEqual(o_mock_processing_execution.api_update.call_count, len(l_status))
                                ##log + callback
                                if f_callback is not None:
                                    self.assertEqual(f_callback.call_count, len(l_status))
                                    self.assertEqual(f_callback.mock_calls, [call(o_mock_processing_execution)] * (len(l_status)))
                                if f_ctrl_c:
                                    f_ctrl_c.assert_called_once_with()
                                return

                            # vérification sortie en erreur de monitoring_until_end
                            with self.assertRaises(KeyboardInterrupt):
                                o_pea.monitoring_until_end(f_callback, f_ctrl_c)

                            # exécution de abort
                            if not b_waits:
                                o_mock_processing_execution.api_abort.assert_not_called()
                            else:
                                o_mock_processing_execution.api_abort.assert_called_once_with()

                            # vérification de l'attente
                            ## update
                            self.assertEqual(o_mock_processing_execution.api_update.call_count, len(l_status))
                            ##log + callback
                            if f_callback is not None:
                                self.assertEqual(f_callback.call_count, i_nb_call_back)
                                self.assertEqual(f_callback.mock_calls, [call(o_mock_processing_execution)] * i_nb_call_back)

                            # vérification suppression el de sortie si nouveau
                            if b_waits and s_status_end == ProcessingExecution.STATUS_ABORTED:
                                if b_upload and o_mock_upload:
                                    if b_new_output:
                                        o_mock_upload.api_delete.assert_called_once_with()
                                    else:
                                        o_mock_upload.api_delete.assert_not_called()
                                elif b_stored_data and o_mock_stored_data:
                                    if b_new_output:
                                        o_mock_stored_data.api_delete.assert_called_once_with()
                                    else:
                                        o_mock_stored_data.api_delete.assert_not_called()

    def test_monitoring_until_end(self) -> None:
        """test de monitoring_until_end"""
        for s_status_end in [ProcessingExecution.STATUS_ABORTED, ProcessingExecution.STATUS_SUCCESS, ProcessingExecution.STATUS_FAILURE]:
            for b_waits in [False, True]:
                for b_callback in [False, True]:
                    self.monitoring_until_end_args(s_status_end, b_waits, b_callback)
                    for s_ctrl_c in ["non", "pass", "delete"]:
                        for b_new_output in [False, True]:
                            self.interrupt_monitoring_until_end_args(s_status_end, b_waits, b_callback, s_ctrl_c, True, False, b_new_output)
                            self.interrupt_monitoring_until_end_args(s_status_end, b_waits, b_callback, s_ctrl_c, False, True, b_new_output)
                            self.interrupt_monitoring_until_end_args(s_status_end, b_waits, b_callback, s_ctrl_c, False, False, b_new_output)
        # cas sans processing execution => impossible
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value=None):
            o_pea = ProcessingExecutionAction("contexte", {})
            # on attend une erreur
            with self.assertRaises(StepActionError) as o_err:
                o_pea.monitoring_until_end()
            self.assertEqual(o_err.exception.message, "Aucune processing-execution trouvée. Impossible de suivre le déroulement du traitement")

        # compatibility_cartes et mise_en_base
        o_pea = ProcessingExecutionAction("contexte", {})
        o_mock_processing_execution = MagicMock(id="id_mise_en_base")
        o_mock_processing_execution.get_store_properties.return_value = {"status": ProcessingExecution.STATUS_SUCCESS}
        o_pea._ProcessingExecutionAction__mode_cartes = True
        l_inputs = [MagicMock(), MagicMock()]

        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value=o_mock_processing_execution):
            with patch.object(Config(), "get_str", side_effect=lambda x, y: y):
                # manque input
                with self.assertRaises(GpfSdkError) as e_err:
                    o_pea.monitoring_until_end()
                self.assertEqual(e_err.exception.message, "Intégration de données vecteur livrées en base : input and output obligatoires")
                # statu ok
                o_pea._ProcessingExecutionAction__inputs_upload = l_inputs
                o_pea.monitoring_until_end()
                for o_upload in l_inputs:
                    o_upload.api_add_tags({"integration_progress": "execution_end_ok_integration_progress"})
                    o_upload.reset_mock()
                # status ko
                o_pea.monitoring_until_end()
                o_mock_processing_execution.get_store_properties.return_value = {"status": ProcessingExecution.STATUS_ABORTED}
                for o_upload in l_inputs:
                    o_upload.api_add_tags({"integration_progress": "execution_end_ko_integration_progress"})

    def test_output_new_entity(self) -> None:
        """test de output_new_entity"""
        for s_output in ["upload", "stored_data"]:
            for b_new in [True, False]:
                d_output = {"name": "new"} if b_new else {"_id": "ancien"}
                d_definition_dict: Dict[str, Any] = {"body_parameters": {"output": {s_output: d_output}}}
                # initialisation de ProcessingExecutionAction
                o_pea = ProcessingExecutionAction("contexte", d_definition_dict)
                self.assertEqual(o_pea.output_new_entity, b_new)
        # pas de sortie
        o_pea = ProcessingExecutionAction("contexte", {"body_parameters": {}})
        self.assertFalse(o_pea.output_new_entity)
        # sortie non stored_data ou upload
        o_pea = ProcessingExecutionAction("contexte", {"body_parameters": {"output": {}}})
        self.assertFalse(o_pea.output_new_entity)

    def test_output_update_entity(self) -> None:
        """test de output_update_entity"""
        for s_output in ["upload", "stored_data"]:
            for b_update in [True, False]:
                d_output = {"_id": "ancien"} if b_update else {"name": "new"}
                d_definition_dict: Dict[str, Any] = {"body_parameters": {"output": {s_output: d_output}}}
                # initialisation de ProcessingExecutionAction
                o_pea = ProcessingExecutionAction("contexte", d_definition_dict)
                self.assertEqual(o_pea.output_update_entity, b_update)
        # pas de sortie
        o_pea = ProcessingExecutionAction("contexte", {"body_parameters": {}})
        self.assertFalse(o_pea.output_update_entity)
        # sortie non stored_data ou upload
        o_pea = ProcessingExecutionAction("contexte", {"body_parameters": {"output": {}}})
        self.assertFalse(o_pea.output_update_entity)

    def test_str(self) -> None:
        """test de __str__"""
        d_definition = {"_id": "ancien"}
        # test sans processing execution
        o_action = ProcessingExecutionAction("nom", d_definition)
        self.assertEqual("ProcessingExecutionAction(workflow=nom)", str(o_action))
        # test avec processing execution
        with patch("sdk_entrepot_gpf.workflow.action.ProcessingExecutionAction.ProcessingExecutionAction.processing_execution", new_callable=PropertyMock) as o_mock_processing_execution:
            o_mock_processing_execution.return_value = MagicMock(id="test uuid")
            self.assertEqual("ProcessingExecutionAction(workflow=nom, processing_execution=test uuid)", str(o_action))
