import json
from pathlib import Path
from typing import Any, Dict, Optional, Type, List
from unittest.mock import PropertyMock, patch, MagicMock

import jsonschema

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution

from sdk_entrepot_gpf.workflow.Errors import WorkflowError
from sdk_entrepot_gpf.workflow.Workflow import Workflow
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.workflow.action.ConfigurationAction import ConfigurationAction
from sdk_entrepot_gpf.workflow.action.CopyConfigurationAction import CopyConfigurationAction
from sdk_entrepot_gpf.workflow.action.DeleteAction import DeleteAction
from sdk_entrepot_gpf.workflow.action.EditAction import EditAction
from sdk_entrepot_gpf.workflow.action.EditUsedDataConfigurationAction import EditUsedDataConfigurationAction
from sdk_entrepot_gpf.workflow.action.OfferingAction import OfferingAction
from sdk_entrepot_gpf.workflow.action.PermissionAction import PermissionAction
from sdk_entrepot_gpf.workflow.action.ProcessingExecutionAction import ProcessingExecutionAction
from sdk_entrepot_gpf.workflow.action.SynchronizeOfferingAction import SynchronizeOfferingAction
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver

from tests.GpfTestCase import GpfTestCase

# pylint:disable=too-many-statements


class WorkflowTestCase(GpfTestCase):
    """Tests Workflow class.

    cmd : python3 -m unittest -b tests.workflow.WorkflowTestCase
    """

    o_mock_action = None

    def test_get_raw_dict(self) -> None:
        """test de get_raw_dict"""
        d_workflow = {"test": "val"}
        o_workflow = Workflow("nom", d_workflow)
        self.assertDictEqual(d_workflow, o_workflow.get_raw_dict())

    def __list_action_run_step(self, s_etape: str, d_args_run_step: Dict[str, Any], d_workflow: Dict[str, Any]) -> List[Dict[str, Any]]:  # pylint:disable=too-many-branches
        """création de la liste des actions pour run_run_step()

        Args:
            s_etape (str): non de l'étape
            d_args_run_step (Dict[str, Any]): dictionnaire donné à run step
            d_workflow (Dict[str, Any]): dictionnaire du workflow

        Returns:
            List[Dict[str, Any]]: liste des actions avec les commentaire et les tags de gérer
        """
        if s_etape not in d_workflow["workflow"]["steps"]:
            return []
        d_etape = d_workflow["workflow"]["steps"][s_etape]
        l_comments: List[str] = d_args_run_step["comments"]
        d_tags: Dict[str, str] = d_args_run_step["tags"]
        l_actions = []

        # général workflow
        if "comments" in d_workflow:
            l_comments = [*l_comments, *d_workflow["comments"]]
        if "tags" in d_workflow:
            d_tags = {**d_tags, **d_workflow["tags"]}
        # dans l'étape
        if "comments" in d_etape:
            l_comments = [*l_comments, *d_etape["comments"]]
        if "tags" in d_etape:
            d_tags = {**d_tags, **d_etape["tags"]}
        for d_action in d_etape["actions"]:
            d_action = d_action.copy()
            if "comments" in d_action:
                d_action["comments"] = [*l_comments, *d_action["comments"]]
            else:
                d_action["comments"] = l_comments
            if "tags" in d_action:
                d_action["tags"] = {**d_tags, **d_action["tags"]}
            else:
                d_action["tags"] = d_tags
            l_actions.append(d_action)

        # les iterations
        if "iter_vals" in d_etape and "iter_key" in d_etape:
            # on itère sur les clefs
            s_actions = str(json.dumps(l_actions, ensure_ascii=False))
            l_actions = []
            if isinstance(d_etape["iter_vals"][0], (str, float, int)):
                # si la liste est une liste de string, un int ou flat : on remplace directement
                for s_val in d_etape["iter_vals"]:
                    l_actions += json.loads(s_actions.replace("{" + d_etape["iter_key"] + "}", s_val))  # json.loads ok car on est dans des tests
            else:
                # on a une liste de sous dict ou apparenté on utilise un résolveur
                for i, s_val in enumerate(d_etape["iter_vals"]):
                    l_actions += json.loads(s_actions.replace(d_etape["iter_key"], f"iter_resolve_{i}"))  # json.loads ok car on est dans des tests
        return l_actions

    def run_run_step(
        self,
        d_args_run_step: Dict[str, Any],
        d_workflow: Dict[str, Any],
        l_run_args: List[Any],
        monitoring_until_end: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        output_type: str = "configuration",
    ) -> None:
        """Fonction de lancement des tests pour run_step()

        Args:
            d_args_run_step Dict[str, Any]: dictionnaire donné à run step
            d_workflow (Dict[str, Any]): dictionnaire du workflow
            l_run_args (List[Any]): liste des argument passé en appel de action.run(). Un élément = un appel
            monitoring_until_end (Optional[List[str]], optional): si None, action sans monitoring, si défini : définition du side effect du mock de action.monitoring_until_end(). Defaults to None.
            error_message (Optional[str], optional): Message d'erreur compléter avec "action", si None : pas d'erreur attendu. Defaults to None.
            output_type (str): type de l'entité de sortie : stored_data, configuration, offering ou upload
        """
        s_etape = str(d_args_run_step["step_name"])

        # récupération de la liste d'action
        l_actions = self.__list_action_run_step(s_etape, d_args_run_step, d_workflow)

        # création du o_mock_action
        if output_type == "upload":
            o_mock_action = MagicMock(spec=ProcessingExecutionAction)
            o_mock_action.stored_data = None
            o_mock_action.upload = f"Entity_{output_type}"
        elif output_type == "stored_data":
            o_mock_action = MagicMock(spec=ProcessingExecutionAction)
            o_mock_action.stored_data = f"Entity_{output_type}"
            o_mock_action.upload = None
        elif output_type == "offering":
            o_mock_action = MagicMock(spec=OfferingAction)
            o_mock_action.offering = f"Entity_{output_type}"
        else:
            o_mock_action = MagicMock(spec=ConfigurationAction)
            o_mock_action.configuration = f"Entity_{output_type}"

        if monitoring_until_end:
            # cas avec monitoring
            o_mock_action.monitoring_until_end.side_effect = monitoring_until_end

        ## config mock générale
        o_mock_action.resolve.return_value = None
        o_mock_action.run.return_value = None

        ## mock de la property definition_dict
        type(o_mock_action).definition_dict = PropertyMock(side_effect=l_actions)

        # initialisation de Workflow
        o_workflow = Workflow("nom", d_workflow)

        # on mock Workflow.generate
        with patch.object(Workflow, "generate", return_value=o_mock_action) as o_mock_action_generate:
            with patch.object(GlobalResolver, "resolve", side_effect=lambda x, **kwargs: x) as o_mock_resolve:
                if error_message is not None:
                    # si on attend une erreur
                    with self.assertRaises(WorkflowError) as o_arc:
                        o_workflow.run_step(**d_args_run_step)
                    self.assertEqual(o_arc.exception.message, error_message.format(action=o_mock_action))
                else:
                    # pas d'erreur attendu
                    l_entities = o_workflow.run_step(**d_args_run_step)
                    self.assertListEqual(l_entities, [f"Entity_{output_type}"] * len(l_run_args))

                    # tests pour "iter_vals"
                    d_step = d_workflow["workflow"]["steps"][s_etape]
                    if "iter_vals" in d_step:
                        # datastore argument du run_step, ou datastore de l'étape ou datastore du workflow
                        o_mock_resolve.assert_called_once_with(json.dumps(d_step["iter_vals"]), datastore=d_args_run_step.get("datastore", d_step.get("datastore", d_workflow.get("datastore"))))

                # vérification des appels à generate
                self.assertEqual(o_mock_action_generate.call_count, len(l_run_args))
                o_parent = None
                for d_action in l_actions:
                    o_mock_action_generate.assert_any_call(s_etape, d_action, o_parent, d_args_run_step["behavior"])
                    o_parent = o_mock_action

                # vérification des appels à résolve
                self.assertEqual(o_mock_action.resolve.call_count, len(l_run_args))

                # vérification des appels à run
                self.assertEqual(o_mock_action.run.call_count, len(l_run_args))
                for o_el in l_run_args:
                    o_mock_action.run.assert_any_call(o_el)

                # si monitoring : vérification des appels à monitoring
                if monitoring_until_end:
                    self.assertEqual(o_mock_action.resolve.call_count, len(l_run_args))
                    o_mock_action.monitoring_until_end.assert_any_call(callback=d_args_run_step["callback"], ctrl_c_action=None)

    def test_run_step(self) -> None:
        """test de run_step"""

        # fonction callback
        def callback(o_pe: ProcessingExecution) -> None:
            """fonction bidon pour affichage le traitement

            Args:
                o_pe (ProcessingExecution): traitement dont on suit le traitement
            """
            print(o_pe)

        d_workflow: Dict[str, Any] = {
            "workflow": {
                "steps": {
                    "1er etape": {},
                    "autre": {},
                    "mise-en-base": {
                        "actions": [{"type": "action1"}],
                    },
                    "mise-en-base2": {
                        "actions": [{"type": "action2-1"}, {"type": "action2-2"}],
                    },
                    "mise-en-base3": {
                        "actions": [{"type": "action3", "datastore": "datastore_3"}],
                    },
                    "mise-en-base4": {
                        "actions": [{"type": "action4-1", "datastore": "datastore_4-1"}, {"type": "action4-2"}],
                    },
                }
            }
        }
        # ajout datastore
        d_workflow_2: Dict[str, Any] = {"datastore": "datastore_workflow", **d_workflow.copy()}
        # tag + commentaire au niveau workflow + étape
        d_workflow_3: Dict[str, Any] = {
            "workflow": {
                "steps": {
                    "mise-en-base": {
                        "actions": [{"type": "action1"}],
                        "comments": ["commentaire step 1", "commentaire step 2"],
                        "tags": {"key_step": "val"},
                    }
                },
            },
            "comments": ["commentaire workflow 1", "commentaire workflow 2"],
            "tags": {"key_workflow": "val"},
        }
        s_datastore = "datastore_force"

        d_args: Dict[str, Any] = {
            "callback": None,
            "behavior": None,
            "datastore": None,
            "comments": [],
            "tags": {},
        }
        # test simple sans s_datastore
        self.run_run_step({**d_args, "step_name": "mise-en-base"}, d_workflow, [None])
        self.run_run_step({**d_args, "step_name": "mise-en-base2"}, d_workflow, [None, None])

        # datastore au niveau des étapes
        self.run_run_step({**d_args, "step_name": "mise-en-base3"}, d_workflow, ["datastore_3"])
        self.run_run_step({**d_args, "step_name": "mise-en-base4"}, d_workflow, ["datastore_4-1", None])

        # datastore au niveau du workflow + étapes
        self.run_run_step({**d_args, "step_name": "mise-en-base"}, d_workflow_2, ["datastore_workflow"])
        self.run_run_step({**d_args, "step_name": "mise-en-base3"}, d_workflow_2, ["datastore_3"])
        self.run_run_step({**d_args, "step_name": "mise-en-base4"}, d_workflow_2, ["datastore_4-1", "datastore_workflow"])

        # datastore au niveau du workflow + étape + forcé dans l'appel
        self.run_run_step({**d_args, "step_name": "mise-en-base", "datastore": s_datastore}, d_workflow, [s_datastore])
        self.run_run_step({**d_args, "step_name": "mise-en-base", "datastore": s_datastore}, d_workflow_2, [s_datastore])
        self.run_run_step({**d_args, "step_name": "mise-en-base3", "datastore": s_datastore}, d_workflow_2, [s_datastore])
        self.run_run_step({**d_args, "step_name": "mise-en-base4", "datastore": s_datastore}, d_workflow_2, [s_datastore, s_datastore])
        self.run_run_step({**d_args, "step_name": "mise-en-base4", "datastore": s_datastore}, d_workflow_2, [s_datastore, s_datastore], output_type="offering")

        # test pour les commentaires + tags
        self.run_run_step({**d_args, "step_name": "mise-en-base", "datastore": s_datastore}, d_workflow_3, [s_datastore])
        self.run_run_step({**d_args, "step_name": "mise-en-base", "datastore": s_datastore, "comments": ["commentaire 1", "commentaire 2"], "tags": {"workflow": "val"}}, d_workflow_3, [s_datastore])

        # étape qui n'existe pas
        self.run_run_step({**d_args, "step_name": "existe_pas"}, d_workflow, [], error_message="L'étape existe_pas n'est pas définie dans le workflow nom")

        # test avec monitoring
        self.run_run_step({**d_args, "step_name": "mise-en-base"}, d_workflow, [None], monitoring_until_end=["SUCCESS"], output_type="upload")
        self.run_run_step({**d_args, "step_name": "mise-en-base"}, d_workflow, [None], monitoring_until_end=["SUCCESS"], output_type="stored_data")
        self.run_run_step({**d_args, "step_name": "mise-en-base4"}, d_workflow_2, ["datastore_4-1", "datastore_workflow"], monitoring_until_end=["SUCCESS", "SUCCESS"], output_type="stored_data")
        self.run_run_step(
            {**d_args, "step_name": "mise-en-base"},
            d_workflow,
            [None],
            monitoring_until_end=["FAILURE"],
            error_message="L'exécution de traitement {action} ne s'est pas bien passée. Sortie FAILURE.",
            output_type="stored_data",
        )
        self.run_run_step(
            {**d_args, "step_name": "mise-en-base"},
            d_workflow,
            [None],
            monitoring_until_end=["ABORTED"],
            error_message="L'exécution de traitement {action} ne s'est pas bien passée. Sortie ABORTED.",
            output_type="stored_data",
        )
        self.run_run_step(
            {**d_args, "step_name": "mise-en-base4"},
            d_workflow_2,
            ["datastore_4-1", "datastore_workflow"],
            monitoring_until_end=["SUCCESS", "ABORTED"],
            error_message="L'exécution de traitement {action} ne s'est pas bien passée. Sortie ABORTED.",
            output_type="stored_data",
        )
        # callbable
        self.run_run_step({**d_args, "step_name": "mise-en-base", "callback": callback}, d_workflow, [None], monitoring_until_end=["SUCCESS", "SUCCESS"], output_type="stored_data")
        # behavior
        self.run_run_step({**d_args, "step_name": "mise-en-base", "behavior": "DELETE"}, d_workflow, [None])
        self.run_run_step(
            {**d_args, "step_name": "mise-en-base", "callback": callback, "behavior": "DELETE"}, d_workflow, [None], monitoring_until_end=["SUCCESS", "SUCCESS"], output_type="stored_data"
        )

        # itérations
        d_workflow_4: Dict[str, Any] = {
            "workflow": {
                "steps": {
                    "mise-en-base": {
                        "actions": [{"type": "action4-{ma_clef}", "datastore": "datastore_4-1"}, {"type": "action4-{ma_clef}"}],
                        "iter_vals": ["a", "b", "c"],
                        "iter_key": "ma_clef",
                    },
                    "mise-en-base-2": {
                        "actions": [{"type": "action4-{ma_clef}", "datastore": "datastore_4-1"}, {"type": "action4-{ma_clef.nom}"}],
                        "iter_vals": [{"nom": "a"}, {"nom": "b"}, {"nom": "c"}],
                        "iter_key": "ma_clef",
                    },
                    "mise-en-base-3": {
                        "actions": [],
                        "iter_key": "ma_clef",
                    },
                    "mise-en-base-4": {
                        "actions": [],
                        "iter_vals": [{"nom": "a"}, {"nom": "b"}, {"nom": "c"}],
                    },
                }
            }
        }
        self.run_run_step({**d_args, "step_name": "mise-en-base", "datastore": s_datastore}, d_workflow_4, [s_datastore] * 6)
        self.run_run_step({**d_args, "step_name": "mise-en-base-2", "datastore": s_datastore}, d_workflow_4, [s_datastore] * 6)
        s_message = "Une seule des clefs iter_vals ou iter_key est trouvée: il faut mettre les deux valeurs ou aucune. Étape mise-en-base-3 workflow nom"
        self.run_run_step({**d_args, "step_name": "mise-en-base-3", "datastore": s_datastore}, d_workflow_4, [], error_message=s_message)
        s_message = "Une seule des clefs iter_vals ou iter_key est trouvée: il faut mettre les deux valeurs ou aucune. Étape mise-en-base-4 workflow nom"
        self.run_run_step({**d_args, "step_name": "mise-en-base-4", "datastore": s_datastore}, d_workflow_4, [], error_message=s_message)

    def run_generation(
        self,
        expected_type: Type[ActionAbstract],
        name: str,
        dico_def: Dict[str, Any],
        parent: Optional[ActionAbstract] = None,
        behavior: Optional[str] = None,
        with_beavior: bool = True,
    ) -> None:
        """lancement de la commande de génération

        Args:
            expected_type (Type[ActionAbstract]): type de la classe attendu en sortie de la fonction
            name (str): nom du contexte du workflow
            dico_def (Dict[str, Any]): dictionnaire de l'action
            parent (Optional[ActionAbstract], optional): parent de l'action.
            behavior (Optional[str], optional): comportement à adopter.
        """

        # mock des fonction __init__ des classes action généré
        def new_init(workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional[ActionAbstract] = None, behavior: Optional[str] = None) -> None:
            print("new - ", workflow_context, definition_dict, parent_action, behavior)

        d_mock = {}
        # fmt: off
        with patch.object(DeleteAction, "__init__", wraps=new_init) as d_mock["DeleteAction"], \
        patch.object(ProcessingExecutionAction, "__init__", wraps=new_init) as d_mock["ProcessingExecutionAction"], \
        patch.object(ConfigurationAction, "__init__", wraps=new_init) as d_mock["ConfigurationAction"], \
        patch.object(OfferingAction, "__init__", wraps=new_init) as d_mock["OfferingAction"], \
        patch.object(SynchronizeOfferingAction, "__init__", wraps=new_init) as d_mock["SynchronizeOfferingAction"], \
        patch.object(CopyConfigurationAction, "__init__", wraps=new_init) as d_mock["CopyConfigurationAction"], \
        patch.object(EditUsedDataConfigurationAction, "__init__", wraps=new_init) as d_mock["EditUsedDataConfigurationAction"], \
        patch.object(EditAction, "__init__", wraps=new_init) as d_mock["EditAction"]:
            # fmt: on
            # exécution
            o_action_generated = Workflow.generate(name, dico_def, parent, behavior=behavior)
            # tests
            self.assertIsInstance(o_action_generated, expected_type)
            for s_class_name, o_mock in d_mock.items():
                if expected_type.__name__ == s_class_name and with_beavior:
                    o_mock.assert_called_once_with(name, dico_def, parent, behavior=behavior)
                elif expected_type.__name__ == s_class_name and not with_beavior:
                    o_mock.assert_called_once_with(name, dico_def, parent)
                else:
                    o_mock.assert_not_called()

    def test_generate(self) -> None:
        """test de generate"""
        # mock pour les parents
        o_mock_parent = MagicMock()

        # test type processing-execution
        self.run_generation(ProcessingExecutionAction, "name", {"type": "processing-execution"}, None, behavior="DELETE")
        self.run_generation(ProcessingExecutionAction, "name", {"type": "processing-execution"}, o_mock_parent)

        # test type configuration
        self.run_generation(ConfigurationAction, "name", {"type": "configuration"}, None, behavior="DELETE")
        self.run_generation(ConfigurationAction, "name", {"type": "configuration"}, o_mock_parent)

        # test type offering
        self.run_generation(OfferingAction, "name", {"type": "offering"}, None, behavior="DELETE")
        self.run_generation(OfferingAction, "name", {"type": "offering"}, o_mock_parent)

        # test type delete-entity
        self.run_generation(DeleteAction, "name", {"type": "delete-entity"}, o_mock_parent, with_beavior=False)
        # test type synchronize-offering
        self.run_generation(SynchronizeOfferingAction, "name", {"type": "synchronize-offering"}, o_mock_parent, with_beavior=False)
        # test type copie-configuration
        self.run_generation(CopyConfigurationAction, "name", {"type": "copy-configuration"}, o_mock_parent, with_beavior=True)
        # test type edit-entity
        self.run_generation(EditAction, "name", {"type": "edit-entity"}, o_mock_parent, with_beavior=False)
        # test type permission
        self.run_generation(PermissionAction, "name", {"type": "permission"}, o_mock_parent, with_beavior=False)
        # test type used_data-configuration
        self.run_generation(EditUsedDataConfigurationAction, "name", {"type": "used_data-configuration"}, o_mock_parent, with_beavior=False)

    def test_open_workflow(self) -> None:
        """Test de la fonction open_workflow."""
        p_workflows = Config().data_dir_path / "workflows"
        # On teste le workflow generic_archive.jsonc
        o_workflow_1 = Workflow.open_workflow(p_workflows / "generic_archive.jsonc")
        self.assertEqual(o_workflow_1.name, "generic_archive.jsonc")
        self.assertEqual(len(o_workflow_1.steps), 4)
        # On teste le workflow generic_vecteur.jsonc
        o_workflow_2 = Workflow.open_workflow(p_workflows / "generic_vecteur.jsonc", "wfs generic")
        self.assertEqual(o_workflow_2.name, "wfs generic")
        self.assertEqual(len(o_workflow_2.steps), 8)
        # On teste un fichier inexistant
        with self.assertRaises(GpfSdkError) as o_arc:
            Workflow.open_workflow(Path("pas_là.json"))
        self.assertEqual(o_arc.exception.message, "Le fichier de workflow pas_là.json est introuvable. Contactez le support.")

    def test_validate(self) -> None:
        """Test de la fonction validate."""
        p_workflows = Config.data_dir_path / "workflows"

        # On valide le workflow generic_archive.jsonc
        o_workflow_1 = Workflow.open_workflow(p_workflows / "generic_archive.jsonc")
        self.assertFalse(o_workflow_1.validate())

        # On valide le workflow generic_vecteur.jsonc
        o_workflow_2 = Workflow.open_workflow(p_workflows / "generic_vecteur.jsonc")
        self.assertFalse(o_workflow_2.validate())

        # On ne valide pas le workflow bad-workflow.jsonc
        p_workflow = GpfTestCase.data_dir_path / "workflows" / "bad-workflow.jsonc"
        o_workflow_2 = Workflow(p_workflow.stem, JsonHelper.load(p_workflow))
        l_errors = o_workflow_2.validate()
        self.assertTrue(l_errors)
        self.assertIn("Le workflow ne respecte pas le schéma demandé. Erreur de schéma :", l_errors[0])
        self.assertEqual(l_errors[1], "Le parent « parent-not-found » de l'étape « no-parent-no-action » n'est pas défini dans le workflow.")
        self.assertEqual(l_errors[2], "L'étape « no-parent-no-action » n'a aucune action de défini.")
        self.assertEqual(l_errors[3], "L'action n°1 de l'étape « configuration-wfs » n'est pas instantiable (Aucune correspondance pour ce type d'action : type-not-found).")
        self.assertEqual(l_errors[4], "L'action n°2 de l'étape « configuration-wfs » n'a pas la clef obligatoire ('type').")
        ## cas erreur non valide
        with patch.object(Workflow, "generate", side_effect=Exception("error")) as o_mock_jsonschema:
            l_errors = o_workflow_1.validate()
            self.assertTrue(l_errors)
            self.assertEqual(l_errors[0], "L'action n°1 de l'étape « intégration-archive-livrée » lève une erreur inattendue (error).")
            self.assertEqual(l_errors[1], "L'action n°1 de l'étape « patch-donnée-stockée » lève une erreur inattendue (error).")
            self.assertEqual(l_errors[2], "L'action n°1 de l'étape « configuration-archive-livrée » lève une erreur inattendue (error).")
            self.assertEqual(l_errors[3], "L'action n°1 de l'étape « publication-archive-livrée » lève une erreur inattendue (error).")

        # problème avec le schema du fichier workflow
        p_schema = Config.conf_dir_path / "json_schemas" / "workflow.json"
        with patch.object(jsonschema, "validate", side_effect=jsonschema.exceptions.SchemaError("error")) as o_mock_jsonschema:
            with self.assertRaises(GpfSdkError) as o_arc:
                o_workflow_2.validate()
            self.assertEqual(o_arc.exception.message, f"Le schéma décrivant la structure d'un workflow {p_schema} est invalide. Contactez le support.")
            o_mock_jsonschema.assert_called_once()

    def test_get_actions(self) -> None:
        """Test de get_actions."""
        # Données test
        d_action_0 = {"type": "action_0"}
        d_action_1 = {"type": "action_1"}
        d_action_2 = {"type": "action_2"}
        d_workflow = {
            "workflow": {
                "steps": {
                    "step_name": {
                        "actions": [
                            d_action_0,
                            d_action_1,
                            d_action_2,
                        ],
                    },
                }
            }
        }
        l_actions = ["action_0", "action_1", "action_2"]
        # Instanciation workflow
        o_workflow = Workflow("workflow_name", d_workflow)
        # On mock generate
        with patch.object(Workflow, "generate", side_effect=l_actions) as o_mock_generate:
            # Appel fonction testée
            l_action_get = o_workflow.get_actions("step_name")
            # Vérification
            self.assertListEqual(l_actions, l_action_get)
            self.assertEqual(o_mock_generate.call_count, 3)
            o_mock_generate.assert_any_call("step_name", d_action_0, None)
            o_mock_generate.assert_any_call("step_name", d_action_1, "action_0")
            o_mock_generate.assert_any_call("step_name", d_action_2, "action_1")

    def test_get_action(self) -> None:
        """Test de get_action."""
        # Données test
        l_actions = ["action_0", "action_1", "action_2"]
        # Instanciation workflow
        o_workflow = Workflow("workflow_name", {})
        # On demande l'action i
        for i, o_action in enumerate(l_actions):
            with patch.object(o_workflow, "get_actions", return_value=l_actions) as o_mock_get_actions:
                # Appel fonction testée
                o_action_get = o_workflow.get_action("stem_name", i)
                # Vérifications
                self.assertEqual(o_action, o_action_get)
                o_mock_get_actions.assert_called_once_with("stem_name")

    def test_get_all_steps(self) -> None:
        """test de get_all_steps"""
        o_workflow = Workflow(
            "workflow_name",
            {
                "workflow": {
                    "steps": {
                        "etape1": {"parents": [], "actions": []},
                        "etape2A": {"parents": ["etape1"], "actions": []},
                        "etape2B": {"parents": ["etape1"], "actions": []},
                        "etape3": {"parents": ["etape2A", "etape2B"], "actions": []},
                    },
                },
            },
        )
        l_steps = o_workflow.get_all_steps()
        self.assertEqual(l_steps[0], "Etape « etape1 » [parent(s) : ]")
        self.assertEqual(l_steps[1], "Etape « etape2A » [parent(s) : etape1]")
        self.assertEqual(l_steps[2], "Etape « etape2B » [parent(s) : etape1]")
        self.assertEqual(l_steps[3], "Etape « etape3 » [parent(s) : etape2A, etape2B]")
