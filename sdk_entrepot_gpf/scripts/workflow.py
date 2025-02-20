from pathlib import Path
from typing import Dict, List, Optional

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper
from sdk_entrepot_gpf.helper.PrintLogHelper import PrintLogHelper
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.scripts.resolve import ResolveCli
from sdk_entrepot_gpf.scripts.utils import Utils
from sdk_entrepot_gpf.workflow.Workflow import Workflow
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution


class WorkflowCli:
    """Classe pour lancer les workflows via le cli."""

    def __init__(
        self,
        datastore: Optional[str],
        file: Path,
        behavior: str,
        step: Optional[str],
        params: Dict[str, str],
        tags: Dict[str, str],
        comments: List[str],
    ) -> None:
        """Si un id est précisé, on récupère l'entité et on fait d'éventuelles actions.
        Sinon on liste les entités avec éventuellement des filtres.

        Args:
            datastore (Optional[str], optional): datastore à considérer
            file (Path): chemin du fichier descriptif à traiter
            behavior (str): comportement de gestion des conflits
            step (Optional[str]): étape à lancer
            params (Dict[str, str]): paramètres complémentaires
            tags (Dict[str, str]): tags à ajouter
            comments (List[str]): commentaires à ajouter
        """
        self.datastore = datastore
        self.file = file
        self.behavior = behavior
        self.step = step
        self.params = params
        self.tags = tags
        self.comments = comments

        # Ouverture du fichier
        p_workflow = Path(self.file).absolute()
        Config().om.info(f"Ouverture du workflow {p_workflow}...")
        self.workflow = Workflow(p_workflow.stem, JsonHelper.load(p_workflow))

        # Y'a-t-il une étape d'indiquée
        if self.step is None:
            # Si pas d'étape indiquée, on valide le workflow
            Config().om.info("Validation du workflow...")
            self.validate()
        else:
            # Sinon on lance l'étape indiquée
            self.run()

    def validate(self) -> None:
        """Validation du workflow."""
        l_errors = self.workflow.validate()
        if l_errors:
            s_errors = "\n   * ".join(l_errors)
            Config().om.error(f"{len(l_errors)} erreurs ont été trouvées dans le workflow.")
            Config().om.info(f"Liste des erreurs :\n   * {s_errors}")
            raise GpfSdkError("Workflow invalide.")
        Config().om.info("Le workflow est valide.", green_colored=True)

        # Affichage des étapes disponibles et des parents
        Config().om.info("Liste des étapes disponibles et de leurs parents :", green_colored=True)
        l_steps = self.workflow.get_all_steps()
        for s_step in l_steps:
            Config().om.info(f"   * {s_step}")

    def run(self) -> None:
        """Lancement de l'étape indiquée."""
        assert self.step is not None
        # On initialise les résolveurs
        ResolveCli.init_resolvers(self.params)

        # le comportement
        s_behavior = str(self.behavior).upper() if self.behavior is not None else None
        # on reset l'afficheur de log
        PrintLogHelper.reset()

        # et on lance l'étape en précisant l'afficheur de log et le comportement
        def callback_run_step(processing_execution: ProcessingExecution) -> None:
            """fonction callback pour l'affichage des logs lors du suivi d'un traitement

            Args:
                processing_execution (ProcessingExecution): processing exécution en cours
            """
            try:
                PrintLogHelper.print(processing_execution.api_logs())
            except Exception:
                PrintLogHelper.print("Logs indisponibles pour le moment...")

        # on lance le monitoring de l'étape en précisant la gestion du ctrl-C
        self.workflow.run_step(
            self.step,
            callback_run_step,
            Utils.ctrl_c_action,
            behavior=s_behavior,
            datastore=self.datastore,
            comments=self.comments,
            tags=self.tags,
        )
