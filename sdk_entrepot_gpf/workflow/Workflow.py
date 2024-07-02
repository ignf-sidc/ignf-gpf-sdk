import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import jsonschema
from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper

from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.workflow.Errors import WorkflowError
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.workflow.action.CopyConfigurationAction import CopyConfigurationAction
from sdk_entrepot_gpf.workflow.action.DeleteAction import DeleteAction
from sdk_entrepot_gpf.workflow.action.EditAction import EditAction
from sdk_entrepot_gpf.workflow.action.EditUsedDataConfigurationAction import EditUsedDataConfigurationAction
from sdk_entrepot_gpf.workflow.action.PermissionAction import PermissionAction
from sdk_entrepot_gpf.workflow.action.ProcessingExecutionAction import ProcessingExecutionAction
from sdk_entrepot_gpf.workflow.action.ConfigurationAction import ConfigurationAction
from sdk_entrepot_gpf.workflow.action.OfferingAction import OfferingAction
from sdk_entrepot_gpf.workflow.action.SynchronizeOfferingAction import SynchronizeOfferingAction
from sdk_entrepot_gpf.workflow.resolver.DictResolver import DictResolver
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver
from sdk_entrepot_gpf.workflow.action.AccessAction import AccessAction


class Workflow:
    """Cette classe permet de décrire et de lancer un workflow.

    Un workflow est une suite de création d'entités (exécution de traitement,
    configuration et offre) permettant de traiter puis de publier des données
    via la Géoplateforme.

    Chaque création d'entité est représentée par la classe Action.

    Attributes:
        __name (str): Nom du workflow
        __raw_definition_dict (dict): Définition du workflow
    """

    def __init__(self, name: str, raw_dict: Dict[str, Any]) -> None:
        """La classe est instanciée à partir d'un nom et d'une représentation du workflow.

        La représentation du workflow peut provenir par exemple d'un fichier JSON.

        Args:
            name (str) : Nom du workflow
            raw_dict (dict): Workflow non résolu
        """
        self.__name = name
        self.__raw_definition_dict = raw_dict
        self.__datastore = raw_dict["datastore"] if "datastore" in raw_dict else None

    def get_raw_dict(self) -> Dict[str, Any]:
        """Renvoie le dictionnaire de définition du workflow.

        Returns:
            le dictionnaire de définition du workflow
        """
        return self.__raw_definition_dict

    def run_step(
        self,
        step_name: str,
        callback: Optional[Callable[[ProcessingExecution], None]] = None,
        ctrl_c_action: Optional[Callable[[], bool]] = None,
        behavior: Optional[str] = None,
        datastore: Optional[str] = None,
        comments: List[str] = [],
        tags: Dict[str, str] = {},
    ) -> List[StoreEntity]:
        """Lance une étape du workflow à partir de son nom. Liste les entités créées par chaque action et retourne la liste.

        Args:
            step_name (str): nom de l'étape
            callback (Optional[Callable[[ProcessingExecution], None]], optional): callback de suivi si création d'une exécution de traitement.
            ctrl_c_action (Optional[Callable[[], bool]], optional): gestion du ctrl-C lors d'une exécution de traitement.
            behavior (Optional[str]): comportement à adopter si une entité existe déjà sur l'entrepôt.
            datastore (Optional[str]): id du datastore à utiliser. Si None, le datastore sera le premier trouvé dans l'action puis dans workflow puis dans configuration.
            comments (Optional[List[str]]): liste des commentaire à rajouté à toute les actions de l'étape (les cas de doublons sont géré).
            tags (Optional[Dict[str, str]]): dictionnaire des tag à rajouté pour toutes les action de l'étape. Écrasé par ceux du workflow, de l'étape et de l'action si les clef sont les même.

        Raises:
            WorkflowError: levée si un problème apparaît pendant l'exécution du workflow

        Returns:
            List[StoreEntity]: liste des entités créées
        """
        Config().om.info(f"Lancement de l'étape {step_name}...")
        # Création d'une liste pour stocker les entités créées
        l_store_entity: List[StoreEntity] = []
        # Récupération de l'étape dans la définition de workflow (datastore forcé, sinon datastore du workflow/None)
        d_step_definition = self.__get_step_definition(step_name, comments, tags, datastore if datastore else self.__datastore)
        # initialisation des actions parentes
        o_parent_action: Optional[ActionAbstract] = None
        # Pour chaque action définie dans le workflow, instanciation de l'objet Action puis création sur l'entrepôt
        for d_action_raw in d_step_definition["actions"]:
            # création de l'action
            o_action = Workflow.generate(step_name, d_action_raw, o_parent_action, behavior)
            # choix du datastore
            ## datastore donné en paramètre
            ## sinon datastore du workflow au niveau de l'action
            ## sinon datastore du workflow au niveau de l'étape
            ## sinon datastore du workflow au niveau global (self.__datastore)
            # NB: si None il sera récupérer dans la configuration
            s_use_datastore = datastore if datastore else o_action.definition_dict.get("datastore", d_step_definition.get("datastore", self.__datastore))

            # résolution
            o_action.resolve(datastore=s_use_datastore)
            # exécution de l'action
            Config().om.info(f"Exécution de l'action '{o_action.workflow_context}-{o_action.index}'...")
            o_action.run(s_use_datastore)
            # on attend la fin de l'exécution si besoin
            if isinstance(o_action, ProcessingExecutionAction):
                s_status = o_action.monitoring_until_end(callback=callback, ctrl_c_action=ctrl_c_action)
                if s_status != ProcessingExecution.STATUS_SUCCESS:
                    s_error_message = f"L'exécution de traitement {o_action} ne s'est pas bien passée. Sortie {s_status}."
                    Config().om.error(s_error_message)
                    raise WorkflowError(s_error_message)

            # On récupère l'entité créée par l'Action
            if isinstance(o_action, ProcessingExecutionAction):
                # Ajout de upload et/ou stored_data
                if o_action.upload is not None:
                    l_store_entity.append(o_action.upload)
                if o_action.stored_data is not None:
                    l_store_entity.append(o_action.stored_data)
            elif isinstance(o_action, ConfigurationAction):
                if o_action.configuration is not None:
                    l_store_entity.append(o_action.configuration)
            elif isinstance(o_action, OfferingAction):
                if o_action.offering is not None:
                    l_store_entity.append(o_action.offering)

            # Message de fin
            Config().om.info(f"Exécution de l'action '{o_action.workflow_context}-{o_action.index}' : terminée")
            # cette action sera la parente de la suivante
            o_parent_action = o_action
        # Retour de la liste
        return l_store_entity

    def __get_step_definition(self, step_name: str, comments: List[str] = [], tags: Dict[str, str] = {}, datastore: Optional[str] = None) -> Dict[str, Any]:
        """Renvoie le dictionnaire correspondant à une étape du workflow à partir de son nom.
        Lève une WorkflowError avec un message clair si l'étape n'est pas trouvée.

        Args:
            step_name (str): nom de l'étape
            comments (Optional[List[str]]): liste des commentaire à rajouté à toute les actions de l'étape (les cas de doublons sont géré).
            tags (Optional[Dict[str, str]]): dictionnaire des tag à rajouté pour toutes les action de l'étape. Écrasé par ceux du workflow, de l'étape et de l'action si les clef sont les même.

        Raises:
            WorkflowExecutionError: est levée si l'étape n'existe pas dans le workflow

        Returns:
            Dict[str, Any]: dictionnaire de l'étape
        """
        # Recherche de l'étape correspondante
        if step_name not in self.__raw_definition_dict["workflow"]["steps"]:
            # Si on passe le if, c'est que l'étape n'existe pas dans la définition du workflow
            s_error_message = f"L'étape {step_name} n'est pas définie dans le workflow {self.__name}"
            Config().om.error(s_error_message)
            raise WorkflowError(s_error_message)

        # récupération e l'étape :
        d_step = dict(self.__raw_definition_dict["workflow"]["steps"][step_name])

        # Gestion des itérations
        if "iter_vals" in d_step and "iter_key" in d_step:
            # on itère sur les clefs
            l_actions = []
            s_actions = str(json.dumps(d_step["actions"], ensure_ascii=False))

            # on lance la résolution sur iter_vals
            d_step["iter_vals"] = JsonHelper.loads(GlobalResolver().resolve(json.dumps(d_step["iter_vals"]), datastore=datastore), "iter_vals résolu")
            Config().om.debug(f"iter_vals : {d_step['iter_vals']}")
            if isinstance(d_step["iter_vals"][0], (str, float, int)):
                # si la liste est une liste de string, un int ou float : on remplace directement
                for o_val in d_step["iter_vals"]:
                    l_actions += JsonHelper.loads(s_actions.replace("{" + d_step["iter_key"] + "}", o_val), "iter_val str/float/int")
            else:
                # on a une liste de sous dict ou apparenté on utilise un résolveur
                for i, o_val in enumerate(d_step["iter_vals"]):
                    l_actions += JsonHelper.loads(s_actions.replace(d_step["iter_key"], f"iter_resolve_{i}"), f"iter_vals list({i})")
                    GlobalResolver().add_resolver(DictResolver(f"iter_resolve_{i}", o_val))
            d_step["actions"] = l_actions

        elif "iter_vals" in d_step or "iter_key" in d_step:
            # on a une seule des deux clef
            s_error_message = f"Une seule des clefs iter_vals ou iter_key est trouvée: il faut mettre les deux valeurs ou aucune. Étape {step_name} workflow {self.__name}"
            Config().om.error(s_error_message)
            raise WorkflowError(s_error_message)

        # on récupère les commentaires commun au workflow et à l'étape
        comments.extend(self.__raw_definition_dict.get("comments", []))
        comments.extend(d_step.get("comments", []))

        # on récupère les tags commun au workflow et à l'étape
        tags.update(self.__raw_definition_dict.get("tags", {}))
        tags.update(d_step.get("tags", {}))

        # Ajout des commentaires et des tags à chaque actions
        for d_action in d_step["actions"]:
            d_action["comments"] = [*comments, *d_action.get("comments", [])]
            d_action["tags"] = {**tags, **d_action.get("tags", {})}

        return d_step

    def get_actions(self, step_name: str) -> List[ActionAbstract]:
        """Instancie les actions de l'étape demandée et en renvoie la liste.

        Args:
            step_name (str): nom de l'étape

        Returns:
            liste des actions de l'étape
        """
        # Création d'une liste pour stocker les actions
        l_actions: List[ActionAbstract] = []
        # Récupération de l'étape dans la définition de workflow
        d_step_definition = self.__get_step_definition(step_name)
        # initialisation des actions parentes
        o_parent_action: Optional[ActionAbstract] = None
        for d_action_raw in d_step_definition["actions"]:
            # création de l'action
            o_action = Workflow.generate(f"{step_name}", d_action_raw, o_parent_action)
            # Maj action parente
            o_parent_action = o_action
            # Ajout
            l_actions.append(o_action)
        # On renvoie la liste d'actions
        return l_actions

    def get_action(self, step_name: str, number: int) -> ActionAbstract:
        """Instancie l'action de l'étape demandée.

        Args:
            step_name (str): nom de l'étape
            number (int): numéro de l'action (0 pour la première)

        Returns:
            action demandée
        """
        # On renvoie l'action demandée
        return self.get_actions(step_name)[number]

    @property
    def name(self) -> str:
        return self.__name

    @property
    def steps(self) -> List[str]:
        return list(self.__raw_definition_dict["workflow"]["steps"].keys())

    @staticmethod
    def generate(  # pylint: disable=too-many-return-statements
        workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional[ActionAbstract] = None, behavior: Optional[str] = None
    ) -> ActionAbstract:
        """Génération de la bonne action selon le type indiqué dans la représentation du workflow.

        Args:
            workflow_context (str): nom du context du workflow
            definition_dict (Dict[str, Any]): dictionnaire définissant l'action
            parent_action (Optional[ActionAbstract], optional): action précédente (si étape à plusieurs action). Defaults to None.
            behavior (Optional[str]): comportement à adopter si l'entité créée par l'action existe déjà sur l'entrepôt. Defaults to None.

        Returns:
            instance permettant de lancer l'action
        """
        if definition_dict["type"] == "delete-entity":
            return DeleteAction(workflow_context, definition_dict, parent_action)
        if definition_dict["type"] == "processing-execution":
            return ProcessingExecutionAction(workflow_context, definition_dict, parent_action, behavior=behavior)
        if definition_dict["type"] == "configuration":
            return ConfigurationAction(workflow_context, definition_dict, parent_action, behavior=behavior)
        if definition_dict["type"] == "copy-configuration":
            return CopyConfigurationAction(workflow_context, definition_dict, parent_action, behavior=behavior)
        if definition_dict["type"] == "used_data-configuration":
            return EditUsedDataConfigurationAction(workflow_context, definition_dict, parent_action)
        if definition_dict["type"] == "offering":
            return OfferingAction(workflow_context, definition_dict, parent_action, behavior=behavior)
        if definition_dict["type"] == "synchronize-offering":
            return SynchronizeOfferingAction(workflow_context, definition_dict, parent_action)
        if definition_dict["type"] == "edit-entity":
            return EditAction(workflow_context, definition_dict, parent_action)
        if definition_dict["type"] == "access":
            return AccessAction(workflow_context, definition_dict, parent_action)
        if definition_dict["type"] == "permission":
            return PermissionAction(workflow_context, definition_dict, parent_action)
        raise WorkflowError(f"Aucune correspondance pour ce type d'action : {definition_dict['type']}")

    @staticmethod
    def open_workflow(workflow_path: Path, workflow_name: Optional[str] = None) -> "Workflow":
        """Instancie un Workflow en vérifiant le schéma fourni.

        Args:
            workflow_path (Path): chemin vers le fichier de workflow.
            workflow_name (Optional[str], optional): nom du workflow, si None, le nom du fichier est utilisé.. Defaults to None.

        Returns:
            workflow instancié
        """
        # Chemin vers le schéma des workflows
        p_schema = Config.conf_dir_path / "json_schemas" / "workflow.json"
        # Vérification du schéma
        JsonHelper.validate_json(
            workflow_path,
            p_schema,
            schema_not_found_pattern="Le schéma décrivant la structure d'un workflow {schema_path} est introuvable. Contactez le support.",
            schema_not_parsable_pattern="Le schéma décrivant la structure d'un workflow {schema_path} est non parsable. Contactez le support.",
            schema_not_valid_pattern="Le schéma décrivant la structure d'un workflow {schema_path} est invalide. Contactez le support.",
            json_not_found_pattern="Le fichier de workflow {json_path} est introuvable. Contactez le support.",
            json_not_parsable_pattern="Le fichier de workflow {json_path} est non parsable. Contactez le support.",
            json_not_valid_pattern="Le fichier de workflow {json_path} est invalide. Contactez le support.",
        )
        # Ouverture du json
        d_workflow = JsonHelper.load(workflow_path)
        # Si le nom n'est pas défini, on prend celui du fichier
        if workflow_name is None:
            workflow_name = workflow_path.name
        # Instanciation et retour
        return Workflow(workflow_name, d_workflow)

    def validate(self) -> List[str]:
        """Valide le workflow en s'assurant qu'il est cohérent. Retourne la liste des erreurs trouvées.

        Returns:
            liste des erreurs trouvées
        """
        l_errors: List[str] = []

        # Chemin vers le schéma des workflows
        p_schema = Config.conf_dir_path / "json_schemas" / "workflow.json"
        # Ouverture du schéma
        d_schema = JsonHelper.load(
            p_schema,
            file_not_found_pattern="Le schéma décrivant la structure d'un workflow {schema_path} est introuvable. Contactez le support.",
            file_not_parsable_pattern="Le schéma décrivant la structure d'un workflow {schema_path} est non parsable. Contactez le support.",
        )
        # Vérification du schéma
        try:
            jsonschema.validate(instance=self.__raw_definition_dict, schema=d_schema)
        # Récupération de l'erreur levée si le schéma est invalide
        except jsonschema.exceptions.SchemaError as e:
            raise GpfSdkError(f"Le schéma décrivant la structure d'un workflow {p_schema} est invalide. Contactez le support.") from e
        # Récupération de l'erreur levée si le json est invalide
        except jsonschema.exceptions.ValidationError as e:
            l_errors.append(f"Le workflow ne respecte pas le schéma demandé. Erreur de schéma :\n--- début ---\n{e}\n--- fin ---")

        # Maintenant que l'on a fait ça, on peut faire des vérifications pratiques

        # Pour chaque étape
        for s_step_name in self.steps:
            # 1. Est-ce que les parents de chaque étape existent ?
            # Pour chaque parent de l'étape
            for s_parent_name in self.__get_step_definition(s_step_name)["parents"]:
                # S'il n'est pas dans la liste
                if not s_parent_name in self.steps:
                    l_errors.append(f"Le parent « {s_parent_name} » de l'étape « {s_step_name} » n'est pas défini dans le workflow.")
            # 2. Est-ce que chaque action a au moins une étape ?
            if not self.__get_step_definition(s_step_name)["actions"]:
                l_errors.append(f"L'étape « {s_step_name} » n'a aucune action de défini.")
            # 3. Est-ce que chaque action de chaque étape est instantiable ?
            # Pour chaque action de l'étape
            for i, d_action in enumerate(self.__get_step_definition(s_step_name)["actions"], 1):
                # On tente de l'instancier
                try:
                    Workflow.generate(self.name, d_action)
                except WorkflowError as e_workflow_error:
                    l_errors.append(f"L'action n°{i} de l'étape « {s_step_name} » n'est pas instantiable ({e_workflow_error}).")
                except KeyError as e_key_error:
                    l_errors.append(f"L'action n°{i} de l'étape « {s_step_name} » n'a pas la clef obligatoire ({e_key_error}).")
                except Exception as e:
                    l_errors.append(f"L'action n°{i} de l'étape « {s_step_name} » lève une erreur inattendue ({e}).")

        # On renvoie la liste
        return l_errors

    def get_all_steps(self) -> List[str]:
        """Retourne la liste des différentes étapes et de leurs parents.

        Returns:
            liste des étapes (et des parents)
        """
        l_steps: List[str] = []

        # Pour chaque étape
        for s_step_name in self.steps:
            # on récupère les parents
            l_parents = self.__get_step_definition(s_step_name)["parents"]
            s_parents = ", ".join(l_parents)
            # on ajoute dans la liste
            l_steps.append(f"Etape « {s_step_name} » [parent(s) : {s_parents}]")

        # On renvoie la liste
        return l_steps
