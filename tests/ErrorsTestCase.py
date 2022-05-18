import unittest

from ignf_gpf_api.Errors import GpfApiError


class ErrorsTestCase(unittest.TestCase):
    """Tests Errors classes.

    cmd : python3 -m unittest -b tests.ErrorsTestCase
    """

    @staticmethod
    def raise_GpfApiError() -> None:
        raise GpfApiError("message")

    def test_GpfApiError(self) -> None:
        """Vérifie le bon fonctionnement de GpfApiError."""
        # On lève l'exception
        with self.assertRaises(GpfApiError) as o_arc:
            ErrorsTestCase.raise_GpfApiError()
        # Vérifications
        # Message renvoi message
        self.assertEqual(o_arc.exception.message, "message")
        # La forme str renvoi message
        self.assertEqual(str(o_arc.exception), "message")
        self.assertEqual(f"{o_arc.exception}", "message")
        # La représentation est le nom de classe + le message
        self.assertEqual(repr(o_arc.exception), "GpfApiError(message)")
