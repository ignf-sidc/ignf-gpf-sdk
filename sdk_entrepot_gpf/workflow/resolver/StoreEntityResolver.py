import json
import re
from typing import Any, Dict, Optional, Pattern, Type

from sdk_entrepot_gpf.workflow.resolver.AbstractResolver import AbstractResolver
from sdk_entrepot_gpf.workflow.resolver.Errors import NoEntityFoundError, ResolverError
from sdk_entrepot_gpf.store.interface.TagInterface import TagInterface
from sdk_entrepot_gpf.store.Processing import Processing
from sdk_entrepot_gpf.store.StoredData import StoredData
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.ProcessingExecution import ProcessingExecution
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.Endpoint import Endpoint
from sdk_entrepot_gpf.store.Static import Static
from sdk_entrepot_gpf.store.Datastore import Datastore
from sdk_entrepot_gpf.io.Config import Config


class StoreEntityResolver(AbstractResolver):
    """Classe permettant de résoudre des paramètres faisant référence à une entité.

    Attributes:
        __name (str): nom de code du resolver
        __regex (Pattern[str]): regex du resolver
    """

    __key_to_cls: Dict[str, Type[StoreEntity]] = {
        Upload.entity_name(): Upload,
        Processing.entity_name(): Processing,
        StoredData.entity_name(): StoredData,
        Configuration.entity_name(): Configuration,
        Offering.entity_name(): Offering,
        ProcessingExecution.entity_name(): ProcessingExecution,
        Endpoint.entity_name(): Endpoint,
        Static.entity_name(): Static,
        Datastore.entity_name(): Datastore,
    }

    def __init__(self, name: str) -> None:
        """À l'instanciation, le résolveur est nommé selon ce qui est indiqué dans la Config.

        Args:
            name (str): nom du résolveur
        """
        super().__init__(name)
        self.__regex: Pattern[str] = re.compile(Config().get_str("workflow_resolution_regex", "store_entity_regex"))

    def resolve(self, string_to_solve: str, **kwargs: Any) -> str:
        """Résolution en listant les entités de l'API.

        Args:
            string_to_solve (str): chaîne à résoudre (type de l'entité, attribut à récupérer)
            kwargs (Any): paramètres supplémentaires (datastore).

        Raises:
            ResolverError: si la chaîne à résoudre n'est pas parsable
            NoEntityFoundError: si aucune entité n'est trouvée
            ResolverError: si aucune information n'est retournée

        Returns:
            l'attribut demandé de l'entité demandée
        """
        # On parse la chaîne à résoudre
        o_result = self.regex.search(string_to_solve)
        if o_result is None:
            raise ResolverError(self.name, string_to_solve)
        d_groups = o_result.groupdict()
        # On récupère les filtres à utiliser
        # Sur les infos
        s_filter_infos: Optional[str] = d_groups["filter_infos"]
        d_filter_infos = StoreEntity.filter_dict_from_str(s_filter_infos)
        # Sur les tags
        s_filter_tags: Optional[str] = d_groups["filter_tags"]
        d_filter_tags = StoreEntity.filter_dict_from_str(s_filter_tags)
        # On récupère le type de StoreEntity demandé
        s_entity_type = str(d_groups["entity_type"])
        # On liste les éléments API via la fonction de classe
        l_entities = self.__key_to_cls[s_entity_type].api_list(
            infos_filter=d_filter_infos,
            tags_filter=d_filter_tags,
            page=1,
            datastore=kwargs.get("datastore"),
        )
        # Si on a aucune entité trouvée
        if len(l_entities) == 0:
            raise NoEntityFoundError(self.name, string_to_solve)
        # Sinon on regarde ce qu'on doit envoyer

        if d_groups["number_dict"] == "ONE":
            # json de la première entité trouvée
            l_entities[0].api_update()
            return l_entities[0].to_json()
        if d_groups["number_dict"] == "ALL":
            # json de toutes les entités trouvées
            l_res1 = []
            for o_entity in l_entities:
                o_entity.api_update()
                l_res1.append(o_entity.get_store_properties())
            return json.dumps(l_res1)
        try:
            if not d_groups["number_selected"] or d_groups["number_selected"] == "ONE":
                # une seule entité à traiter, affichage d'une info ou d'un tag
                return self._get_info_or_tag(l_entities[0], d_groups)
            if d_groups["number_selected"] == "ALL":
                # affichage d'une info ou d'un tag pour toutes les entités trouvées
                l_res2 = [self._get_info_or_tag(o_entity, d_groups) for o_entity in l_entities]
                if d_groups["selected_field_type"] == "tags":
                    l_res2 = list(set(l_res2))
                return json.dumps(l_res2)
        except KeyError as e:
            raise ResolverError(self.name, string_to_solve) from e

        raise ResolverError(self.name, string_to_solve)

    def _get_info_or_tag(self, o_entity: StoreEntity, d_groups: Dict[str, Any]) -> str:
        o_entity.api_update()
        s_selected_field = d_groups["selected_field"]
        # On doit envoyer une info ?
        if d_groups["selected_field_type"] == "infos":
            # On doit renvoyer une info
            return str(self.get(o_entity.get_store_properties(), s_selected_field))
        # On doit renvoyer un tag, possible que si ça implémente TagInterface
        if isinstance(o_entity, TagInterface):
            return o_entity.get_tag(s_selected_field)
        raise KeyError()

    @property
    def regex(self) -> Pattern[str]:
        return self.__regex
