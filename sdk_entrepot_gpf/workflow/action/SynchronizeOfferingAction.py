import time
from typing import List, Optional

from sdk_entrepot_gpf.io.Errors import ConflictError, NotFoundError
from sdk_entrepot_gpf.store.Configuration import Configuration
from sdk_entrepot_gpf.store.Offering import Offering
from sdk_entrepot_gpf.workflow.Errors import StepActionError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract
from sdk_entrepot_gpf.io.Config import Config


class SynchronizeOfferingAction(ActionAbstract):
    """Classe dédiée à la synchronization des Offering.

    Attributes:
        __workflow_context (str): nom du contexte du workflow
        __definition_dict (Dict[str, Any]): définition de l'action
        __parent_action (Optional["Action"]): action parente
    """

    def _find_offerings(self, datastore: Optional[str] = None) -> List[Offering]:
        """Recherche de la liste des offerings à traiter

        Args:
            datastore (Optional[str], optional): Datastore à utiliser. Defaults to None.

        Raises:
            StepActionError: Impossible de trouver l'offre (uniquement avec "entity_id")
            StepActionError: Action mal paramétrée : il faut obligatoirement "entity_id" ou "filter_infos"

        Returns:
            List[Offering]: Liste des offres à synchroniser
        """
        l_offering = []
        if self.definition_dict.get("entity_id"):
            ## si id => on recherche directement
            try:
                l_offering.append(Offering.api_get(self.definition_dict["entity_id"], datastore=datastore))
            except NotFoundError as e:
                raise StepActionError(f"Impossible de trouver l'offre : {self.definition_dict['entity_id']}.") from e
        elif "filter_infos" in self.definition_dict:
            d_filter_infos = self.definition_dict["filter_infos"]
            ## par liste des éléments
            ####################################################################################################################
            # solution temporaire en attendant que la liste des offres permette le filtrage que les configurations
            if "configuration" in d_filter_infos:
                # si on a configuration on recherche la configuration puis les filtres sur les offres lé à la configuration
                o_config = Configuration.api_get(d_filter_infos["configuration"], datastore=datastore)
                # trie selon les autre filtre possibles
                l_stored_data = [d_data["stored_data"] for d_data in o_config["type_infos"]["used_data"]]
                if d_filter_infos.get("stored_data", l_stored_data[0]) in l_stored_data:
                    l_config_offering = o_config.api_list_offerings()
                    for o_offering in l_config_offering:
                        o_offering.api_update()
                        if (
                            d_filter_infos.get("type", o_offering["type"]) == o_offering["type"]
                            and d_filter_infos.get("endpoint", o_offering["endpoint"]["_id"]) == o_offering["endpoint"]["_id"]
                            and d_filter_infos.get("status", o_offering["status"]) == o_offering["status"]
                        ):
                            l_offering.append(o_offering)

            ####################################################################################################################
            else:
                l_offering = Offering.api_list(d_filter_infos, datastore=datastore)
        else:
            raise StepActionError('Il faut L\'une des clefs suivantes : "entity_id" ou "filter_infos" pour cette action.')
        return l_offering

    def run(self, datastore: Optional[str] = None) -> None:
        """lancement de la synchronization des Offering.

        Args:
            datastore (Optional[str], optional): surcharge du datastore, sinon utilisation de celui par défaut. Defaults to None.

        Raises:
            StepActionError: Aucune offre trouvée pour la synchronisation
            StepActionError: Plusieurs offres trouvées pour la synchronisation (uniquement si "if_multi" == "error")
            StepActionError: La synchronisation d'au moins une offre est terminée en erreur
        """
        Config().om.info("Synchronisation d'offres ...")
        # récupération des offres
        l_offering = self._find_offerings(datastore)
        # gestion des cas particuliers
        if len(l_offering) == 0:
            raise StepActionError("Aucune offre trouvée pour la synchronisation")
        if len(l_offering) > 1:
            if self.definition_dict.get("if_multi") == "error":
                # On sort en erreur
                raise StepActionError(f"Plusieurs offres trouvées pour la synchronisation : {l_offering}")
            if self.definition_dict.get("if_multi") == "first":
                # on ne synchronise que le 1er élément trouvé
                l_offering = [l_offering[0]]
            # sinon  on les synchronise tous

        l_errors: List[str] = []
        # lancement de la synchronise des offering
        Config().om.info(f"Synchronisation de {len(l_offering)} offres :\n * " + "\n * ".join([str(o_offering) for o_offering in l_offering]))
        # on copie l_offering car on va enlever de la liste des offering si on a un problème
        for o_offering in [*l_offering]:
            try:
                # synchronisation (l'offre met du temps à synchroniser donc on lance tout puis on fera le suivi)
                o_offering.api_synchronize()
            except NotFoundError as e:
                s_message = f"Impossible de trouver l'offre {o_offering}. A-elle été supprimée ?"
                Config().om.error(s_message)
                Config().om.debug(str(e))
                l_errors.append(s_message)
                l_offering.remove(o_offering)
                print("-" * 500)
            except ConflictError as e:
                s_message = f"Problème lors de la synchronisation de {o_offering} : {e.message}"
                Config().om.error(s_message)
                Config().om.debug(str(e))
                l_errors.append(s_message)
                l_offering.remove(o_offering)

        # puis affichage et attente de la fin de la synchronisation
        for o_offering in l_offering:
            ## Récupération des liens
            Config().om.info(f"Offre synchronisée : {o_offering}\n   - " + "\n   - ".join(o_offering.get_url()), green_colored=True)
            ## vérification du status.
            Config().om.info("vérification du statut ...")
            while True:
                o_offering.api_update()
                s_status = o_offering["status"]
                if s_status == Offering.STATUS_PUBLISHED:
                    Config().om.info(f"Synchronisation de {o_offering} : terminé")
                    break
                if s_status == Offering.STATUS_UNSTABLE:
                    Config().om.error(f"Synchronisation de {o_offering} : terminé en erreur.")
                    l_errors.append(f"Synchronisation de {o_offering} : terminé en erreur.")
                    break
                # on fixe à 1 seconde, normalement quasiment instantané
                Config().om.debug(f"Status : '{s_status}', on attend ...")
                time.sleep(1)
        if l_errors:
            raise StepActionError("La synchronisation d'au moins une offre est terminée en erreur \n * " + "\n * ".join(l_errors))
        Config().om.info("Synchronisation d'offres : terminé")
