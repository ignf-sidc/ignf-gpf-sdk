from pathlib import Path

from sdk_entrepot_gpf.Errors import GpfSdkError


class ResolverError(GpfSdkError):
    """Classe d'erreur pour les résolveurs.

    Attributes:
        __message (str): message décrivant le problème
        __resolver_name (str): nom du résolveur
        __to_solve (str): chaîne à résoudre
    """

    def __init__(self, resolver_name: str, to_solve: str, message: str = "") -> None:
        s_message = f"Erreur du résolveur '{resolver_name}' avec la chaîne '{to_solve}'"
        if message:
            s_message += f" : {message}"
        super().__init__(s_message)
        self.__resolver_name = resolver_name
        self.__to_solve = to_solve

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__resolver_name}, {self.__to_solve}, {self.__message})"


class ResolverNotFoundError(GpfSdkError):
    """Classe d'erreur si résolveur non trouvé.

    Attributes:
        __message (str): message décrivant le problème
        __resolver_name (str): nom du résolveur
    """

    def __init__(self, resolver_name: str) -> None:
        s_message = f"Le résolveur '{resolver_name}' demandé est non défini."
        super().__init__(s_message)
        self.__resolver_name = resolver_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__resolver_name})"

    @property
    def resolver_name(self) -> str:
        return self.__resolver_name


class NoEntityFoundError(GpfSdkError):
    """Classe d'erreur pour le résolveur StoreEntityResolver quand aucune entité n'est trouvée.

    Attributes:
        __message (str): message décrivant le problème
        __resolver_name (str): nom du résolveur
        __to_solve (str): chaîne à résoudre
    """

    def __init__(self, resolver_name: str, to_solve: str) -> None:
        s_message = f"Impossible de trouver une entité correspondante (résolveur '{resolver_name}') avec la chaîne '{to_solve}'."
        super().__init__(s_message)
        self.__resolver_name = resolver_name
        self.__to_solve = to_solve

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__resolver_name}, {self.__to_solve})"


class ResolveFileNotFoundError(GpfSdkError):
    """Classe d'erreur pour le résolveur FileResolver quand le fichier indiqué est introuvable.

    Attributes:
        __message (str): message décrivant le problème
        __resolver_name (str): nom du résolveur
        __to_solve (str): chaîne à résoudre
        __absolute_path (Path): chemin vers le fichier non trouvé
    """

    def __init__(self, resolver_name: str, to_solve: str, path: Path) -> None:
        s_message = f"Erreur de traitement d'un fichier (résolveur '{resolver_name}') avec la chaîne '{to_solve}': fichier ({path.absolute()}) non existant."
        super().__init__(s_message)
        self.__resolver_name = resolver_name
        self.__to_solve = to_solve
        self.__absolute_path = path.absolute()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__resolver_name}, {self.__to_solve}, {self.__absolute_path})"


class ResolveFileInvalidError(GpfSdkError):
    """Classe d'erreur pour le résolveur FileResolver quand le fichier indiqué est invalide.

    Attributes:
        __message (str): message décrivant le problème
        __resolver_name (str): nom du résolveur
        __to_solve (str): chaîne à résoudre
    """

    def __init__(self, resolver_name: str, to_solve: str) -> None:
        s_message = f"Erreur de traitement d'un fichier (résolveur '{resolver_name}') avec la chaîne '{to_solve}'."
        super().__init__(s_message)
        self.__resolver_name = resolver_name
        self.__to_solve = to_solve

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__resolver_name}, {self.__to_solve})"


class ResolveUserError(GpfSdkError):
    """Classe d'erreur quand les informations de l'utilisateur ne sont pas récupérées.

    Attributes:
        __message (str): message décrivant le problème
        __resolver_name (str): nom du résolveur
        __to_solve (str): chaîne à résoudre
    """

    def __init__(self, resolver_name: str, to_solve: str) -> None:
        s_message = f"Erreur de récupération des données de l'utilisateur (résolveur '{resolver_name}') avec la chaîne '{to_solve}'."
        super().__init__(s_message)
        self.__to_solve = to_solve
        self.__resolver_name = resolver_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__resolver_name},{self.__to_solve})"
