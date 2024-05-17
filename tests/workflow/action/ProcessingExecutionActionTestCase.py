import time
from typing import Any, Dict, List, Optional

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


# pylint:disable=too-many-arguments
# pylint:disable=too-many-locals
# pylint:disable=too-many-branches
# pylint:disable=too-many-statements
# fmt: off
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
        d_action:Dict[str, Any] = {
            "type": "processing-execution",
            "body_parameters": {
                "output": {
                    "stored_data": {"name": "name_stored_data"}
                }
            },
            "tags": {"tag": "val"}
        }
        # exécution de ProcessingExecutionAction
        o_ua = ProcessingExecutionAction("contexte", d_action)

        for s_datastore in [None, "datastore"]:
            ## execution sans datastore
            # Mock de ActionAbstract.get_filters et Upload.api_list
            with patch.object(ActionAbstract, "get_filters", return_value=({"info":"val"}, {"tag":"val"})) as o_mock_get_filters:
                with patch.object(StoredData, "api_list", return_value=[o_pe1, o_pe2]) as o_mock_api_list :
                    # Appel de la fonction find_stored_data
                    o_stored_data = o_ua.find_stored_data(s_datastore)
                    # Vérifications
                    o_mock_get_filters.assert_called_once_with("processing_execution", d_action["body_parameters"]["output"]["stored_data"], d_action["tags"])
                    o_mock_api_list.assert_called_once_with(infos_filter={"info":"val"}, tags_filter={"tag":"val"}, datastore=s_datastore)
                    self.assertEqual(o_stored_data, o_pe1)
        # pas de stored data trouvé
        with patch.object(ActionAbstract, "get_filters", return_value=({"info":"val"}, {"tag":"val"})) as o_mock_get_filters:
            with patch.object(StoredData, "api_list", return_value=[]) as o_mock_api_list :
                # Appel de la fonction find_stored_data
                o_stored_data = o_ua.find_stored_data(s_datastore)
                # Vérifications
                o_mock_get_filters.assert_called_once_with("processing_execution", d_action["body_parameters"]["output"]["stored_data"], d_action["tags"])
                o_mock_api_list.assert_called_once_with(infos_filter={"info":"val"}, tags_filter={"tag":"val"}, datastore=s_datastore)
                self.assertEqual(o_stored_data, None)

    def run_args(self,
        tags: Optional[Dict[str,Any]],
        comments: Optional[List[str]],
        s_key: str,
        s_type_output: str,
        datastore: Optional[str],
        output_already_exist: bool = False,
        behavior: Optional[str] = None,
    ) -> None:
        """lancement + test de ProcessingExecutionAction.run selon param

        Args:
            tags (Optional[Dict[str, Any]]): dictionnaire des tags ou None
            comments (Optional[List]): liste des commentaires ou None
            s_type_output (str): type de l'output (stored_data ou upload)
        """
        self.i += 1
        with self.subTest(i=self.i):
            d_action: Dict[str, Any] = {"type": "processing-execution", "body_parameters":{"output":{s_key:"test"}}}
            if tags is not None:
                d_action["tags"] = tags
            if comments is not None:
                d_action["comments"] = comments

            # initialisation de ProcessingExecutionAction
            o_pea = ProcessingExecutionAction("contexte", d_action, behavior=behavior)

            # mock de processing execution
            d_store_properties = {"output": {s_type_output: {"_id": "id"}}}
            o_mock_processing_execution = MagicMock()
            o_mock_processing_execution.get_store_properties.return_value = d_store_properties
            o_mock_processing_execution.api_launch.return_value = None
            # o_mock_processing_execution.__getitem__.return_value = ProcessingExecution.STATUS_CREATED
            # ça veut dire que : o_mock_processing_execution["quelchechose"] = "CREATED"
            def get_items_processing(key:str) -> Any:
                if key == "status":
                    return "CREATED"
                return MagicMock()
            o_mock_processing_execution.__getitem__.side_effect = get_items_processing

            # mock de upload d'entrée
            o_mock_upload = MagicMock()
            o_mock_upload.api_add_tags.return_value = None
            o_mock_upload.api_add_comment.return_value = None

            # mock de stored_data d'entrée
            o_mock_stored_data = MagicMock()
            o_mock_stored_data.api_add_tags.return_value = None
            o_mock_stored_data.api_add_comment.return_value = None

            # résultat de ProcessingExecutionAction."find_stored_data" : stored_data de sortie
            o_exist_output = None
            if output_already_exist:
                o_mock_exist_output = MagicMock()
                o_mock_exist_output.api_delete.return_value = None
                o_exist_output = o_mock_exist_output

            # suppression de la mise en page forcée pour le with
            with patch.object(Upload, "api_get", return_value=o_mock_upload) as o_mock_upload_api_get, \
                patch.object(StoredData, "api_get", return_value=o_mock_stored_data) as o_mock_stored_data_api_get, \
                patch.object(ProcessingExecution, "api_create", return_value=o_mock_processing_execution) as o_mock_pe_api_create, \
                patch.object(ProcessingExecution, "api_list", return_value=[o_mock_processing_execution]) as o_mock_pe_api_list, \
                patch.object(ProcessingExecutionAction, "find_stored_data", return_value=o_exist_output) as o_mock_pea_find_stored_data, \
                patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=output_already_exist), \
                patch.object(Config, "get_str", return_value="STOP") \
            :
                # dans le cas où une entité existe déjà dans la gpf :
                if output_already_exist:
                    if not behavior or behavior == "STOP":
                        # on attend une erreur
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_pea.run(datastore)
                        self.assertEqual(o_err.exception.message, f"Impossible de créer l’exécution de traitement, une donnée stockée en sortie équivalente {o_exist_output} existe déjà.")
                        return

                    if behavior == "DELETE":
                        # suppression de l'existant puis normal
                        o_pea.run(datastore)
                        # un appel à find_stored_data
                        o_mock_pea_find_stored_data.assert_called_once_with(datastore)
                        o_mock_exist_output.api_delete.assert_called_once_with()
                    elif behavior == "CONTINUE":
                        # premier test sur STATUS_UNSTABLE
                        o_mock_exist_output.__getitem__.return_value = StoredData.STATUS_UNSTABLE
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_pea.run(datastore)
                        self.assertEqual(
                            o_err.exception.message,
                            f"Le traitement précédent a échoué sur la donnée stockée en sortie {o_mock_exist_output}. Impossible de lancer le traitement demandé."
                        )

                        # deuxième test sur la stored data créée
                        o_mock_exist_output.__getitem__.return_value = StoredData.STATUS_CREATED
                        o_pea.run(datastore)
                        o_mock_pe_api_list.assert_called_once_with({"output_stored_data":o_mock_exist_output.id}, datastore=datastore)
                        self.assertEqual(o_pea.processing_execution, o_mock_processing_execution)

                        # troisième test sur l'absence de la processing execution
                        o_mock_pe_api_list.return_value = []
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_pea.run(datastore)
                        self.assertEqual(o_err.exception.message, f"Impossible de trouver l'exécution de traitement liée à la donnée stockée {o_mock_exist_output}")

                        return
                    elif behavior == "RESUME":
                        # premier test sur la stored data créée
                        o_mock_exist_output.__getitem__.return_value = StoredData.STATUS_CREATED
                        o_pea.run(datastore)
                        o_mock_pe_api_list.assert_called_once_with({"output_stored_data":o_mock_exist_output.id}, datastore=datastore)
                        self.assertEqual(o_pea.processing_execution, o_mock_processing_execution)

                        o_mock_exist_output.reset_mock()
                        o_mock_pea_find_stored_data.reset_mock()

                        # deuxième test sur l'absence de la processing execution
                        o_mock_pe_api_list.return_value = []
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_pea.run(datastore)
                        self.assertEqual(o_err.exception.message, f"Impossible de trouver l'exécution de traitement liée à la donnée stockée {o_mock_exist_output}")

                        o_mock_exist_output.reset_mock()
                        o_mock_pea_find_stored_data.reset_mock()
                        o_mock_processing_execution.api_launch.reset_mock()

                        # troisième test sur STATUS_UNSTABLE => suppression puis normal
                        o_mock_exist_output.__getitem__.return_value = StoredData.STATUS_UNSTABLE
                        o_pea.run(datastore)
                        # un appel à find_stored_data
                        o_mock_pea_find_stored_data.assert_called_once_with(datastore)
                        o_mock_exist_output.api_delete.assert_called_once_with()
                    else:
                        # behavior non reconnu. On attend une erreur
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_pea.run(datastore)
                        self.assertEqual(o_err.exception.message, f"Le comportement {behavior} n'est pas reconnu (STOP|DELETE|CONTINUE|RESUME), l'exécution de traitement n'est pas possible.")
                        return

                else:
                    # on appelle la méthode à tester
                    o_pea.run(datastore)
                    o_mock_pea_find_stored_data.assert_not_called()

                # test de l'appel à ProcessingExecution.api_create
                o_mock_pe_api_create.assert_called_once_with(d_action['body_parameters'], {"datastore":datastore})
                # un appel à ProcessingExecution().get_store_properties
                o_mock_processing_execution.get_store_properties.assert_called_once_with()

                # verif appel à Upload/StoredData
                if "stored_data" in d_store_properties["output"]:
                    # test  .api_get
                    o_mock_stored_data_api_get.assert_called_once_with("id", datastore=datastore)
                    o_mock_upload_api_get.assert_not_called()

                    # test api_add_tags
                    if "tags" in d_action and d_action["tags"]:
                        o_mock_stored_data.api_add_tags.assert_called_once_with(d_action["tags"])
                    else:
                        o_mock_stored_data.api_add_tags.assert_not_called()
                    o_mock_upload.api_add_tags.assert_not_called()

                    # test commentaires
                    if "comments" in d_action and d_action["comments"]:
                        self.assertEqual(len(d_action["comments"]), o_mock_stored_data.api_add_comment.call_count)
                        for s_comm in d_action["comments"]:
                            o_mock_stored_data.api_add_comment.assert_any_call({"text": s_comm})
                    else:
                        o_mock_stored_data.api_add_comment.assert_not_called()
                    o_mock_upload.api_add_comment.assert_not_called()


                elif "upload" in  d_store_properties["output"]:
                    # test api_get
                    o_mock_upload_api_get.assert_called_once_with("id", datastore=datastore)
                    o_mock_stored_data_api_get.assert_not_called()

                    # test api_add_tags
                    if "tags" in d_action and d_action["tags"]:
                        o_mock_upload.api_add_tags.assert_called_once_with(d_action["tags"])
                    else:
                        o_mock_upload.api_add_tags.assert_not_called()
                    o_mock_stored_data.api_add_tags.assert_not_called()

                    # test commentaires
                    if "comments" in d_action and d_action["comments"]:
                        self.assertEqual(len(d_action["comments"]), o_mock_upload.api_add_comment.call_count)
                        for s_comm in d_action["comments"]:
                            o_mock_upload.api_add_comment.assert_any_call({"text": s_comm})
                    else:
                        o_mock_upload.api_add_comment.assert_not_called()
                    o_mock_stored_data.api_add_comment.assert_not_called()

                # un appel à api_launch
                o_mock_processing_execution.api_launch.assert_called_once_with()

    def test_run(self) -> None:
        """test de run"""
        s_key = "name"
        # test upload
        for s_datastore in [None, "datastore"]:
            for s_type_output in [ "upload", "stored_data"]:
                ## sans tag + sans commentaire
                self.run_args(None, None, s_key, s_type_output, s_datastore)
                ## tag vide + commentaire vide
                self.run_args({}, [], s_key, s_type_output, s_datastore)
                ## 1 tag + 1 commentaire
                self.run_args({"tag1": "val1"}, ["comm1"], s_key, s_type_output, s_datastore)
                ## 2 tag + 4 commentaire
                self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore)

        # tests particuliers pour cas ou la sortie existe déjà
        self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore, True, "STOP")
        self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore, True, "DELETE")
        self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore, True, "CONTINUE")
        self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore, True, "RESUME")
        self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore, True, "Toto")
        self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], s_key, s_type_output, s_datastore, True, None)

        # cas en erreurs non spécifique
        d_action: Dict[str, Any] = {"type": "processing-execution", "body_parameters":{"output":{s_key:"test"}}, "tags": {"key":"val"}, "comments": ["comm"]}
        o_mock_processing_execution = MagicMock()
        o_mock_processing_execution.get_store_properties.return_value = {"output":None}

        ## processing_execution.get_store_properties vide après création
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior="STOP")
        with patch.object(ProcessingExecution, "api_create", return_value=o_mock_processing_execution), \
            patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=False), \
            patch.object(Config, "get_str", return_value="STOP") \
        :
            with self.assertRaises(GpfSdkError) as o_err_gpf:
                o_pea.run()
            s_message = "Erreur à la création de l'exécution de traitement : impossible de récupérer l'entité en sortie."
            self.assertEqual(o_err_gpf.exception.message, s_message)

        ## impossible de récupérer le donnée en sortie depuis processing_execution
        d_output={"autre": "", "key": ""}
        o_mock_processing_execution.get_store_properties.return_value = {"output":d_output}
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior="STOP")
        with patch.object(ProcessingExecution, "api_create", return_value=o_mock_processing_execution), \
            patch.object(ProcessingExecutionAction, "output_new_entity", new_callable=PropertyMock, return_value=False), \
            patch.object(Config, "get_str", return_value="STOP") \
        :
            with self.assertRaises(StepActionError) as o_err_step:
                o_pea.run()
            s_message = f"Aucune correspondance pour {d_output.keys()}"
            self.assertEqual(o_err_step.exception.message, s_message)

        ## impossible d'ajouté un tag, pas de donnée en sortie
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior="STOP")
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None), \
            patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock, return_value=None), \
            patch.object(Config, "get_str", return_value="STOP"), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__create_processing_execution", return_value=None) \
        :
            with self.assertRaises(StepActionError) as o_err_step:
                o_pea.run()
            s_message = "ni upload ni stored-data trouvé. Impossible d'ajouter les tags"
            self.assertEqual(o_err_step.exception.message, s_message)

        ## impossible d'ajouté un commentaire, pas de donnée en sortie
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior="STOP")
        with patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock, return_value=None), \
            patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock, return_value=None), \
            patch.object(Config, "get_str", return_value="STOP"), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__create_processing_execution", return_value=None), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_tags", return_value=None) \
        :
            with self.assertRaises(StepActionError) as o_err_step:
                o_pea.run()
            s_message = "ni upload ni stored-data trouvé. Impossible d'ajouter les commentaires"
            self.assertEqual(o_err_step.exception.message, s_message)

        ## __launch pas de processing_execution
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior="STOP")
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value=None), \
            patch.object(Config, "get_str", return_value="STOP"), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__create_processing_execution", return_value=None), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_tags", return_value=None), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_comments", return_value=None) \
        :
            with self.assertRaises(StepActionError) as o_err_step:
                o_pea.run()
            s_message = "Aucune exécution de traitement trouvée. Impossible de lancer le traitement"
            self.assertEqual(o_err_step.exception.message, s_message)

        ## __launch traitement pas déjà lancé et pas en mode continue ou reprise
        o_pea = ProcessingExecutionAction("contexte", d_action, behavior="STOP")
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value={"status": "autre"}), \
            patch.object(Config, "get_str", return_value="STOP"), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__create_processing_execution", return_value=None), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_tags", return_value=None), \
            patch.object(ProcessingExecutionAction, "_ProcessingExecutionAction__add_comments", return_value=None) \
        :
            with self.assertRaises(StepActionError) as o_err_step:
                o_pea.run()
            s_message = "L'exécution de traitement est déjà lancée."
            self.assertEqual(o_err_step.exception.message, s_message)


    def monitoring_until_end_args(self, s_status_end: str, b_waits: bool, b_callback: bool) -> None:
        """lancement + test de ProcessingExecutionAction.monitoring_until_end() selon param

        Args:
            s_status_end (str): status de fin
            b_waits (bool): si on a des status intermédiaire
            b_callback (bool): si on a une fonction callback
        """

        l_status = [] if not b_waits else [ProcessingExecution.STATUS_CREATED,ProcessingExecution.STATUS_WAITING, ProcessingExecution.STATUS_PROGRESS]
        f_callback = MagicMock() if b_callback else None
        f_ctrl_c = MagicMock(return_value=True)

        # mock de o_mock_processing_execution
        o_mock_processing_execution = MagicMock(name="test")
        o_mock_processing_execution.get_store_properties.side_effect = [{"status": el} for el in l_status] + [{"status": s_status_end}]*3
        o_mock_processing_execution.api_update.return_value = None

        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value = o_mock_processing_execution), \
            patch.object(time, "sleep", return_value=None), \
            patch.object(Config, "get_int", return_value=0) :

            # initialisation de ProcessingExecutionAction
            o_pea = ProcessingExecutionAction("contexte", {})
            s_return = o_pea.monitoring_until_end(f_callback, f_ctrl_c)

            # vérification valeur de sortie
            self.assertEqual(s_return, s_status_end)

            # vérification de l'attente
            ## update
            self.assertEqual(o_mock_processing_execution.api_update.call_count, len(l_status)+1)
            ##log + callback
            if f_callback is not None:
                self.assertEqual(f_callback.call_count, len(l_status)+1)
                self.assertEqual(f_callback.mock_calls, [call(o_mock_processing_execution)] * (len(l_status)+1))

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
            i_nb_call_back=4
            l_status = [{"status": ProcessingExecution.STATUS_CREATED}, {"status": ProcessingExecution.STATUS_WAITING}, {"status": ProcessingExecution.STATUS_PROGRESS}, \
                {"raise": "KeyboardInterrupt"}, {"status": ProcessingExecution.STATUS_PROGRESS}, {"status": ProcessingExecution.STATUS_PROGRESS}, {"status": s_status_end}]
        else:
            i_nb_call_back =2
            l_status = [{"status": ProcessingExecution.STATUS_PROGRESS}, {"raise": "KeyboardInterrupt"}, {"status": s_status_end}]

        f_callback = MagicMock() if b_callback else None
        if s_ctrl_c == "delete":
            f_ctrl_c = MagicMock(return_value=True)
        elif s_ctrl_c  == "pass":
            f_ctrl_c = MagicMock(return_value=False)
        else:
            f_ctrl_c = None

        d_definition_dict: Dict[str, Any] = {"body_parameters":{"output":{}}}
        d_output = {"name": "new"} if b_new_output else {"_id": "ancien"}
        if b_upload :
            o_mock_upload = MagicMock()
            o_mock_upload.api_delete.return_value = None
            o_mock_stored_data = None
            d_definition_dict["body_parameters"]["output"]["upload"]=d_output
        elif b_stored_data:
            o_mock_upload = None
            o_mock_stored_data = MagicMock()
            o_mock_stored_data.api_delete.return_value = None
            d_definition_dict["body_parameters"]["output"]["stored_data"]=d_output
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

            i_iter+=1
            if "raise" in s_el:
                raise KeyboardInterrupt()
            return s_el

        # mock de o_mock_processing_execution
        o_mock_processing_execution = MagicMock(name="test")
        o_mock_processing_execution.get_store_properties.side_effect = status
        o_mock_processing_execution.api_update.return_value = None
        o_mock_processing_execution.api_abort.return_value = None


        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock) as o_mock_pe, \
            patch.object(ProcessingExecutionAction, "upload", new_callable=PropertyMock) as o_mock_u, \
            patch.object(ProcessingExecutionAction, "stored_data", new_callable=PropertyMock) as o_mock_sd, \
            patch.object(time, "sleep", return_value=None), \
            patch.object(Config, "get_int", return_value=0) :

            o_mock_pe.return_value = o_mock_processing_execution
            o_mock_u.return_value = o_mock_upload
            o_mock_sd.return_value = o_mock_stored_data

            # initialisation de ProcessingExecutionAction
            o_pea = ProcessingExecutionAction("contexte", d_definition_dict)

            # ctrl+C mais continue
            if s_ctrl_c  == "pass":
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

    def test_monitoring_until_end(self)-> None:
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
        with patch.object(ProcessingExecutionAction, "processing_execution", new_callable=PropertyMock, return_value = None):
            o_pea = ProcessingExecutionAction("contexte", {})
            # on attend une erreur
            with self.assertRaises(StepActionError) as o_err:
                o_pea.monitoring_until_end()
            self.assertEqual(o_err.exception.message, "Aucune processing-execution trouvée. Impossible de suivre le déroulement du traitement")
            return


    def test_output_new_entity(self)-> None:
        """test de output_new_entity"""
        for s_output in ["upload", "stored_data"]:
            for b_new in [True, False]:
                d_output = {"name": "new"} if b_new else {"_id": "ancien"}
                d_definition_dict: Dict[str, Any] = {"body_parameters":{"output":{s_output:d_output}}}
                # initialisation de ProcessingExecutionAction
                o_pea = ProcessingExecutionAction("contexte", d_definition_dict)
                self.assertEqual(o_pea.output_new_entity, b_new)


    def test_str(self) -> None:
        """test de __str__"""
        d_definition = {"_id": "ancien"}
        # test sans processing execution
        o_action = ProcessingExecutionAction("nom", d_definition)
        self.assertEqual("ProcessingExecutionAction(workflow=nom)", str(o_action))
        # test avec processing execution
        with patch('sdk_entrepot_gpf.workflow.action.ProcessingExecutionAction.ProcessingExecutionAction.processing_execution', new_callable=PropertyMock) as o_mock_processing_execution:
            o_mock_processing_execution.return_value = MagicMock(id='test uuid')
            self.assertEqual("ProcessingExecutionAction(workflow=nom, processing_execution=test uuid)", str(o_action))
