import time
from typing import Any, Callable, Dict, List, Optional, Union

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction

# cSpell:ignore datasheet vectordb creat


class ProcessingExecutionAction(ActionAbstract):
    """Classe dédiée à la création des ProcessingExecution.

    Attributes:
        __workflow_context (str): nom du context du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
        __processing_execution (Optional[ProcessingExecution]): représentation Python de l'exécution de traitement créée
        __Upload (Optional[Upload]): représentation Python de la livraison en sortie (null si donnée stockée en sortie)
        __StoredData (Optional[StoredData]): représentation Python de la donnée stockée en sortie (null si livraison en sortie)
    """

    # Comportements possibles pour une ProcessingExecutionAction
    BEHAVIORS = [
        ActionAbstract.BEHAVIOR_STOP,
        ActionAbstract.BEHAVIOR_DELETE,
        ActionAbstract.BEHAVIOR_CONTINUE,
        ActionAbstract.BEHAVIOR_RESUME,
    ]

    # status possibles d'une ProcessingExecution (status délivrés par l'api)
    # STATUS_CREATED
    # STATUS_ABORTED STATUS_SUCCESS STATUS_FAILURE

    # status possibles d'une Stored data (status délivrés par l'api)
    # STATUS_CREATED
    # STATUS_UNSTABLE
    # STATUS_GENERATING STATUS_MODIFYING
    # STATUS_GENERATED

    def __init__(
        self, workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional["ActionAbstract"] = None, behavior: Optional[str] = None, compatibility_cartes: Optional[bool] = None
    ) -> None:
        super().__init__(workflow_context, definition_dict, parent_action)
        # l'exécution du traitement
        self.__processing_execution: Optional[ProcessingExecution] = None
        # les données en sortie
        self.__upload: Optional[Upload] = None
        self.__stored_data: Optional[StoredData] = None
        self.__no_output = False
        # donnée en entrée
        self.__inputs_upload: Optional[List[Upload]] = None
        self.__inputs_stored_data: Optional[List[StoredData]] = None
        # comportement (écrit dans la ligne de commande par l'utilisateur), sinon celui par défaut (dans la config) qui vaut STOP
        self.__behavior: str = behavior if behavior is not None else Config().get_str("processing_execution", "behavior_if_exists")
        self.__mode_cartes: Optional[bool] = compatibility_cartes if compatibility_cartes is not None else Config().get_bool("compatibility_cartes", "activate")

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Création d'une exécution de traitement et complétion de l'entité en sortie...", force_flush=True)
        # Création de l'exécution du traitement (attributs processing_execution et Upload/StoredData défini)
        self.__create_processing_execution(datastore)

        # Ajout des tags sur l'Upload ou la StoredData
        self.__add_tags()
        # Ajout des commentaires sur l'Upload ou la StoredData
        self.__add_comments()
        # Lancement du traitement
        self.__launch()
        # Affichage
        o_output_entity = self.__stored_data if self.__stored_data is not None else self.__upload if self.__upload is not None else "pas de donnée en sortie"
        Config().om.info(f"Exécution de traitement créée et lancée ({self.processing_execution}) et entité en sortie complétée ({o_output_entity}).")
        Config().om.info("Création d'une exécution de traitement et complétion de l'entité en sortie : terminé")

    def __gestion_new_output(self, datastore: Optional[str]) -> None:
        """gestion des behaviors quand il y a création d'un nouveau traitement.

        Args:
            datastore (Optional[str]): Identifiant du datastore.
        """
        # TODO : gérer également les Livraisons
        # On vérifie si une Donnée Stockée équivalente à celle du dictionnaire de définition (champ name) existe déjà sur la gpf
        o_stored_data = self.find_stored_data(datastore)
        # Si on a trouvé une Donnée Stockée sur la gpf :
        if o_stored_data is None:
            return
        # Comportement d'arrêt du programme
        if self.__behavior == self.BEHAVIOR_STOP:
            raise GpfSdkError(f"Impossible de créer l’exécution de traitement, une donnée stockée en sortie équivalente {o_stored_data} existe déjà.")

        # on met à jour o_stored_data pour avoir son status
        o_stored_data.api_update()
        # Comportement de suppression des entités détectées
        if self.__behavior == self.BEHAVIOR_DELETE or (o_stored_data["status"] == StoredData.STATUS_UNSTABLE and self.__behavior == self.BEHAVIOR_RESUME):
            Config().om.warning(f"Une donnée stockée équivalente à {o_stored_data} va être supprimée puis recréée.")
            # Suppression de la donnée stockée
            o_stored_data.api_delete()
            # on force à None pour que la création soit faite
            self.__processing_execution = None
        # Comportement "on continue l'exécution"
        elif self.__behavior in [self.BEHAVIOR_CONTINUE, self.BEHAVIOR_RESUME]:
            # on regarde si le résultat du traitement précédent est en échec (cas pour self.BEHAVIOR_RESUME, déjà traité)
            if o_stored_data["status"] == StoredData.STATUS_UNSTABLE:
                raise GpfSdkError(f"Le traitement précédent a échoué sur la donnée stockée en sortie {o_stored_data}. Impossible de lancer le traitement demandé.")

            # on est donc dans un des cas suivants :
            # le processing_execution a été créé mais pas exécuté (StoredData.STATUS_CREATED)
            # ou le processing execution est en cours d'exécution (StoredData.STATUS_GENERATING ou StoredData.STATUS_MODIFYING)
            # ou le processing execution est terminé (StoredData.STATUS_GENERATED)
            self.__stored_data = o_stored_data
            l_proc_exec = ProcessingExecution.api_list({"output_stored_data": o_stored_data.id}, datastore=datastore)
            if not l_proc_exec:
                raise GpfSdkError(f"Impossible de trouver l'exécution de traitement liée à la donnée stockée {o_stored_data}")
            # arbitrairement, on prend le premier de la liste
            self.__processing_execution = l_proc_exec[0]
            Config().om.info(f"La donnée stocké en sortie {o_stored_data} déjà existante, on reprend le traitement associé : {self.__processing_execution}.")
            return
        # Comportement non reconnu
        else:
            raise GpfSdkError(f"Le comportement {self.__behavior} n'est pas reconnu ({'|'.join(self.BEHAVIORS)}), l'exécution de traitement n'est pas possible.")

    def __gestion_update_entity(self, datastore: Optional[str]) -> None:
        """gestion des behaviors quand il y a mise à jour d'une entité.

        Args:
            datastore (Optional[str]): Identifiant du datastore.
        """
        if not "_id" in self.definition_dict["body_parameters"].get("output", {}).get("stored_data", {}):
            # on ne gère que les mises à jour des stored_data
            return
        # On recherche le traitement entre les données en entrée et celle en sortie
        o_stored_data = StoredData.api_get(self.definition_dict["body_parameters"]["output"]["stored_data"]["_id"], datastore=datastore)
        # Si on a trouvé une Donnée Stockée sur la gpf :
        if o_stored_data is None:
            raise GpfSdkError("La donnée en sortie est introuvable, impossible de faire la mise à jour.")

        d_filter = {
            "output_stored_data": o_stored_data.id,
            "processing": self.definition_dict["body_parameters"]["processing"],
        }
        if self.definition_dict["body_parameters"].get("inputs", {}).get("upload"):
            d_filter["input_upload"] = self.definition_dict["body_parameters"]["inputs"]["upload"][0]
        elif self.definition_dict["body_parameters"].get("inputs", {}).get("stored_data"):
            d_filter["input_stored_data"] = self.definition_dict["body_parameters"]["inputs"]["stored_data"][0]

        # On recherche le traitement
        l_proc_exec = ProcessingExecution.api_list(d_filter, datastore=datastore)
        # affinage de la recherche
        for o_proc_exec in l_proc_exec:
            o_proc_exec.api_update()
            # vérification des entrées (si on a plus d'une entrée):
            l_in_ids_upload = sorted(self.definition_dict["body_parameters"].get("inputs", {}).get("upload", []))
            l_in_ids_stored_data = sorted(self.definition_dict["body_parameters"].get("inputs", {}).get("stored_data", []))
            d_data_pe = o_proc_exec.get_store_properties()
            l_pe_ids_upload = sorted([o_upload["_id"] for o_upload in d_data_pe.get("inputs", {}).get("upload", [])])
            l_pe_ids_stored_data = sorted([o_upload["_id"] for o_upload in d_data_pe.get("inputs", {}).get("stored_data", [])])
            if l_in_ids_upload == l_pe_ids_upload and l_in_ids_stored_data == l_pe_ids_stored_data and d_data_pe["parameters"] == self.definition_dict["body_parameters"].get("parameters", {}):
                # les entrées, les sorties et paramètres correspondent, on a trouvé le traitement (o_proc_exec)
                break
        else:
            # aucun traitement trouvé
            return

        # Comportement d'arrêt du programme
        if self.__behavior == self.BEHAVIOR_STOP:
            raise GpfSdkError(f"Le traitement a déjà été lancé pour mettre à jour cette donnée {o_proc_exec}.")

        # on met à jour o_stored_data pour avoir son status
        o_stored_data.api_update()
        # Comportement de suppression des entités détectées (il n'est pas possible de supprimer la mise à jour précédente mais on relance la mise à jour)
        if self.__behavior == self.BEHAVIOR_DELETE or (d_data_pe["status"] in [ProcessingExecution.STATUS_FAILURE, ProcessingExecution.STATUS_ABORTED] and self.__behavior == self.BEHAVIOR_RESUME):
            Config().om.warning(f"Le traitement a déjà été lancé sans succès pour cette donnée ({o_proc_exec} statut {d_data_pe['status']}). On relance le traitement.")
            # on force à None pour que la création soit faite
            self.__processing_execution = None
        # Comportement "on continue l'exécution"
        elif self.__behavior in [self.BEHAVIOR_CONTINUE, self.BEHAVIOR_RESUME]:
            # on regarde si le résultat du traitement précédent est en échec (peut-être causé un autre traitement)
            if o_stored_data["status"] == StoredData.STATUS_UNSTABLE:
                raise GpfSdkError(
                    (
                        f"Le traitement précédent a échoué sur la donnée stockée en sortie {o_stored_data}. "
                        "Impossible de lancer le traitement demandé : contactez le support de l'Entrepôt Géoplateforme "
                        "pour faire réinitialiser son statut."
                    )
                )

            # on est donc dans un des cas suivants :
            # la processing_execution a été créé mais pas exécutée (StoredData.STATUS_CREATED)
            # ou la processing_execution est en cours d'exécution (StoredData.STATUS_GENERATING ou StoredData.STATUS_MODIFYING)
            # ou la processing_execution est terminée (StoredData.STATUS_GENERATED)
            self.__stored_data = o_stored_data
            self.__processing_execution = o_proc_exec
            Config().om.info(f"La donnée stockée en sortie {o_stored_data} est en cours de mise à jour, on reprend le traitement associé : {self.__processing_execution}.")
            return
        # Comportement non reconnu
        else:
            raise GpfSdkError(f"Le comportement {self.__behavior} n'est pas reconnu ({'|'.join(self.BEHAVIORS)}), l'exécution de traitement n'est pas possible.")

    def __create_processing_execution(self, datastore: Optional[str] = None) -> None:
        """Création du ProcessingExecution sur l'API à partir des paramètres de définition de l'action.
        Récupération des attributs processing_execution et Upload/StoredData.
        """
        d_info: Optional[Dict[str, Any]] = None

        # On regarde si cette Exécution de Traitement implique la création d'une nouvelle entité (Livraison ou Donnée Stockée)
        if self.output_new_entity:
            self.__gestion_new_output(datastore)

        if self.output_update_entity:
            self.__gestion_update_entity(datastore)

        # A ce niveau là, si on a encore self.__processing_execution qui est None, c'est qu'on peut créer l'Exécution de Traitement sans problème
        if self.__processing_execution is None:
            # création de la ProcessingExecution
            self.__processing_execution = ProcessingExecution.api_create(self.definition_dict["body_parameters"], {"datastore": datastore})

        d_data = self.__processing_execution.get_store_properties()

        # récupération des entrées :
        if "upload" in d_data.get("inputs", {}):
            self.__inputs_upload = [Upload.api_get(d_upload["_id"], datastore=datastore) for d_upload in d_data["inputs"]["upload"]]
        if "stored_data" in d_data.get("inputs", {}):
            self.__inputs_stored_data = [StoredData.api_get(d_stored_data["_id"], datastore=datastore) for d_stored_data in d_data["inputs"]["stored_data"]]

        # récupération de la sortie si elle existe
        d_info = d_data.get("output", {"no_output": ""})

        if d_info is None:
            Config().om.debug(self.__processing_execution.to_json(indent=4))
            raise GpfSdkError("Erreur à la création de l'exécution de traitement : impossible de récupérer l'entité en sortie.")

        if "no_output" in d_info:
            Config().om.info("Traitement sans donnée en sortie")
            self.__no_output = True
            return
        # Récupération des entités de l'exécution de traitement
        if "upload" in d_info:
            # récupération de l'upload
            self.__upload = Upload.api_get(d_info["upload"]["_id"], datastore=datastore)
            return
        if "stored_data" in d_info:
            # récupération de la stored_data
            self.__stored_data = StoredData.api_get(d_info["stored_data"]["_id"], datastore=datastore)
            return
        raise StepActionError(f"Aucune correspondance pour {d_info.keys()}")

    def __add_tags(self) -> None:
        """Ajout des tags sur l'Upload ou la StoredData en sortie du ProcessingExecution."""
        d_tags = self.definition_dict.get("tags", {})
        # gestion des tags pour compatibility_cartes
        if self.__mode_cartes and self.__processing_execution:
            s_processing_id = self.__processing_execution.get_store_properties().get("processing", {"_id": ""})["_id"]
            # mise en base de donnée livrée (vecteur)
            if s_processing_id == Config().get_str("compatibility_cartes", "id_mise_en_base"):
                if "datasheet_name" not in d_tags:
                    raise GpfSdkError("Mode compatibility_cartes activé, il faut obligatoirement définir le tag 'datasheet_name'")
                if not self.__inputs_upload or not self.stored_data:
                    raise GpfSdkError("Intégration de données vecteur livrées en base : input and output obligatoires")
                for o_upload in self.__inputs_upload:
                    # ajout des tags "mode cartes" permettant d'identifier le traitement et la donnée stockée liés à la livraison
                    o_upload.api_add_tags({"proc_int_id": self.__processing_execution.id, "vectordb_id": self.stored_data.id})
                    # ajout des tags "mode cartes" permettant de suivre l'étape du traitement
                    UploadAction.add_carte_tags(self.__mode_cartes, o_upload, "execution_start")
                d_tags["uuid_upload"] = self.__inputs_upload[0].id
            # création de pyramide vecteur
            elif s_processing_id == Config().get_str("compatibility_cartes", "id_pyramide_vecteur"):
                if "datasheet_name" not in d_tags:
                    raise GpfSdkError("Mode compatibility_cartes activé, il faut obligatoirement définir le tag 'datasheet_name'")
                if not self.__inputs_stored_data or not self.stored_data:
                    raise GpfSdkError("Création de pyramide vecteur : input and output obligatoires")
                d_tags["vectordb_id"] = self.__inputs_stored_data[0].id
                d_tags["proc_pyr_creat_id"] = self.__processing_execution.id

        if not self.definition_dict.get("tags") or self.__no_output:
            # cas on a pas de tag ou pas de donnée en sortie: on ne fait rien
            return
        # on ajoute les tags
        if self.upload is not None:
            Config().om.info(f"Livraison {self.upload['name']} : ajout des {len(self.definition_dict['tags'])} tags...")
            self.upload.api_add_tags(d_tags)
            Config().om.info(f"Livraison {self.upload['name']} : les {len(self.definition_dict['tags'])} tags ont été ajoutés avec succès.")
        elif self.stored_data is not None:
            Config().om.info(f"Donnée stockée {self.stored_data['name']} : ajout des {len(self.definition_dict['tags'])} tags...")
            self.stored_data.api_add_tags(d_tags)
            Config().om.info(f"Donnée stockée {self.stored_data['name']} : les {len(self.definition_dict['tags'])} tags ont été ajoutés avec succès.")
        else:
            # on a pas de stored_data ni de upload
            raise StepActionError("ni upload ni stored-data trouvé. Impossible d'ajouter les tags")

    def __add_comments(self) -> None:
        """Ajout des commentaires sur l'Upload ou la StoredData en sortie du ProcessingExecution."""
        if "comments" not in self.definition_dict or self.__no_output:
            # cas on a pas de commentaires : on ne fait rien
            return
        # on ajoute les commentaires
        i_nb_ajout = 0
        if self.upload is not None:
            o_data: Union[StoredData, Upload] = self.upload
            s_type = "Livraison"
        elif self.stored_data is not None:
            o_data = self.stored_data
            s_type = "Donnée stockée"
        else:
            # on a pas de stored_data ni de upload
            raise StepActionError("ni upload ni stored-data trouvé. Impossible d'ajouter les commentaires")

        Config().om.info(f"{s_type} {o_data['name']} : ajout des {len(self.definition_dict['comments'])} commentaires...")
        l_actual_comments = [d_comment["text"] for d_comment in o_data.api_list_comments() if d_comment]
        for s_comment in self.definition_dict["comments"]:
            if s_comment not in l_actual_comments:
                o_data.api_add_comment({"text": s_comment})
                i_nb_ajout += 1
        Config().om.info(f"{s_type} {o_data['name']} : {i_nb_ajout} commentaires ont été ajoutés.")

    def __launch(self) -> None:
        """Lancement de la ProcessingExecution."""
        if self.processing_execution is None:
            raise StepActionError("Aucune exécution de traitement trouvée. Impossible de lancer le traitement")

        if self.processing_execution["status"] == ProcessingExecution.STATUS_CREATED:
            Config().om.info(f"Exécution de traitement {self.processing_execution['processing']['name']} : lancement...", force_flush=True)
            self.processing_execution.api_launch()
            Config().om.info(f"Exécution de traitement {self.processing_execution['processing']['name']} : lancée avec succès.", force_flush=True)
        elif self.__behavior in [self.BEHAVIOR_CONTINUE, self.BEHAVIOR_RESUME]:
            Config().om.info(f"Exécution de traitement {self.processing_execution['processing']['name']} : déjà lancée.", force_flush=True)
        else:
            # processing_execution est déjà lancé ET le __behavior n'est pas en "continue", on ne devrait pas être ici :
            raise StepActionError("L'exécution de traitement est déjà lancée.")

    def find_stored_data(self, datastore: Optional[str] = None) -> Optional[StoredData]:
        """Fonction permettant de récupérer une Stored Data ressemblant à celle qui devrait être créée par
        l'exécution de traitement en fonction des filtres définis dans la Config.

        Returns:
            donnée stockée retrouvée
        """
        # Récupération des critères de filtre
        d_infos, d_tags = ActionAbstract.get_filters("processing_execution", self.definition_dict["body_parameters"]["output"]["stored_data"], self.definition_dict.get("tags", {}))
        # On peut maintenant filtrer les stored data selon ces critères
        l_stored_data = StoredData.api_list(infos_filter=d_infos, tags_filter=d_tags, datastore=datastore)
        # S'il y a un ou plusieurs stored data, on retourne le 1er :
        if l_stored_data:
            return l_stored_data[0]
        # sinon on retourne None
        return None

    def monitoring_until_end(self, callback: Optional[Callable[[ProcessingExecution], None]] = None, ctrl_c_action: Optional[Callable[[], bool]] = None) -> str:
        """Attend que la ProcessingExecution soit terminée (statut `SUCCESS`, `FAILURE` ou `ABORTED`) avant de rendre la main.

        La fonction callback indiquée est exécutée après **chaque vérification du statut** en lui passant en paramètre
        la processing execution (callback(self.processing_execution)).

        Si l'utilisateur stoppe le programme (par ctrl-C), le devenir de la ProcessingExecutionAction sera géré par la callback ctrl_c_action().

        Args:
            callback (Optional[Callable[[ProcessingExecution], None]], optional): fonction de callback à exécuter. Prend en argument le traitement (callback(processing-execution)).
            ctrl_c_action (Optional[Callable[[], bool]], optional): fonction de gestion du ctrl-C. Renvoie True si on doit stopper le traitement.

        Returns:
            str: statut final de l'exécution du traitement
        """

        def callback_not_null(o_pe: ProcessingExecution) -> None:
            """fonction pour éviter des if à chaque appel

            Args:
                o_pe (ProcessingExecution): traitement en cours
            """
            if callback is not None:
                callback(o_pe)

        # NOTE :  Ne pas utiliser self.__processing_execution mais self.processing_execution pour faciliter les tests
        i_nb_sec_between_check = Config().get_int("processing_execution", "nb_sec_between_check_updates")
        Config().om.info(f"Monitoring du traitement toutes les {i_nb_sec_between_check} secondes...", force_flush=True)
        if self.processing_execution is None:
            raise StepActionError("Aucune processing-execution trouvée. Impossible de suivre le déroulement du traitement")

        self.processing_execution.api_update()
        s_status = self.processing_execution.get_store_properties()["status"]
        while s_status not in [ProcessingExecution.STATUS_ABORTED, ProcessingExecution.STATUS_SUCCESS, ProcessingExecution.STATUS_FAILURE]:
            try:
                # appel de la fonction affichant les logs
                callback_not_null(self.processing_execution)

                # On attend le temps demandé
                time.sleep(i_nb_sec_between_check)

                # On met à jour __processing_execution + valeur status
                self.processing_execution.api_update()
                s_status = self.processing_execution.get_store_properties()["status"]

            except KeyboardInterrupt:
                # on appelle la callback de gestion du ctrl-C
                if ctrl_c_action is None or ctrl_c_action():
                    # on doit arrêter le traitement (maj + action spécifique selon le statut)

                    # mise à jour du traitement
                    self.processing_execution.api_update()

                    # si le traitement est déjà dans un statut terminé, on ne fait rien => transmission de l'interruption
                    s_status = self.processing_execution.get_store_properties()["status"]

                    # si le traitement est terminé, on fait un dernier affichage :
                    if s_status in [ProcessingExecution.STATUS_ABORTED, ProcessingExecution.STATUS_SUCCESS, ProcessingExecution.STATUS_FAILURE]:
                        callback_not_null(self.processing_execution)
                        Config().om.warning("traitement déjà terminé.")
                        raise

                    # arrêt du traitement
                    Config().om.warning("Ctrl+C : traitement en cours d’interruption, veuillez attendre...", force_flush=True)
                    self.processing_execution.api_abort()
                    # attente que le traitement passe dans un statut terminé
                    self.processing_execution.api_update()
                    s_status = self.processing_execution.get_store_properties()["status"]
                    while s_status not in [ProcessingExecution.STATUS_ABORTED, ProcessingExecution.STATUS_SUCCESS, ProcessingExecution.STATUS_FAILURE]:
                        # On attend 2s
                        time.sleep(2)
                        # On met à jour __processing_execution + valeur status
                        self.processing_execution.api_update()
                        s_status = self.processing_execution.get_store_properties()["status"]
                    # traitement terminé. On fait un dernier affichage :
                    callback_not_null(self.processing_execution)

                    # si statut Aborted :
                    # suppression de l'upload ou de la stored data en sortie
                    if s_status == ProcessingExecution.STATUS_ABORTED and self.output_new_entity:
                        if self.upload is not None:
                            Config().om.warning("Suppression de l'upload en cours de remplissage suite à l’interruption du programme")
                            self.upload.api_delete()
                        elif self.stored_data is not None:
                            Config().om.warning("Suppression de la stored-data en cours de remplissage suite à l'interruption du programme")
                            self.stored_data.api_delete()
                    # enfin, transmission de l'interruption
                    raise

        # Si on est sorti du while c'est que la processing execution est terminée
        ## dernier affichage
        callback_not_null(self.processing_execution)

        # gestion du mode cartes
        if self.__mode_cartes and self.processing_execution.id == Config().get_str("compatibility_cartes", "id_mise_en_base"):
            if not self.__inputs_upload:
                raise GpfSdkError("Intégration de données vecteur livrées en base : input and output obligatoires")
            s_key = "execution_end_ok_integration_progress" if s_status == ProcessingExecution.STATUS_SUCCESS else "execution_end_ko_integration_progress"
            for o_upload in self.__inputs_upload:
                o_upload.api_add_tags({"integration_progress": Config().get_str("compatibility_cartes", s_key)})

        ## on return le status de fin
        return str(s_status)

    @property
    def processing_execution(self) -> Optional[ProcessingExecution]:
        return self.__processing_execution

    @property
    def upload(self) -> Optional[Upload]:
        return self.__upload

    @property
    def stored_data(self) -> Optional[StoredData]:
        return self.__stored_data

    @property
    def no_output(self) -> bool:
        return self.__no_output

    @property
    def inputs_stored_data(self) -> Optional[List[StoredData]]:
        return self.__inputs_stored_data

    @property
    def inputs_upload(self) -> Optional[List[Upload]]:
        return self.__inputs_upload

    @property
    def output_new_entity(self) -> bool:
        """Indique s'il y aura création d'une nouvelle entité par rapport au paramètre de création de l'exécution de traitement
        (la clé "name" et non la clé "_id" est présente dans le paramètre "output" du corps de requête).
        """
        d_output = self.definition_dict["body_parameters"].get("output", {})
        if "upload" in d_output:
            d_el = d_output["upload"]
        elif "stored_data" in d_output:
            d_el = d_output["stored_data"]
        else:
            return False
        return "name" in d_el

    @property
    def output_update_entity(self) -> bool:
        """Indique s'il y aura mise à jour d'une entité par rapport au paramètre de création de l'exécution de traitement
        (la clé "_id" et non la clé "name" est présente dans le paramètre "output" du corps de requête).
        """
        d_output = self.definition_dict["body_parameters"].get("output", {})
        if "upload" in d_output:
            d_el = d_output["upload"]
        elif "stored_data" in d_output:
            d_el = d_output["stored_data"]
        else:
            return False
        return "_id" in d_el

    ##############################################################
    # Fonctions de représentation
    ##############################################################
    def __str__(self) -> str:
        # Affichage à destination d'un utilisateur.
        # On affiche l'id et le nom si possible.

        # Liste pour stocker les infos à afficher
        l_infos = []
        # Ajout de l'id
        l_infos.append(f"workflow={self.workflow_context}")
        if self.processing_execution:
            l_infos.append(f"processing_execution={self.processing_execution.id}")
        return f"{self.__class__.__name__}({', '.join(l_infos)})"
