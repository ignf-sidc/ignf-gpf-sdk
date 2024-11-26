from datetime import datetime
from unittest.mock import patch

from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from tests.GpfTestCase import GpfTestCase


class ProcessingExecutionTestCase(GpfTestCase):
    """Tests ProcessingExecution class.

    cmd : python3 -m unittest -b tests.store.ProcessingExecutionTestCase
    """

    def test_api_launch(self) -> None:
        """Vérifie le bon fonctionnement de api_launch."""
        for s_datastore in [None, "api_launch"]:
            # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons params
            with patch.object(ApiRequester, "route_request", return_value=None) as o_mock_request:
                # on appelle la fonction à tester : api_launch
                o_processing_execution = ProcessingExecution({"_id": "id_entité"}, s_datastore)
                o_processing_execution.api_launch()

                # on vérifie que route_request est appelé correctement
                o_mock_request.assert_called_once_with(
                    "processing_execution_launch",
                    route_params={"processing_execution": "id_entité", "datastore": s_datastore},
                    method=ApiRequester.POST,
                )

    def test_api_abort(self) -> None:
        """Vérifie le bon fonctionnement de api_abort."""
        for s_datastore in [None, "api_launch"]:
            # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons params
            with patch.object(ApiRequester, "route_request", return_value=None) as o_mock_request:
                # on appelle la fonction à tester : api_abort
                o_processing_execution = ProcessingExecution({"_id": "id_entité"}, s_datastore)
                o_processing_execution.api_abort()

                # on vérifie que route_request est appelé correctement
                o_mock_request.assert_called_once_with(
                    "processing_execution_abort",
                    route_params={"processing_execution": "id_entité", "datastore": s_datastore},
                    method=ApiRequester.POST,
                )

    def test_launch(self) -> None:
        """Vérifie le bon fonctionnement de launch."""
        # Instanciation
        o_processing_execution = ProcessingExecution({"_id": "id_entité"})
        # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons params
        with patch.object(o_processing_execution, "_get_datetime", return_value=datetime.now()) as o_mock_get_datetime:
            # on appelle la fonction à tester : launch
            o_datetime = o_processing_execution.launch

            # on vérifie que route_request est appelé correctement
            o_mock_get_datetime.assert_called_once_with("launch")
            self.assertEqual(o_datetime, o_mock_get_datetime.return_value)
