from typing import List, Optional

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.Permission import Permission
from sdk_entrepot_gpf.store.Key import Key
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.Errors import NotFoundError
from sdk_entrepot_gpf import store
from sdk_entrepot_gpf.workflow.Errors import StepActionError


class DeleteAction(ActionAbstract):
    """Classe dédiée à la suppression des entités.

    Attributes:
        __workflow_context (str): nom du contexte du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
    """

    DELETABLE_TYPES = [
        Upload.entity_name(),
        StoredData.entity_name(),
        Configuration.entity_name(),
        Offering.entity_name(),
        Permission.entity_name(),
        Key.entity_name(),
    ]

    @staticmethod
    def question_before_delete(l_delete: List[StoreEntity]) -> List[StoreEntity]:
        """question posée avant que la suppression soit effectuée

        Args:
            l_delete (List[StoreEntity]): liste des entités à supprimer

        Returns:
            List[StoreEntity]: liste final des entités à supprimer
        """
        Config().om.info("suppression de :")
        for o_entity in l_delete:
            Config().om.info(str(o_entity), green_colored=True)
        Config().om.info("Voulez-vous effectuer la suppression ? (oui/NON)")
        s_rep = input()
        # si la réponse ne correspond pas à oui on sort
        if s_rep.lower() not in ["oui", "o", "yes", "y"]:
            Config().om.info("La suppression est annulée.")
            return []
        return l_delete

    @staticmethod
    def print_before_delete(l_delete: List[StoreEntity]) -> List[StoreEntity]:
        """Affichage avant que la suppression soit effectuée

        Args:
            l_delete (List[StoreEntity]): liste des entités à supprimer

        Returns:
            List[StoreEntity]: liste finale des entités à supprimer
        """
        Config().om.info("suppression de :")
        for o_entity in l_delete:
            Config().om.info(str(o_entity), green_colored=True)
        return l_delete

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Suppression...")
        if "entity_type" not in self.definition_dict:
            raise StepActionError('La clef "entity_type" est obligatoire pour cette action')
        if self.definition_dict["entity_type"] not in DeleteAction.DELETABLE_TYPES:
            raise StepActionError(f"Type {self.definition_dict['entity_type']} non reconnu. Types valides : {', '.join(DeleteAction.DELETABLE_TYPES)}")
        # Recherche de la/ les entité à supprimer
        l_entities = []
        if self.definition_dict.get("entity_id"):
            ## si id => on recherche directement
            try:
                l_entities.append(store.TYPE__ENTITY[self.definition_dict["entity_type"]].api_get(self.definition_dict["entity_id"], datastore=datastore))
            except NotFoundError:
                pass
        elif "filter_infos" in self.definition_dict or "filter_tags" in self.definition_dict:
            ## par liste des éléments
            l_entities = store.TYPE__ENTITY[self.definition_dict["entity_type"]].api_list(self.definition_dict.get("filter_infos"), self.definition_dict.get("filter_tags"), datastore=datastore)
        else:
            raise StepActionError('Il faut au moins une des clefs suivantes : "entity_id", "filter_infos", "filter_tags" pour cette action.')

        if len(l_entities) == 0:
            if not self.definition_dict.get("not_found_ok"):
                raise StepActionError("Aucune entité trouvée pour la suppression")
            # sinon OK
            Config().om.info("Aucune entité à supprimer.", green_colored=True)
            return
        if len(l_entities) > 1 and self.definition_dict.get("if_multi") == "error":
            # On sort en erreur
            raise StepActionError(f"Plusieurs entités trouvées pour la suppression : {l_entities}")
        if len(l_entities) > 1 and self.definition_dict.get("if_multi") == "first":
            # on ne supprime que le 1er élément trouvé
            l_entities = [l_entities[0]]
        # on les supprimera tous

        # récupération des entités en cascades si demandé
        if self.definition_dict.get("cascade", False):
            Config().om.info("Suppression en cascade, recherche des entités à supprimer ...")
            l_entities_cascade = []
            for o_entity in l_entities:
                l_entities_cascade += o_entity.get_liste_deletable_cascade()
            l_entities = l_entities_cascade

        # choix de la fonction d'affichage.
        o_before_delete = self.question_before_delete if self.definition_dict.get("confirm", True) else self.print_before_delete

        # suppression
        StoreEntity.delete_liste_entities(l_entities, o_before_delete)
        Config().om.info("Suppression : terminé")
