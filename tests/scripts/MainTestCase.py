from sdk_entrepot_gpf.scripts.run import Main
from tests.GpfTestCase import GpfTestCase


class MainTestCase(GpfTestCase):
    """Tests Main class.

    cmd : python3 -m unittest -b tests.scripts.MainTestCase
    """

    def test_parse_args(self) -> None:
        """Vérifie le bon fonctionnement de parse_args."""
        # Sans rien, ça quitte en erreur
        with self.assertRaises(SystemExit) as o_arc:
            Main.parse_args(args=[])
        self.assertEqual(o_arc.exception.code, 2)

        # Avec --help, ça quitte en succès
        with self.assertRaises(SystemExit) as o_arc:
            Main.parse_args(args=["--help"])
        self.assertEqual(o_arc.exception.code, 0)

        # Avec --version, ça quitte en succès
        with self.assertRaises(SystemExit) as o_arc:
            Main.parse_args(args=["--version"])
        self.assertEqual(o_arc.exception.code, 0)

    def test_parse_args_auth(self) -> None:
        """Vérifie le bon fonctionnement de parse_args."""
        # Avec tâche="auth" seul, c'est ok
        o_args = Main.parse_args(args=["auth"])
        self.assertEqual(o_args.task, "auth")
        self.assertIsNone(o_args.show)

        # Avec tâche="auth" et show="token", c'est ok
        o_args = Main.parse_args(args=["auth", "token"])
        self.assertEqual(o_args.task, "auth")
        self.assertEqual(o_args.show, "token")

        # Avec tâche "auth" et show="header", c'est ok
        o_args = Main.parse_args(args=["auth", "header"])
        self.assertEqual(o_args.task, "auth")
        self.assertEqual(o_args.show, "header")

    def test_parse_args_config(self) -> None:
        """Vérifie le bon fonctionnement de parse_args."""
        # Avec tâche="config" seul, c'est ok
        o_args = Main.parse_args(args=["config"])
        self.assertEqual(o_args.task, "config")
        self.assertIsNone(o_args.file)
        self.assertIsNone(o_args.section)
        self.assertIsNone(o_args.option)

        # Avec tâche="config" et file="toto.ini", c'est ok
        o_args = Main.parse_args(args=["config", "--file", "toto.ini"])
        self.assertEqual(o_args.task, "config")
        self.assertEqual(o_args.file, "toto.ini")
        self.assertIsNone(o_args.section)
        self.assertIsNone(o_args.option)

        # Avec tâche "config", file="toto.ini" et section="store_authentification", c'est ok
        o_args = Main.parse_args(args=["config", "--file", "toto.ini", "store_authentification"])
        self.assertEqual(o_args.task, "config")
        self.assertEqual(o_args.file, "toto.ini")
        self.assertEqual(o_args.section, "store_authentification")
        self.assertIsNone(o_args.option)

        # Avec tâche "config", section="store_authentification", c'est ok
        o_args = Main.parse_args(args=["config", "store_authentification"])
        self.assertEqual(o_args.task, "config")
        self.assertIsNone(o_args.file)
        self.assertEqual(o_args.section, "store_authentification")
        self.assertIsNone(o_args.option)

        # Avec tâche "config", section="store_authentification" et option="password", c'est ok
        o_args = Main.parse_args(args=["config", "store_authentification", "password"])
        self.assertEqual(o_args.task, "config")
        self.assertIsNone(o_args.file)
        self.assertEqual(o_args.section, "store_authentification")
        self.assertEqual(o_args.option, "password")
