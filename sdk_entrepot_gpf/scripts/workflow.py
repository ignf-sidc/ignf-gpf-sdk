import argparse
from pathlib import Path
from typing import Optional

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper
from sdk_entrepot_gpf.helper.PrintLogHelper import PrintLogHelper
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.scripts.utils import Utils
from sdk_entrepot_gpf.workflow.Workflow import Workflow
from sdk_entrepot_gpf.workflow.resolver.DateResolver import DateResolver
from sdk_entrepot_gpf.workflow.resolver.DictResolver import DictResolver
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver
from sdk_entrepot_gpf.workflow.resolver.StoreEntityResolver import StoreEntityResolver
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.workflow.resolver.UserResolver import UserResolver


class WorkflowCli:
    """Classe pour lancer les workflows via le cli."""

    def __init__(self, datastore: Optional[str], file: Optional[Path], behavior: str, args: argparse.Namespace) -> None:
        """Si un id est précisé, on récupère l'entité et on fait d'éventuelles actions.
        Sinon on liste les entités avec éventuellement des filtres.

        Args:
            datastore (Optional[str], optional): datastore à considérer
            file (Optional[Path]): chemin du fichier descriptif à traiter
            behavior (str): comportement de gestion des conflits
            args (argparse.Namespace): reste des paramètres
        """
        self.datastore = datastore
        self.file = file
        self.behavior = behavior
        self.args = args

        # Ouverture du fichier
        p_workflow = Path(self.args.file).absolute()
        Config().om.info(f"Ouverture du workflow {p_workflow}...")
        self.workflow = Workflow(p_workflow.stem, JsonHelper.load(p_workflow))

        # Y'a-t-il une étape d'indiquée
        if self.args.step is None:
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
        # On définit des résolveurs
        GlobalResolver().add_resolver(StoreEntityResolver("store_entity"))
        GlobalResolver().add_resolver(UserResolver("user"))
        GlobalResolver().add_resolver(DateResolver("datetime"))
        # Résolveur params qui permet d'accéder aux paramètres supplémentaires passés par l'utilisateur
        GlobalResolver().add_resolver(DictResolver("params", {x[0]: x[1] for x in self.args.params}))

        # le comportement
        s_behavior = str(self.args.behavior).upper() if self.args.behavior is not None else None
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
        d_tags = {l_el[0]: l_el[1] for l_el in self.args.tag}
        self.workflow.run_step(
            self.args.step,
            callback_run_step,
            Utils.ctrl_c_action,
            behavior=s_behavior,
            datastore=self.datastore,
            comments=self.args.comment,
            tags=d_tags,
        )
