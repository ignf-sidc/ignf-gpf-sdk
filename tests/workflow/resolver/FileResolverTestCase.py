from sdk_entrepot_gpf.workflow.resolver.Errors import ResolveFileInvalidError, ResolveFileNotFoundError, ResolverError
from sdk_entrepot_gpf.workflow.resolver.FileResolver import FileResolver
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver

from tests.GpfTestCase import GpfTestCase


class FileResolverTestCase(GpfTestCase):
    """Tests FileResolver class.

    cmd : python3 -m unittest -b tests.workflow.resolver.FileResolverTestCase
    """

    root_path = GpfTestCase.test_dir_path / "workflow" / "resolver" / "FileResolver"

    s_str_value: str = "contenu du fichier de type str"
    s_list_value: str = str('["info_1", "info_2"]')
    s_dict_value: str = str('{"k1":"v1", "k2":"v2"}')

    def test_resolve_other(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un str."""
        o_file_resolver = FileResolver("file", self.root_path)
        # Si mot clé incorrect erreur levée
        with self.assertRaises(ResolverError) as o_arc_1:
            o_file_resolver.resolve("other(text.txt)")
        self.assertRegex(o_arc_1.exception.message, r"^Erreur du résolveur 'file' avec la chaîne 'other\(text.txt\)' : la chaîne ne correspond pas au pattern \(.*\)$")

    def test_resolve_str(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un str."""
        o_file_resolver = FileResolver("file", self.root_path)
        # Si ok
        s_test_str: str = o_file_resolver.resolve("str(text.txt)")
        self.assertEqual(self.s_str_value, s_test_str)
        # Si non existant erreur levée
        with self.assertRaises(ResolveFileNotFoundError) as o_arc_1:
            o_file_resolver.resolve("str(not-existing.txt)")
        self.assertEqual(
            o_arc_1.exception.message, f"Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'str(not-existing.txt)': fichier ({self.root_path}/not-existing.txt) non existant."
        )

    def test_resolve_list(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un list."""
        o_file_resolver = FileResolver("file", self.root_path)
        # Si ok
        s_test_list: str = o_file_resolver.resolve("list(list.json)")
        self.assertEqual(self.s_list_value, s_test_list)
        # Si non existant erreur levée
        with self.assertRaises(ResolveFileNotFoundError) as o_arc_1:
            o_file_resolver.resolve("list(not-existing.json)")
        self.assertEqual(
            o_arc_1.exception.message, f"Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'list(not-existing.json)': fichier ({self.root_path}/not-existing.json) non existant."
        )
        # Si pas liste erreur levée
        with self.assertRaises(ResolveFileInvalidError) as o_arc_2:
            o_file_resolver.resolve("list(dict.json)")
        self.assertEqual(o_arc_2.exception.message, "Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'list(dict.json)'.")
        # Si pas valide erreur levée
        with self.assertRaises(ResolveFileInvalidError) as o_arc_3:
            o_file_resolver.resolve("list(not-valid.json)")
        self.assertEqual(o_arc_3.exception.message, "Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'list(not-valid.json)'.")

    def test_resolve_dict(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve pour un dict."""
        o_file_resolver = FileResolver("file", self.root_path)
        # Si ok
        s_test_dict: str = o_file_resolver.resolve("dict(dict.json)")
        self.assertEqual(self.s_dict_value, s_test_dict)
        # Si non existant erreur levée
        with self.assertRaises(ResolveFileNotFoundError) as o_arc_1:
            o_file_resolver.resolve("dict(not-existing.json)")
        self.assertEqual(
            o_arc_1.exception.message, f"Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'dict(not-existing.json)': fichier ({self.root_path}/not-existing.json) non existant."
        )
        # Si pas liste erreur levée
        with self.assertRaises(ResolveFileInvalidError) as o_arc_2:
            o_file_resolver.resolve("dict(list.json)")
        self.assertEqual(o_arc_2.exception.message, "Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'dict(list.json)'.")
        # Si pas valide erreur levée
        with self.assertRaises(ResolveFileInvalidError) as o_arc_3:
            o_file_resolver.resolve("dict(not-valid.json)")
        self.assertEqual(o_arc_3.exception.message, "Erreur de traitement d'un fichier (résolveur 'file') avec la chaîne 'dict(not-valid.json)'.")

    def test_global_resolve(self) -> None:
        """Vérifie le bon fonctionnement en pratique."""
        GlobalResolver().add_resolver(FileResolver("file", self.root_path))
        # Test 1 : texte
        s_text_1 = "Test sur du text : {file.str(text.txt)}"
        s_result_1 = GlobalResolver().resolve(s_text_1)
        self.assertEqual(s_result_1, "Test sur du text : contenu du fichier de type str")
        # Test 2 : liste
        s_text_2 = '{"ma liste" : ["_file_","list(list.json)"]}'
        s_result_2 = GlobalResolver().resolve(s_text_2)
        self.assertEqual(s_result_2, '{"ma liste" : ["info_1", "info_2"]}')
        # Test 3 : dict
        s_text_3 = '{"mon dict" : {"_file_":"dict(dict.json)"} }'
        s_result_3 = GlobalResolver().resolve(s_text_3)
        self.assertEqual(s_result_3, '{"mon dict" : {"k1":"v1", "k2":"v2"} }')
