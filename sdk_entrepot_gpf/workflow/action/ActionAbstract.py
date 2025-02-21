from abc import ABC, abstractmethod
import json
from typing import Any, Dict, Optional, Tuple

from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver
from sdk_entrepot_gpf.io.Config import Config


class ActionAbstract(ABC):
    """Classe abstraite représentant une action d'un workflow.

    Lancer une action revient à créer une entité dans l'API. Par exemple :

    * faire un traitement revient à créer une Exécution de Traitement ;
    * configurer un géoservice revient à créer une Configuration ;
    * publier un géoservice revient à créer une Offre.

    Attributes:
        __workflow_context (str): nom du context du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
    """

    # comportements possibles (que peut écrire l'utilisateur)
    BEHAVIOR_STOP = "STOP"
    BEHAVIOR_DELETE = "DELETE"
    BEHAVIOR_CONTINUE = "CONTINUE"
    BEHAVIOR_RESUME = "RESUME"

    def __init__(self, workflow_context: str, definition_dict: Dict[str, Any], parent_action: Optional["ActionAbstract"] = None) -> None:
        super().__init__()
        self.__workflow_context: str = workflow_context
        self.__definition_dict: Dict[str, Any] = definition_dict
        self.__parent_action: Optional["ActionAbstract"] = parent_action

    @property
    def workflow_context(self) -> str:
        return self.__workflow_context

    @property
    def index(self) -> int:
        """Renvoie l'index de l'action dans la liste des actions de cette étape.
        La première action a le numéro 0.

        Returns:
            index de l'action dans la liste des actions de cette étape
        """
        if self.parent_action is not None:
            return self.parent_action.index + 1
        return 0

    @property
    def definition_dict(self) -> Dict[str, Any]:
        return self.__definition_dict

    @property
    def parent_action(self) -> Optional["ActionAbstract"]:
        return self.__parent_action

    def resolve(self, **kwargs: Any) -> None:
        """Résout la définition de l'action.

        L'action peut faire référence à des entités via des filtres, on
        veut donc résoudre ces éléments afin de soumettre une requête valide à l'API.

        Args:
            kwargs (Any): paramètres supplémentaires.

        Raises:
            StepActionError: _description_
        """
        Config().om.info(f"Résolution de l'action '{self.workflow_context}-{self.index}'...", force_flush=True)
        # Pour faciliter la résolution, on repasse la définition de l'action en json
        s_definition = str(json.dumps(self.__definition_dict, ensure_ascii=False))
        # lancement des résolveurs
        s_resolved_definition = GlobalResolver().resolve(s_definition, **kwargs)
        # on repasse en json
        try:
            self.__definition_dict = json.loads(s_resolved_definition)
            Config().om.info(f"Résolution de l'action '{self.workflow_context}-{self.index}' : terminée")
        except json.decoder.JSONDecodeError as e_json:
            Config().om.debug(f"resolved action: {s_resolved_definition}")
            raise StepActionError(f"Action '{self.workflow_context}-{self.index}' non valide après résolution : {e_json}") from e_json

    @abstractmethod
    def run(self, datastore: Optional[str] = None) -> None:
        """Lancement de l'action.

        Args:
            datastore (Optional[str]): id du datastore à utiliser. Si None, le datastore sera récupéré dans la configuration. Defaults to None.
        """

    @staticmethod
    def get_filters(config_key: str, infos: Dict[str, Any], tags: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Génère les critères de filtres (pour voir si cette action n'a pas déjà été lancée)
        d'après les critères d'unicité et les paramètres de création d'entité.

        Args:
            config_key (str): clé permettant de récupérer les critère d'unicité en config
            infos (Dict[str, Any]): paramètres d'attributs pour la création de l'entité
            tags (Dict[str, Any]): paramètres de tags pour la création de l'entité

        Returns:
            critère de filtres sur les infos et les tags
        """
        # On liste les filtres sur les informations (uniqueness_constraint_infos)
        l_attributes = Config().get_str(config_key, "uniqueness_constraint_infos", "").split(";")
        d_infos = {}
        for s_infos in l_attributes:
            if s_infos != "":
                d_infos[s_infos] = infos.get(s_infos, None)
        # On liste les filtres sur les tags (uniqueness_constraint_tags)
        l_tags = Config().get_str(config_key, "uniqueness_constraint_tags", "").split(";")
        d_tags = {}
        for s_tag in l_tags:
            if s_tag != "" and s_tag in tags:
                d_tags[s_tag] = tags[s_tag]
        # On peut maintenant renvoyer les filtres
        return d_infos, d_tags

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
        return f"{self.__class__.__name__}({', '.join(l_infos)})"

    def __repr__(self) -> str:
        # Affichage à destination d'un développeur.
        # Pour le moment, pas de différence avec __str__
        return str(self)
