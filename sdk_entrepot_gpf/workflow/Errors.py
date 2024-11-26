from pathlib import Path
from typing import List, Tuple
from sdk_entrepot_gpf.Errors import GpfSdkError


class WorkflowError(GpfSdkError):
    """Classe d'erreur pour le workflow"""


class StepActionError(GpfSdkError):
    """Classe d'erreur pour le workflow"""


class UploadFileError(GpfSdkError):
    """classe d'erreur lors de la livraison de donnée sur le store"""

    def __init__(self, message: str, files: List[Tuple[Path, str]]) -> None:
        super().__init__(message)
        self.files = files
