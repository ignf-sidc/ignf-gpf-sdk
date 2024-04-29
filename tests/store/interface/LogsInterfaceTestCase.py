from typing import List, Dict, Any
from unittest.mock import patch

from sdk_entrepot_gpf.io.ApiRequester import ApiRequester
from sdk_entrepot_gpf.store.interface.LogsInterface import LogsInterface
from tests.GpfTestCase import GpfTestCase


class LogsInterfaceTestCase(GpfTestCase):
    """Tests LogsInterface class.

    cmd : python3 -m unittest -b tests.store.interface.LogsInterfaceTestCase
    """

    def test_api_logs_monopage(self) -> None:
        "Vérifie le bon fonctionnement de api_logs (une seule page)."
        s_data = "2022/05/18 14:29:25       INFO §USER§ Envoi du signal de début de l'exécution à l'API.\n2022/05/18 14:29:25       INFO §USER§ Signal transmis avec succès."
        l_rep: List[Dict[str, Any]] = [
            {"datastore": "datastore_id", "data": s_data.split("\n"), "rep": s_data},
            {"datastore": "datastore_id", "data": "", "rep": ""},
            {"datastore": "datastore_id", "data": [], "rep": ""},
            {"datastore": "datastore_id", "data": ["log1", "log2", ' log "complexe"'], "rep": 'log1\nlog2\n log "complexe"'},
        ]

        for d_rep in l_rep:
            o_response = GpfTestCase.get_response(json=d_rep["data"])
            # On mock la fonction route_request, on veut vérifier qu'elle est appelée avec les bons params
            with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
                with patch.object(ApiRequester, "range_next_page", return_value=False) as o_mock_range:
                    # on appelle la fonction à tester : api_logs
                    o_log_interface = LogsInterface({"_id": "id_entité"}, datastore=d_rep["datastore"])
                    s_data_recupere = o_log_interface.api_logs()
                    # on vérifie que route_request et range_next_page sont appelés correctement
                    o_mock_request.assert_called_once_with(
                        "store_entity_logs",
                        route_params={"datastore": d_rep["datastore"], "store_entity": "id_entité"},
                        params={"page": 1, "limit": 2000},
                    )
                    o_mock_range.assert_called_once_with(o_response.headers.get("Content-Range"), len(d_rep["data"]))
                    # on vérifie la similitude des données retournées
                    self.assertEqual(d_rep["rep"], s_data_recupere)

    def test_test_api_logs_multipage(self) -> None:
        "Vérifie le bon fonctionnement de api_logs (plusieurs pages)."
        # paramètre
        s_datastore = "datastore_id"
        l_data = [f"log {j}" for j in range(2000)]

        # nombre de page voulue
        i_page = 4

        o_response = GpfTestCase.get_response(json=l_data)
        with patch.object(ApiRequester, "route_request", return_value=o_response) as o_mock_request:
            with patch.object(ApiRequester, "range_next_page", side_effect=[True] * (i_page - 1) + [False]) as o_mock_range:
                # on appelle la fonction à tester : api_logs
                o_log_interface = LogsInterface({"_id": "id_entité"}, datastore=s_datastore)
                s_data_recupere = o_log_interface.api_logs()
                # on vérifie la similitude des données retournées
                s_data = "\n".join(l_data * i_page)

                print(len(s_data), len(s_data_recupere))

                self.assertEqual(s_data, s_data_recupere)
                # on vérifie que route_request et range_next_page sont appelés correctement
                self.assertEqual(i_page, o_mock_request.call_count)
                self.assertEqual(i_page, o_mock_range.call_count)
                for i in range(1, i_page + 1):
                    o_mock_request.assert_any_call(
                        "store_entity_logs",
                        route_params={"datastore": s_datastore, "store_entity": "id_entité"},
                        params={"page": i, "limit": 2000},
                    )

                    o_mock_range.assert_any_call(o_response.headers.get("Content-Range"), 2000 * i)
