import json
from typing import Any, Dict, List
from unittest.mock import patch

from sdk_entrepot_gpf.store.Endpoint import Endpoint
from sdk_entrepot_gpf.store.StoreEntity import StoreEntity
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.store.Datastore import Datastore
from sdk_entrepot_gpf.workflow.resolver.Errors import NoEntityFoundError, ResolverError
from sdk_entrepot_gpf.workflow.resolver.StoreEntityResolver import StoreEntityResolver

from tests.GpfTestCase import GpfTestCase


class StoreEntityResolverTestCase(GpfTestCase):
    """Tests StoreEntityResolver class.

    cmd : python3 -m unittest -b tests.workflow.resolver.StoreEntityResolverTestCase
    """

    def test_resolve_errors(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve si erreurs."""

        o_store_entity_resolver = StoreEntityResolver("store_entity")

        # Si mot clé incorrect erreur levée
        with self.assertRaises(ResolverError) as o_arc_1:
            o_store_entity_resolver.resolve("other()")
        self.assertEqual(o_arc_1.exception.message, "Erreur du résolveur 'store_entity' avec la chaîne 'other()'.")

        # Si mot clé incorrect erreur levée
        with self.assertRaises(ResolverError) as o_arc_2:
            o_store_entity_resolver.resolve("upload.infos._id [IFO(name=titi)]")
        self.assertEqual(o_arc_2.exception.message, "Erreur du résolveur 'store_entity' avec la chaîne 'upload.infos._id [IFO(name=titi)]'.")

        # pas de possibilité de récupérer un tag pour une entité endpoint
        l_endpoints = [Endpoint({"_id": "endpoint", "name": "Name", "type": "ARCHIVE"})]
        o_store_entity_resolver = StoreEntityResolver("store_entity")
        # On mock la fonction api_list, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(Endpoint, "api_list", return_value=l_endpoints) as o_mock_api_list:
            s_to_solve = "endpoint.tags.k_tag [INFOS(type=ARCHIVE)]"
            with self.assertRaises(ResolverError) as o_arc:
                o_store_entity_resolver.resolve("endpoint.tags.k_tag [INFOS(type=ARCHIVE)]")
            # Vérification erreur
            self.assertEqual(o_arc.exception.message, f"Erreur du résolveur 'store_entity' avec la chaîne '{s_to_solve}'.")
            # Vérifications o_mock_api_list
            o_mock_api_list.assert_called_once_with(
                infos_filter={"type": "ARCHIVE"},
                tags_filter={},
                page=1,
                datastore=None,
            )

    def test_resolve_no_result(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve si aucun résultat n'est trouvé."""

        o_store_entity_resolver = StoreEntityResolver("store_entity")
        l_uploads: List[StoreEntity] = []

        # On mock la fonction api_list, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(StoreEntity, "api_list", return_value=l_uploads) as o_mock_api_list:
            s_to_solve = "upload.infos._id [INFOS(name=start_%), TAGS(k_tag=v_tag)]"
            with self.assertRaises(NoEntityFoundError) as o_arc:
                o_store_entity_resolver.resolve(s_to_solve)
            # Vérification erreur
            self.assertEqual(o_arc.exception.message, f"Impossible de trouver une entité correspondante (résolveur 'store_entity') avec la chaîne '{s_to_solve}'.")
            # Vérifications o_mock_api_list
            o_mock_api_list.assert_called_once_with(
                infos_filter={"name": "start_%"},
                tags_filter={"k_tag": "v_tag"},
                page=1,
                datastore=None,
            )

    def test_no_key(self) -> None:
        """vérifie l'erreur retournée quand la clef n'est pas trouvée"""

        o_store_entity_resolver = StoreEntityResolver("store_entity")
        l_uploads = [
            Upload({"_id": "upload_1", "name": "Name 1", "tags": {"k_tag": "v_tag"}}),
            Upload({"_id": "upload_2", "name": "Name 2", "tags": {"k_tag": "v_tag"}}),
        ]

        # TEST 1 : attributs, on tente de récupérer différents attributs du 1er élément

        # On mock la fonction api_list, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(StoreEntity, "api_list", return_value=l_uploads) as o_mock_api_list:
            with patch.object(StoreEntity, "api_update", return_value=None) as o_mock_api_update:
                s_to_solve = "upload.infos.not_in_dict [INFOS(name=start_%), TAGS(k_tag=v_tag)]"
                with self.assertRaises(ResolverError) as o_arc:
                    o_store_entity_resolver.resolve(s_to_solve)
                # message d'erreur :
                self.assertEqual(o_arc.exception.message, f"Erreur du résolveur 'store_entity' avec la chaîne '{s_to_solve}'.")
                # Vérifications o_mock_api_list
                o_mock_api_list.assert_called_once_with(
                    infos_filter={"name": "start_%"},
                    tags_filter={"k_tag": "v_tag"},
                    page=1,
                    datastore=None,
                )
                # Vérification maj entité via appel de api_update
                o_mock_api_update.assert_called_once_with()

    def run_resolve(self, d_param: Dict[str, Any]) -> None:
        """lancement des tests pour resolve() sans erreur

        Args:
            d_param (Dict[str,Any]): dictionnaire
        """
        o_store_entity_resolver = StoreEntityResolver("store_entity")
        # On mock la fonction api_list, on veut vérifier qu'elle est appelée avec les bons param
        with patch.object(d_param["classe"], "api_list", return_value=d_param["return_api_list"]) as o_mock_api_list:
            with patch.object(d_param["classe"], "api_update", return_value=None) as o_mock_api_update:
                s_result = o_store_entity_resolver.resolve(**d_param["expression"])
                # Vérifications o_mock_api_list
                o_mock_api_list.assert_called_once_with(**d_param["data_api_list"])
                # Vérification id récupérée
                self.assertEqual(s_result, d_param["expected_result"])
                # Vérification maj entité via appel de api_update
                self.assertEqual(o_mock_api_update.call_count, d_param.get("nb_api_update", 1))

    def test_resolve_upload(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un upload."""
        l_uploads = [
            Upload({"_id": "upload_1", "name": "Name 1", "tags": {"k_tag": "v_tag"}}),
            Upload({"_id": "upload_2", "name": "Name 2", "tags": {"k_tag": "v_tag"}}),
            Upload({"_id": "upload_2", "name": "Name 2", "tags": {"k_tag": "autre_tag"}}),
        ]

        l_param = [
            # TEST 1 : attributs, on tente de récupérer différents attributs du 1er élément
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "upload.infos._id [INFOS(name=start_%), TAGS(k_tag=v_tag)]"},
                "expected_result": l_uploads[0]["_id"],
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "upload.infos.name [INFOS(name=start_%), TAGS(k_tag=v_tag)]"},
                "expected_result": l_uploads[0]["name"],
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "upload.tags.k_tag [INFOS(name=start_%), TAGS(k_tag=v_tag)]"},
                "expected_result": l_uploads[0]["tags"]["k_tag"],
            },
            # TEST 2 : avec on sens datastore, on vérifie qu'un datastore passé est bien transmis
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": "datastore_1"},
                "expression": {"string_to_solve": "upload.infos._id [INFOS(name=start_%), TAGS(k_tag=v_tag)]", "datastore": "datastore_1"},
                "expected_result": l_uploads[0]["_id"],
            },
            # TEST 3 : utilisation de ONE
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": "datastore_1"},
                "expression": {"string_to_solve": "upload.ONE.infos._id [INFOS(name=start_%), TAGS(k_tag=v_tag)]", "datastore": "datastore_1"},
                "expected_result": l_uploads[0]["_id"],
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "upload.ONE.infos.name [INFOS(name=start_%), TAGS(k_tag=v_tag)]"},
                "expected_result": l_uploads[0]["name"],
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "upload.ONE.tags.k_tag [INFOS(name=start_%), TAGS(k_tag=v_tag)]"},
                "expected_result": l_uploads[0]["tags"]["k_tag"],
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "upload.ONE [INFOS(name=start_%), TAGS(k_tag=v_tag)]"},
                "expected_result": l_uploads[0].to_json(),
            },
            # TEST 4 : utilisation de ALL
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": "datastore_1"},
                "expression": {"string_to_solve": "upload.ALL.infos._id [INFOS(name=start_%), TAGS(k_tag=v_tag)]", "datastore": "datastore_1"},
                "expected_result": json.dumps([o_upload["_id"] for o_upload in l_uploads]),
                "nb_api_update": len(l_uploads),
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": "datastore_1"},
                "expression": {"string_to_solve": "upload.ALL.infos.name [INFOS(name=start_%), TAGS(k_tag=v_tag)]", "datastore": "datastore_1"},
                "expected_result": json.dumps([o_upload["name"] for o_upload in l_uploads]),
                "nb_api_update": len(l_uploads),
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {"k_tag": "v_tag"}, "page": 1, "datastore": "datastore_1"},
                "expression": {"string_to_solve": "upload.ALL [INFOS(name=start_%), TAGS(k_tag=v_tag)]", "datastore": "datastore_1"},
                "expected_result": json.dumps([o_upload.get_store_properties() for o_upload in l_uploads]),
                "nb_api_update": len(l_uploads),
            },
            {
                "classe": Upload,
                "return_api_list": l_uploads,
                "data_api_list": {"infos_filter": {"name": "start_%"}, "tags_filter": {}, "page": 1, "datastore": "datastore_1"},
                "expression": {"string_to_solve": "upload.ALL.tags.k_tag [INFOS(name=start_%)]", "datastore": "datastore_1"},
                "expected_result": json.dumps(list({o_upload["tags"]["k_tag"] for o_upload in l_uploads})),
                "nb_api_update": len(l_uploads),
            },
        ]
        for d_param in l_param:
            self.run_resolve(d_param)

    def test_resolve_endpoint(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un endpoint."""
        l_endpoints = [Endpoint({"_id": "endpoint", "name": "Name", "type": "ARCHIVE"})]
        l_param = [
            # TEST 1 : attributs, on tente de récupérer différents attributs du 1er élément
            {
                "classe": Endpoint,
                "return_api_list": l_endpoints,
                "data_api_list": {"infos_filter": {"type": "ARCHIVE"}, "tags_filter": {}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "endpoint.infos._id [INFOS(type=ARCHIVE)]"},
                "expected_result": l_endpoints[0]["_id"],
            },
            {
                "classe": Endpoint,
                "return_api_list": l_endpoints,
                "data_api_list": {"infos_filter": {"type": "ARCHIVE"}, "tags_filter": {}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "endpoint.infos.name [INFOS(type=ARCHIVE)]"},
                "expected_result": l_endpoints[0]["name"],
            },
        ]
        for d_param in l_param:
            self.run_resolve(d_param)

    def test_resolve_datastore(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un store.
        On peut utiliser `name` pour filter sur le `name` et sur le `technical_name`.
        """
        l_entities = [Datastore({"_id": "1", "name": "Datastore 1", "technical_name": "ds1"})]
        l_param = [
            # TEST 1 : attributs, on tente de récupérer différents attributs du 1er élément
            {
                "classe": Datastore,
                "return_api_list": l_entities,
                "data_api_list": {"infos_filter": {"name": "ds1"}, "tags_filter": {}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "datastore.infos._id [INFOS(name=ds1)]"},
                "expected_result": l_entities[0]["_id"],
            },
            {
                "classe": Datastore,
                "return_api_list": l_entities,
                "data_api_list": {"infos_filter": {"name": "ds1"}, "tags_filter": {}, "page": 1, "datastore": None},
                "expression": {"string_to_solve": "datastore.infos.technical_name [INFOS(name=ds1)]"},
                "expected_result": l_entities[0]["technical_name"],
            },
        ]
        for d_param in l_param:
            self.run_resolve(d_param)
