from typing import Any, Dict, List, Optional

from unittest.mock import patch, MagicMock
from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Errors import ConflictError

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.workflow.action.ConfigurationAction import ConfigurationAction
from tests.GpfTestCase import GpfTestCase


# pylint:disable=too-many-arguments
# pylint:disable=too-many-locals
# pylint:disable=too-many-branches


class ConfigurationActionTestCase(GpfTestCase):
    """Tests ConfigurationAction class.

    cmd : python3 -m unittest -b tests.workflow.action.ConfigurationActionTestCase
    """

    def test_find_configuration(self) -> None:
        """Test find_configuration.

        Dans ce test, on suppose que le datastore est défini (cf. find_configuration).
        """
        o_c1 = Configuration({"_id": "pe_1"})
        o_c2 = Configuration({"_id": "pe_2"})
        # création du dict décrivant l'action
        d_action: Dict[str, Any] = {
            "type": "configuration",
            "body_parameters": {
                "name": "name_configuration",
                "layer_name": "layer_name_configuration",
            },
            "tags": {
                "tag": "val",
            },
        }
        for o_api_list_return in [[o_c1, o_c2], [], None]:
            # exécution de ConfigurationAction
            o_ca = ConfigurationAction("contexte", d_action)
            # Mock de ActionAbstract.get_filters et Configuration.api_list
            with patch.object(ActionAbstract, "get_filters", return_value=({"info": "val"}, {"tag": "val"})) as o_mock_get_filters:
                with patch.object(Configuration, "api_list", return_value=o_api_list_return) as o_mock_api_list:
                    # Appel de la fonction find_configuration
                    o_stored_data = o_ca.find_configuration("datastore_id")
                    # Vérifications
                    o_mock_get_filters.assert_called_once_with("configuration", d_action["body_parameters"], d_action["tags"])
                    o_mock_api_list.assert_called_once_with(infos_filter={"info": "val"}, tags_filter={"tag": "val"}, datastore="datastore_id")
                    self.assertEqual(o_stored_data, o_c1 if o_api_list_return else None)

    def run_args(  # pylint:disable=too-many-statements
        self,
        tags: Optional[Dict[str, Any]],
        comments: Optional[List[str]],
        config_already_exists: bool,
        comment_exist: bool = False,
        behavior: Optional[str] = None,
        datastore: Optional[str] = None,
        conflict_creation: bool = False,
    ) -> None:
        """lancement +test de ConfigurationAction.run selon param
        Args:
            tags (Optional[Dict[str, Any]]): dict des tags ou None
            comments (Optional[List[str]]): liste des comments ou None
            config_already_exists (bool): configuration déjà existante
            comment_exist (bool): si on a un commentaire qui existe déjà
            behavior (Optional[str]): si on a un commentaire qui existe déjà
            datastore (Optional[str]): id du datastore à utiliser.
            conflict_creation (bool): si il y a un conflict lors de la creation
        """
        # creation du dictionnaire qui reprend les paramètres du workflow pour créer une configuration
        d_action: Dict[str, Any] = {"type": "configuration", "body_parameters": {"param": "valeur"}}
        if tags is not None:
            d_action["tags"] = tags
        if comments is not None:
            d_action["comments"] = comments.copy()
            if comment_exist:
                d_action["comments"].append("commentaire existe")

        # mock de configuration
        o_mock_configuration = MagicMock()
        o_mock_configuration.api_launch.return_value = None
        o_mock_configuration.api_add_comment.return_value = None
        o_mock_configuration.api_list_comments.return_value = [{"text": "commentaire existe"}] if comment_exist else []

        # paramétrage du mock de Configuration.api_create
        if conflict_creation:
            d_api_create: Dict[str, Any] = {"side_effect": ConflictError("url", "POST", None, None, '{"error_description":["message_erreur"]}')}
        else:
            d_api_create = {"return_value": o_mock_configuration}

        # Liste des configurations déjà existantes
        o_configs = o_mock_configuration if config_already_exists else None

        # suppression de la mise en page forcé pour le with
        with patch.object(Configuration, "api_create", **d_api_create) as o_mock_configuration_api_create:
            with patch.object(ConfigurationAction, "find_configuration", return_value=o_configs) as o_mock_find_configuration:
                # initialisation de Configuration
                o_conf = ConfigurationAction("contexte", d_action, behavior=behavior, compatibility_cartes=False)
                if config_already_exists:
                    if behavior == "STOP":
                        # on attend une erreur
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_conf.run(datastore)
                        self.assertEqual(o_err.exception.message, f"Impossible de créer la configuration, une configuration équivalente {o_mock_configuration} existe déjà.")
                        o_mock_find_configuration.assert_called_once_with(datastore)
                        return

                    if behavior == "DELETE":
                        if conflict_creation:
                            with self.assertRaises(StepActionError) as o_err_2:
                                o_conf.run(datastore)
                            print(o_err_2.exception.message)
                            self.assertEqual(o_err_2.exception.message, "Impossible de créer la configuration il y a un conflict : \nmessage_erreur")
                            return
                        # suppression de l'existant puis normal
                        o_conf.run(datastore)
                        # un appel à find_stored_data
                        o_mock_configuration.api_delete.assert_called_once_with()
                        o_mock_configuration_api_create.assert_called_once_with(d_action["body_parameters"], route_params={"datastore": datastore})
                    elif not behavior or behavior == "CONTINUE":
                        o_conf.run(datastore)
                        # on n'a pas d'api create
                        self.assertEqual(o_mock_configuration, o_conf.configuration)
                        o_mock_configuration_api_create.assert_not_called()
                    else:
                        # behavior non valide
                        with self.assertRaises(GpfSdkError) as o_err:
                            o_conf.run(datastore)
                        self.assertEqual(o_err.exception.message, f"Le comportement {behavior} n'est pas reconnu (STOP|DELETE|CONTINUE), l'exécution de traitement n'est pas possible.")
                        return

                elif conflict_creation:
                    # pas de conflict trouvé avant création mais erreur conflict lors de la creation
                    with self.assertRaises(StepActionError) as o_err_2:
                        o_conf.run(datastore)
                    self.assertEqual(o_err_2.exception.message, "Impossible de créer la configuration il y a un conflict : \nmessage_erreur")
                    return
                else:
                    # on lance l'exécution de run
                    o_conf.run(datastore)
                    o_mock_configuration_api_create.assert_called_once_with(d_action["body_parameters"], route_params={"datastore": datastore})

                # test de l'appel à Configuration.api_create
                o_mock_find_configuration.assert_called_once()

                # test api_add_tags
                if "tags" in d_action and d_action["tags"]:
                    o_mock_configuration.api_add_tags.assert_called_once_with(d_action["tags"])
                else:
                    o_mock_configuration.api_add_tags.assert_not_called()

                # test commentaires
                if "comments" in d_action and comments:
                    o_mock_configuration.api_list_comments.assert_called_once_with()
                    self.assertEqual(len(comments), o_mock_configuration.api_add_comment.call_count)
                    for s_comm in comments:
                        o_mock_configuration.api_add_comment.assert_any_call({"text": s_comm})
                else:
                    o_mock_configuration.api_add_comment.assert_not_called()

    def test_run(self) -> None:
        """test de run"""
        # On teste avec et sans configuration renvoyé par api_list
        for b_config_already_exists in [True, False]:
            ## sans tag + sans commentaire
            self.run_args(None, None, b_config_already_exists, False)
            ## tag vide + commentaire vide
            self.run_args({}, [], b_config_already_exists, False)
            ## 1 tag + 1 commentaire
            self.run_args({"tag1": "val1"}, ["comm1"], b_config_already_exists, False)
            ## 2 tag + 4 commentaire
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, False)
            ## 2 tag + 4 commentaire + 1 commentaire qui existe déjà
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, True)
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, True, "STOP", "toto")
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, True, "CONTINUE", "toto")
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, True, "DELETE", "toto")
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, True, "non", "toto")
            self.run_args({"tag1": "val1", "tag2": "val2"}, ["comm1", "comm2", "comm3", "comm4"], b_config_already_exists, True, "DELETE", "toto", True)
