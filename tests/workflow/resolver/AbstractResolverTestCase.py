from unittest.mock import MagicMock, PropertyMock, patch

from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.resolver.AbstractResolver import AbstractResolver

from tests.GpfTestCase import GpfTestCase


class AbstractResolverTestCase(GpfTestCase):
    """Tests AbstractResolver class.

    cmd : python3 -m unittest -b tests.workflow.resolver.AbstractResolverTestCase
    """

    def test_get_ok(self) -> None:
        """test unitaire pour get() quand ça fonctionne"""

        d_data = {"key": "val", "dict": {"key": "val_dict"}, "list": ["val_list", {"key": "val_list_dict"}]}
        l_res = [
            ("key", "val"),
            ("dict.key", "val_dict"),
            ("list[0]", "val_list"),
            ("list[1].key", "val_list_dict"),
        ]
        for s_js_key, s_res in l_res:
            self.assertEqual(s_res, AbstractResolver.get(d_data, s_js_key))

    def test_get_ko(self) -> None:
        """test unitaire pour get() quand ça ne fonctionne pas"""

        d_data = {"key": "val", "dict": {"key": "val_dict"}, "list": ["val_list", {"key": "val_list_dict"}]}
        l_res = [
            ("bad_key", ("bad_key", "bad_key", "key, dict, list")),
            ("dict.bad_key", ("bad_key", "bad_key", "key")),
            ("bad_list[0]", ("bad_list", "bad_list[0]", "key, dict, list")),
            ("list[1].bad_key", ("bad_key", "bad_key", "key")),
        ]
        for s_js_key, s_params in l_res:
            with self.assertRaises(KeyError) as o_key_error:
                o_fake_om = MagicMock()
                o_fake_om.error = MagicMock()
                with patch.object(Config, "om", new_callable=PropertyMock, return_value=o_fake_om):
                    AbstractResolver.get(d_data, s_js_key)
            # Vérifications
            # Key error doit être levée
            self.assertEqual(o_key_error.exception.args[0], s_params[0])
            # une erreur doit être logué
            o_fake_om.error.assert_called_once_with(f"Impossible de résoudre la clef '{s_js_key}' : sous-clef '{s_params[1]}' non trouvée, clefs possibles à ce niveau : {s_params[2]}")
