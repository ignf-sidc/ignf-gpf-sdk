from typing import Optional

from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.Key import Key
from sdk_entrepot_gpf.store.Permission import Permission
from sdk_entrepot_gpf.store.interface.CommentInterface import CommentInterface
from sdk_entrepot_gpf.store.interface.TagInterface import TagInterface
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf import store
from sdk_entrepot_gpf.workflow.Errors import StepActionError


class EditAction(ActionAbstract):
    """Classe dédiée à la Mise à jour des entités.

    Attributes:
        __workflow_context (str): nom du contexte du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
    """

    UPDATABLE_TYPES = [
        Upload.entity_name(),
        StoredData.entity_name(),
        Configuration.entity_name(),
        Offering.entity_name(),
        Key.entity_name(),
        Permission.entity_name(),
    ]

    def run(self, datastore: Optional[str] = None) -> None:
        Config().om.info("Edition ...")
        if "entity_type" not in self.definition_dict:
            raise StepActionError('La clef "entity_type" est obligatoire pour cette action')
        if self.definition_dict["entity_type"] not in EditAction.UPDATABLE_TYPES:
            raise StepActionError(f"Type {self.definition_dict['entity_type']} non reconnu. Types valides : {', '.join(EditAction.UPDATABLE_TYPES)}")
        if not self.definition_dict.get("entity_id"):
            raise StepActionError('La clef "entity_id" est obligatoire pour cette action.')
        o_entity: StoreEntity = store.TYPE__ENTITY[self.definition_dict["entity_type"]].api_get(self.definition_dict["entity_id"], datastore=datastore)

        Config().om.info(f"Edition de {o_entity}.")

        # Lancement de la mise à jour si demandé
        if self.definition_dict.get("body_parameters"):
            o_entity.edit(self.definition_dict["body_parameters"])
            Config().om.info(f"Mise à jour de {o_entity} .")

        # ajout des tags si possible
        if self.definition_dict.get("tags") and isinstance(o_entity, TagInterface):
            Config().om.info(f"ajout des {len(self.definition_dict['tags'])} tags...")
            o_entity.api_add_tags(self.definition_dict["tags"])
            Config().om.info(f"les {len(self.definition_dict['tags'])} tags ont été ajoutés avec succès.")
        # ajout des commentaires si possible
        if self.definition_dict.get("comments") and isinstance(o_entity, CommentInterface):
            l_actual_comments = [d_comment["text"] for d_comment in o_entity.api_list_comments() if d_comment]
            Config().om.info(f"Ajout des {len(self.definition_dict['comments'])} commentaires...")
            for s_comment in self.definition_dict["comments"]:
                # si le commentaire n'existe pas déjà on l'ajoute
                if s_comment not in l_actual_comments:
                    o_entity.api_add_comment({"text": s_comment})
            Config().om.info(f"Les {len(self.definition_dict['comments'])} commentaires ont été ajoutés avec succès.")
        Config().om.info("Edition : terminé")
