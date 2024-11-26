import re
import json
from pathlib import Path
from typing import Any

from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.resolver.AbstractResolver import AbstractResolver
from sdk_entrepot_gpf.workflow.resolver.Errors import ResolveFileInvalidError, ResolveFileNotFoundError, ResolverError


class FileResolver(AbstractResolver):
    """Classe permettant de résoudre des paramètres faisant référence à des fichiers : ce résolveur
    permet d'insérer le contenu d'un fichier au moment de la résolution.

    Ce fichier peut être un fichier texte basique, une liste au format JSON ou un dictionnaire au format JSON.


    **Fichier texte :** (dans cet exemple, `file` est le nom du résolveur)

    Contenu du fichier `exemple.txt` :

    ```txt
    coucou
    ```

    Chaîne à remplacer : `Je veux dire : {file.str(exemple.txt)}`

    Résultat : `Je veux dire : coucou`


    **Fichier de liste :** (dans cet exemple, `file` est le nom du résolveur)

    Contenu du fichier `list.json` :

    ```json
    ["valeur 1", "valeur 2"]
    ```

    Chaîne à remplacer : `{"values": ["file","list(list.json)"]}`

    Résultat : `{"values": ["valeur 1", "valeur 2"]}`


    **Fichier de clé-valeur :** (dans cet exemple, `file` est le nom du résolveur)

    Contenu du fichier `dict.json` :

    ```json
    {"k1":"v1", "k2":"v2"}
    ```

    Chaîne à remplacer : `{"parameters": {"file":"dict(dict.json)"}}`

    Résultat : `{"parameters": {"k1":"v1", "k2":"v2"}}`


    Attributes:
        __name (str): nom de code du resolver
    """

    _file_regex = re.compile(Config().get_str("workflow_resolution_regex", "file_regex"))

    def __init__(self, name: str, root_path: Path) -> None:
        """À l'instanciation, il faut indiquer au résolveur le chemin racine d'où chercher les fichiers.

        Args:
            name (str): nom du résolveur
            root_path (Path): chemin racine
        """
        super().__init__(name)
        self.__root_path = root_path.absolute()

    def __resolve_str(self, string_to_solve: str, s_path: str) -> str:
        """fonction privée qui se charge d'extraire une string d'un fichier texte
           on valide que le contenu est bien un texte

        Args:
            string_to_solve (str): chaîne à résoudre
            s_path (str): string du path du fichier à ouvrir

        Returns:
            texte contenu dans le fichier
        """
        p_path_text = self.__root_path / s_path
        if p_path_text.exists():
            s_result = str(p_path_text.read_text(encoding="UTF-8").rstrip("\n"))
        else:
            raise ResolveFileNotFoundError(self.name, string_to_solve, p_path_text)
        return s_result

    def __resolve_list(self, string_to_solve: str, s_path: str) -> str:
        """fonction privée qui se charge d'extraire une string d'un fichier contenant une liste
           on valide que le contenu est bien une liste

        Args:
            string_to_solve (str): chaîne à résoudre
            s_path (str): string du path du fichier à ouvrir

        Returns:
            liste contenue dans le fichier
        """
        s_data = self.__resolve_str(string_to_solve, s_path)
        # on vérifie que cela est bien une liste
        try:
            l_to_solve = json.loads(s_data)  # json.loads ok car on veut récupérer l'erreur
        except json.decoder.JSONDecodeError as e_not_list:
            raise ResolveFileInvalidError(self.name, string_to_solve) from e_not_list

        if not isinstance(l_to_solve, list):
            raise ResolveFileInvalidError(self.name, string_to_solve)

        return s_data

    def __resolve_dict(self, string_to_solve: str, s_path: str) -> str:
        """fonction privée qui se charge d'extraire une string d'un fichier contenant un dictionnaire
           on valide que le contenu est bien un dictionnaire

        Args:
            string_to_solve (str): chaîne à résoudre
            s_path (str): string du path du fichier à ouvrir

        Returns:
            dictionnaire contenu dans le fichier
        """
        s_data = self.__resolve_str(string_to_solve, s_path)
        # on vérifie que cela est bien un dictionnaire
        try:
            d_to_solve = json.loads(s_data)  # json.loads ok car on veut récupérer l'erreur
        except json.decoder.JSONDecodeError as e_not_list:
            raise ResolveFileInvalidError(self.name, string_to_solve) from e_not_list

        if not isinstance(d_to_solve, dict):
            # le programme émet une erreur
            raise ResolveFileInvalidError(self.name, string_to_solve)
        return s_data

    def resolve(self, string_to_solve: str, **kwargs: Any) -> str:
        """Fonction permettant de renvoyer sous forme de string la résolution
        des paramètres de fichier passés en entrée.

        Args:
            string_to_solve (str): chaîne à résoudre (type de fichier à traiter et chemin)
            kwargs (Any): paramètres supplémentaires.

        Raises:
            ResolverError: si la chaîne à résoudre est incorrecte
            ResolverError: si le type de donnée n'est pas str/list/dict

        Returns:
            le contenu du fichier en entrée sous forme de string
        """
        s_result = ""
        # On cherche les résolutions à effectuer
        o_result = FileResolver._file_regex.search(string_to_solve)
        if o_result is None:
            raise ResolverError(self.name, string_to_solve)
        d_groups = o_result.groupdict()
        if d_groups["resolver_type"] == "str":
            s_result = str(self.__resolve_str(string_to_solve, d_groups["resolver_file"]))
        elif d_groups["resolver_type"] == "list":
            s_result = str(self.__resolve_list(string_to_solve, d_groups["resolver_file"]))
        elif d_groups["resolver_type"] == "dict":
            s_result = str(self.__resolve_dict(string_to_solve, d_groups["resolver_file"]))
        else:
            raise ResolverError(self.name, string_to_solve)
        return s_result
