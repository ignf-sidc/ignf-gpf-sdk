from typing import Dict, Any
from sdk_entrepot_gpf.helper.DictHelper import DictHelper
from tests.GpfTestCase import GpfTestCase


class DictHelperTestCase(GpfTestCase):
    """Test de la classe DictHelper.

    cmd : python3 -m unittest -b tests.helper.DictHelperTestCase
    """

    def test_get(self) -> None:
        """Vérification du bon fonctionnement de la fonction get."""
        d_dict: Dict[str, Any] = {
            "key1": {
                "key2": {
                    "key3": "value",
                    "list": ["first", "value2", "last"],
                }
            },
            "list": ["first", "value2", "last"],
            "number": 42,
        }
        # Ca fonctionne
        self.assertEqual("value", DictHelper.get(d_dict, "key1.key2.key3"))
        self.assertEqual(d_dict["key1"]["key2"]["list"], DictHelper.get(d_dict, "key1.key2.list"))
        self.assertEqual(d_dict["list"][0], DictHelper.get(d_dict, "list[0]"))
        self.assertEqual(d_dict["list"][1], DictHelper.get(d_dict, "list[1]"))
        self.assertEqual(d_dict["list"][2], DictHelper.get(d_dict, "list[2]"))
        self.assertEqual(d_dict["list"][-1], DictHelper.get(d_dict, "list[-1]"))
        self.assertEqual(d_dict["list"][-2], DictHelper.get(d_dict, "list[-2]"))
        # Erreur levée si non existant par défaut
        with self.assertRaises(KeyError):
            DictHelper.get(d_dict, "key1.key2.key4")
        with self.assertRaises(KeyError):
            DictHelper.get(d_dict, "non_existant")
        # Pas d'erreur levée + None retourné si non existant et raise_error=False
        self.assertIsNone(DictHelper.get(d_dict, "key1.key2.key4", raise_error=False))
        self.assertIsNone(DictHelper.get(d_dict, "non_existant", raise_error=False))
