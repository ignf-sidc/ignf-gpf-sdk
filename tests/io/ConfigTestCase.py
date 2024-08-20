from pathlib import Path
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.io.Errors import ConfigReaderError
from tests.GpfTestCase import GpfTestCase

# pylint:disable=protected-access


class ConfigTestCase(GpfTestCase):
    """Tests ConfigTestCase class.

    cmd : python3 -m unittest -b tests.io.ConfigTestCase
    """

    def setUp(self) -> None:
        # On détruit le singleton Config
        Config._instance = None

    def test_get_config(self) -> None:
        """Vérifie le bon fonctionnement de get_config."""
        # On vérifie le type de get_config
        self.assertEqual(type(Config().get_config()), dict)

    def test_read(self) -> None:
        """Vérifie le bon fonctionnement de read."""
        # On vérifie que l'on a les valeurs par défaut
        self.assertEqual(Config().get("store_authentification", "login"), "LOGIN_TO_MODIFY")
        self.assertEqual(Config().get("store_authentification", "password"), "PASSWORD_TO_MODIFY")
        self.assertEqual(Config().get("store_api", "datastore"), "DATASTORE_ID_TO_MODIFY")
        self.assertEqual(Config().get("logging", "log_level"), "INFO")
        # On ouvre le nouveau fichier
        Config().read(GpfTestCase.conf_dir_path / "test_overload.ini")
        # On vérifie que l'on a les nouvelles valeurs et toujours les anciennes non modifiés
        self.assertEqual(Config().get("store_authentification", "login"), "TEST_LOGIN")
        self.assertEqual(Config().get("store_authentification", "password"), "TEST_PASSWORD")
        self.assertEqual(Config().get("store_api", "datastore"), "TEST_DATASTORE")
        self.assertEqual(Config().get("logging", "log_level"), "INFO")
        # On ouvre le nouveau fichier TOML cette fois-ci
        Config().read(GpfTestCase.conf_dir_path / "test_overload.toml")
        # On vérifie que l'on a les nouvelles valeurs et toujours les anciennes non modifiés
        self.assertEqual(Config().get("store_authentification", "login"), "TEST_LOGIN_TOML")
        self.assertEqual(Config().get("store_authentification", "password"), "TEST_PASSWORD_TOML")
        self.assertEqual(Config().get("store_api", "datastore"), "TEST_DATASTORE_TOML")
        self.assertEqual(Config().get("logging", "log_level"), "INFO")

    def test_get(self) -> None:
        """Vérifie le bon fonctionnement de get, get_int, get_float et get_bool."""
        Config().read(GpfTestCase.conf_dir_path / "test_value_type.ini")
        # On peut récupérer des strings
        self.assertEqual(Config().get("test_value_type", "my_string"), "titi")
        self.assertEqual(Config().get("test_value_type", "my_int"), "42")
        self.assertEqual(Config().get("test_value_type", "my_float"), "4.2")
        self.assertEqual(Config().get("test_value_type", "my_bool"), "true")
        # Ou le type adapté
        self.assertEqual(Config().get_int("test_value_type", "my_int"), 42)
        self.assertEqual(Config().get_float("test_value_type", "my_float"), 4.2)
        self.assertEqual(Config().get_bool("test_value_type", "my_bool"), True)
        # On a la valeur fallback par défaut si non existant et fall back non None
        self.assertEqual(Config().get("test_value_type", "not_existing", fallback="fallback"), "fallback")
        self.assertEqual(Config().get_int("test_value_type", "not_existing", fallback=42), 42)
        self.assertEqual(Config().get_float("test_value_type", "not_existing", fallback=4.2), 4.2)
        self.assertEqual(Config().get_bool("test_value_type", "not_existing", fallback=True), True)
        # On a None si option non existante et fallback None avec 'get' et 'get_bool'
        self.assertIsNone(Config().get("test_value_type", "not_existing", fallback=None))
        self.assertFalse(Config().get_bool("test_value_type", "not_existing", fallback=None))
        # On a une exception si option non existante, fallback None et qu'un type est demandé
        with self.assertRaises(ConfigReaderError) as o_arc:
            Config().get_int("test_value_type", "not_existing", fallback=None)
        self.assertIn("Veuillez vérifier la config ([test_value_type-[not_existing]]), entier non reconnu (None).", o_arc.exception.message)
        with self.assertRaises(ConfigReaderError) as o_arc:
            Config().get_float("test_value_type", "not_existing", fallback=None)
        self.assertIn("Veuillez vérifier la config ([test_value_type-[not_existing]]), nombre flottant non reconnu (None).", o_arc.exception.message)

    def test_get_temp(self) -> None:
        """Vérifie le bon fonctionnement de get_temp."""
        self.assertEqual(Config().get_temp(), Path("/tmp"))

    def test_same_instance(self) -> None:
        """Même instance."""
        # Première instance
        o_config_1 = Config()
        # Deuxième instance
        o_config_2 = Config()
        # Ca doit être les mêmes
        self.assertEqual(o_config_1, o_config_2)
