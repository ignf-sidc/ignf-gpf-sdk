from pathlib import Path
import shutil
from typing import List, Optional

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.io.Config import Config


class Example:
    """Classe pour récupérer des exemples via l'utilisation cli."""

    TYPES = [
        "dataset",
        "workflow",
        # "delivery", TODO
    ]

    def __init__(self, example_type: str, example_name: Optional[str], output_path: Optional[Path]) -> None:
        """Si un id est précisé, on récupère l'entité et on fait d'éventuelles actions.
        Sinon on liste les entités avec éventuellement des filtres.

        Args:
            example_type (str): type d'exemple à gérer
            example_name (Optional[str]): nom de l'exemple à récupérer
            output_path (Optional[Path]): chemin de sortie, sinon '.'
        """

        self.type = example_type
        self.name = example_name
        self.output_path = output_path or Path(".")

        if self.type == "dataset":
            self.dataset()
        if self.type == "workflow":
            self.workflow()
        if self.type == "delivery":
            self.delivery()

    def dataset(self) -> None:
        """Liste les datasets disponibles ou récupère le dataset demandé.

        Raises:
            GpfSdkError: levée si le dataset demandé n'existe pas.
        """
        p_root = Config.data_dir_path / "datasets"
        if self.name is not None:
            print(f"Exportation du jeu de donnée '{self.name }'...")
            p_from = p_root / self.name
            if p_from.exists():
                p_output = self.output_path / self.name
                if p_output.exists():
                    p_output = p_output / self.name
                print(f"Chemin de sortie : {p_output}")
                # Copie du répertoire
                shutil.copytree(p_from, p_output)
                print("Exportation terminée.")
            else:
                raise GpfSdkError(f"Jeu de données '{self.name}' introuvable.")
        else:
            l_children: List[str] = []
            for p_child in p_root.iterdir():
                if p_child.is_dir():
                    l_children.append(p_child.name)
            print("Jeux de données disponibles :\n   * {}".format("\n   * ".join(l_children)))

    def workflow(self) -> None:
        """Liste les workflows disponibles ou récupère le workflow demandé.

        Raises:
            GpfSdkError: levée si le workflow demandé n'existe pas.
        """
        p_root = Config.data_dir_path / "workflows"
        # Si demandé, on exporte un workflow d'exemple
        if self.name is not None:
            s_name = self.name if self.name.endswith(".jsonc") else f"{self.name}.jsonc"
            print(f"Exportation du workflow '{s_name}'...")
            p_from = p_root / s_name
            if p_from.exists():
                # Si le chemin existe et est un dossier
                if self.output_path.exists() and self.output_path.is_dir():
                    # On écrit le fichier dedans, nommé comme le workflow
                    p_output = self.output_path / s_name
                else:
                    # Sinon on prend directement le chemin
                    p_output = self.output_path
                print(f"Chemin de sortie : {p_output}")
                # Copie du répertoire
                shutil.copyfile(p_from, p_output)
                print("Exportation terminée.")
            else:
                raise GpfSdkError(f"Workflow '{s_name}' introuvable.")
        else:
            l_children: List[str] = []
            for p_child in p_root.iterdir():
                if p_child.is_file():
                    l_children.append(p_child.name)
            print("Workflows disponibles :\n   * {}".format("\n   * ".join(l_children)))

    def delivery(self) -> None:
        pass
