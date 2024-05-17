from typing import Any, Callable, Dict, List, Optional, Tuple

from pathlib import Path
from unittest.mock import patch, MagicMock

import requests
from sdk_entrepot_gpf.io.Errors import ConflictError
from sdk_entrepot_gpf.store.CheckExecution import CheckExecution
from sdk_entrepot_gpf.workflow.Errors import UploadFileError
from sdk_entrepot_gpf.workflow.action.ActionAbstract import ActionAbstract

from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction
from sdk_entrepot_gpf.store.Upload import Upload
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.Errors import GpfSdkError
from tests.GpfTestCase import GpfTestCase

# mypy: ignore-errors
# pylint:disable=too-many-arguments
# pylint:disable=too-many-locals
# pylint:disable=too-many-branches
# pylint:disable=dangerous-default-value
# pylint:disable=too-many-statements
# pylint:disable=protected-access
# fmt: off
# (on désactive le formatage en attendant Python 3.10 et la possibilité de mettre des parenthèses pour gérer le multi with proprement)

class  UploadActionNoPrivate(UploadAction):
    """Classe pour accéder aux fonction privée de UploadAction"""

    def set_upload(self, o_upload: Optional[Upload]) -> None:
        """change l'upload"""
        self._UploadAction__upload = o_upload# pylint: disable=no-member,invalid-name,attribute-defined-outside-init

    def create_upload(self, datastore: Optional[str]) -> None:
        """Crée l'upload après avoir vérifié s'il n'existe pas déjà...

        Args:
            datastore (Optional[str]): id du datastore à utiliser.
        """
        self._UploadAction__create_upload(datastore) # pylint: disable=no-member
    def add_tags(self) -> None:
        """Ajoute les tags."""
        self._UploadAction__add_tags() # pylint: disable=no-member

    def add_comments(self) -> None:
        """Ajoute les commentaires."""
        self._UploadAction__add_comments() # pylint: disable=no-member

    def push_data_files(self, check_conflict: bool = True) -> None:
        """Téléverse les fichiers de données (listés dans le dataset).

        Args:
            check_conflict (bool): Si une vérification de la bonne livraison des fichier en conflict ou en timeout est lancée.
        """
        self._UploadAction__push_data_files(check_conflict) # pylint: disable=no-member
    def push_md5_files(self, check_conflict: bool = True) -> None:
        """Téléverse les fichiers de clefs (listés dans le dataset).

        Args:
            check_conflict (bool): Si une vérification de la bonne livraison des fichier en conflict ou en timeout est lancée..
        """
        self._UploadAction__push_md5_files(check_conflict) # pylint: disable=no-member
    def normalise_api_push_md5_file(self, path: Path, nom: str) -> None:
        """fonction cachant api_push_md5_file pour avoir une fonction ayant les même entrées que api_push_data_file, utilisé comme paramétre de __push_files

        Args:
            path (Path): chemin le la chef MD5
            nom (str): non du ficher md5
        """
        self._UploadAction__normalise_api_push_md5_file(path, nom) # pylint: disable=no-member
    def push_files(self, l_files: List[Tuple[Path, str]], f_api_push: Callable[[Path, str], None], f_api_delete: Callable[[str], None], check_conflict: bool = True) -> int:
        """pousse un ficher de données ou un ficher md5 sur le store. Gére la reprise de Livraison et les conflicts lors de la livraison.

        Args:
            l_files (List[Tuple[Path, str]]): liste de tuple Path du ficher à livre, nom du ficher sous la gpf
            f_api_push (Callable[[Path, str], None]): fonction pour livrer les données
            f_api_delete (Callable[[str], None]): fonction pour supprimé les données si livrer partiellement.
            check_conflict (bool): Si une vérification de la bonne livraison des fichier en conflict ou en timeout est lancée..

        Returns:
            int: nombre de ficher réellement téléverser durant l'action
        """
        return self._UploadAction__push_files(l_files, f_api_push, f_api_delete, check_conflict) # pylint: disable=no-member
    def check_file_uploaded(self, l_files: List[Tuple[Path, str]]) -> List[Tuple[Path, str]]:
        """vérifie si les fichiers donnée en entrée soit bien livrer

        Args:
            l_files (List[Tuple[Path, str]]): liste des ficher à vérifier (path du fichier, chemin du fichier sur la GPF)

        Raises:
            GpfSdkError: _description_

        Returns:
            List[Tuple[Path, str]]: liste des fichiers en erreur (path du fichier, chemin du fichier sur la GPF)
        """
        return self._UploadAction__check_file_uploaded(l_files) # pylint: disable=no-member
    def close(self) -> None:
        """Ferme la livraison."""
        self._UploadAction__close() # pylint: disable=no-member



class UploadActionTestCase(GpfTestCase):
    """Tests UploadAction class.

    cmd : python3 -m unittest -b tests.workflow.action.UploadActionTestCase
    """

    # constante afin de savoir si un fichier téléversé est entièrement téléversé ou pas.
    SIZE_OK = 10000
    @classmethod
    def setUpClass(cls) -> None:
        """fonction lancée une fois avant tous les tests de la classe"""
        super().setUpClass()
        # On détruit le Singleton Config
        Config._instance = None
        # On charge une config spéciale pour les tests d'upload
        o_config = Config()
        o_config.read(GpfTestCase.conf_dir_path / "test_upload.ini")
        o_config.set_output_manager(MagicMock())

    @classmethod
    def tearDownClass(cls) -> None:
        """fonction lancée une fois après tous les tests de la classe"""
        super().tearDownClass()
        # On détruit le Singleton Config
        Config._instance = None

    def test_find_upload(self) -> None:
        """Test find_upload."""
        o_u1 = Upload({"_id": "upload_1"})
        o_u2 = Upload({"_id": "upload_2"})
        # création du dataset
        o_mock_dataset = MagicMock()
        o_mock_dataset.data_files = {Path("./a"): "a", Path("./b"): "b", Path("./c"): "c"}
        o_mock_dataset.md5_files = [Path("./a"), Path("./2")]
        o_mock_dataset.upload_infos = {"_id": "upload_base", "name": "upload_name"}
        o_mock_dataset.tags = {"tag1": "val1", "tag2": "val2"}
        o_mock_dataset.comments = ["comm1", "comm2", "comm3"]
        # exécution de UploadAction
        o_ua = UploadAction(o_mock_dataset)
        # Mock de ActionAbstract.get_filters et Upload.api_list
        with patch.object(ActionAbstract, "get_filters", return_value=({"info":"val"}, {"tag":"val"})) as o_mock_get_filters:
            with patch.object(Upload, "api_list", return_value=[o_u1, o_u2]) as o_mock_api_list :
                # Appel de la fonction find_upload
                o_upload = o_ua.find_upload("datastore_id")
                # Vérifications
                o_mock_get_filters.assert_called_once_with("upload", o_mock_dataset.upload_infos, o_mock_dataset.tags)
                o_mock_api_list.assert_called_once_with(infos_filter={"info":"val"}, tags_filter={"tag":"val"}, datastore="datastore_id")
                self.assertEqual(o_upload, o_u1)
        with patch.object(ActionAbstract, "get_filters", return_value=({"info":"val"}, {"tag":"val"})) as o_mock_get_filters:
            with patch.object(Upload, "api_list", return_value=[]) as o_mock_api_list :
                # Appel de la fonction find_upload
                o_upload = o_ua.find_upload("datastore_id")
                # Vérifications
                o_mock_get_filters.assert_called_once_with("upload", o_mock_dataset.upload_infos, o_mock_dataset.tags)
                o_mock_api_list.assert_called_once_with(infos_filter={"info":"val"}, tags_filter={"tag":"val"}, datastore="datastore_id")
                self.assertEqual(None, o_upload)

    def test_run(self)->None:
        """vérification de la fonction run"""
        s_datastore="test"

        # upload None
        with patch.object(UploadAction, "_UploadAction__create_upload") as o_mock__create_upload:

            o_mock_dataset = MagicMock()
            o_ua = UploadAction(o_mock_dataset)
            with self.assertRaises(GpfSdkError) as o_err:
                o_upload = o_ua.run(s_datastore)
            self.assertEqual("Erreur à la création de la livraison.", o_err.exception.message)


        # upload fermé
        with patch.object(UploadAction, "_UploadAction__create_upload") as o_mock__create_upload, \
            patch.object(UploadAction, "_UploadAction__add_tags") as o_mock__add_tags, \
            patch.object(UploadAction, "_UploadAction__add_comments") as o_mock__add_comments, \
            patch.object(UploadAction, "_UploadAction__push_data_files") as o_mock__push_data_files, \
            patch.object(UploadAction, "_UploadAction__push_md5_files") as o_mock__push_md5_files, \
            patch.object(UploadAction, "_UploadAction__check_file_uploaded") as o_mock__check_file_uploaded, \
            patch.object(UploadAction, "_UploadAction__close") as o_mock__close:

            o_mock_dataset = MagicMock()
            o_ua = UploadActionNoPrivate(o_mock_dataset)
            o_mock_upload = MagicMock()
            o_mock_upload.is_open.return_value = False
            o_ua.set_upload(o_mock_upload)
            o_upload = o_ua.run(s_datastore)
            self.assertEqual(o_upload, o_mock_upload)
            o_mock__create_upload.assert_called_once_with(s_datastore)
            o_mock__add_tags.assert_not_called()
            o_mock__add_comments.assert_not_called()
            o_mock__push_data_files.assert_not_called()
            o_mock__push_md5_files.assert_not_called()
            o_mock__check_file_uploaded.assert_not_called()
            o_mock__close.assert_not_called()

        # upload ouvert sans vérification avant fermeture
        with patch.object(UploadAction, "_UploadAction__create_upload") as o_mock__create_upload, \
            patch.object(UploadAction, "_UploadAction__add_tags") as o_mock__add_tags, \
            patch.object(UploadAction, "_UploadAction__add_comments") as o_mock__add_comments, \
            patch.object(UploadAction, "_UploadAction__push_data_files") as o_mock__push_data_files, \
            patch.object(UploadAction, "_UploadAction__push_md5_files") as o_mock__push_md5_files, \
            patch.object(UploadAction, "_UploadAction__check_file_uploaded") as o_mock__check_file_uploaded, \
            patch.object(UploadAction, "_UploadAction__close") as o_mock__close:

            o_mock_dataset = MagicMock()
            o_ua = UploadActionNoPrivate(o_mock_dataset)
            o_mock_upload = MagicMock()
            o_mock_upload.is_open.return_value = True
            o_ua.set_upload(o_mock_upload)
            o_upload = o_ua.run(s_datastore)
            self.assertEqual(o_upload, o_mock_upload)
            o_mock__create_upload.assert_called_once_with(s_datastore)
            o_mock__add_tags.assert_called_once_with()
            o_mock__add_comments.assert_called_once_with()
            o_mock__push_data_files.assert_called_once_with(True)
            o_mock__push_md5_files.assert_called_once_with(True)
            o_mock__check_file_uploaded.assert_not_called()
            o_mock__close.assert_called_once_with()

        # upload ouvert avec vérification avant fermeture ok
        with patch.object(UploadAction, "_UploadAction__create_upload") as o_mock__create_upload, \
            patch.object(UploadAction, "_UploadAction__add_tags") as o_mock__add_tags, \
            patch.object(UploadAction, "_UploadAction__add_comments") as o_mock__add_comments, \
            patch.object(UploadAction, "_UploadAction__push_data_files") as o_mock__push_data_files, \
            patch.object(UploadAction, "_UploadAction__push_md5_files") as o_mock__push_md5_files, \
            patch.object(UploadAction, "_UploadAction__check_file_uploaded", return_value=[]) as o_mock__check_file_uploaded, \
            patch.object(UploadAction, "_UploadAction__close") as o_mock__close:

            o_mock_dataset = MagicMock()
            o_mock_dataset.data_files = {
                Path("file1"): "file1",
                Path("file2"): "file2",
                Path("file3"): "file3",
            }
            o_mock_dataset.md5_files = [Path("md5.md5")]
            o_ua = UploadActionNoPrivate(o_mock_dataset)
            o_mock_upload = MagicMock()
            o_mock_upload.is_open.return_value = True
            o_ua.set_upload(o_mock_upload)
            o_upload = o_ua.run(s_datastore, check_before_close=True)
            self.assertEqual(o_upload, o_mock_upload)
            o_mock__create_upload.assert_called_once_with(s_datastore)
            o_mock__add_tags.assert_called_once_with()
            o_mock__add_comments.assert_called_once_with()
            o_mock__push_data_files.assert_called_once_with(False)
            o_mock__push_md5_files.assert_called_once_with(False)
            o_mock__check_file_uploaded.assert_called_once_with(
                [
                    (Path("file1"), "file1"),
                    (Path("file2"), "file2"),
                    (Path("file3"), "file3"),
                    (Path("md5.md5"), ""),
                ]
            )
            o_mock__close.assert_called_once_with()

        l_error = [(Path("KO"), "ko")]
        # upload ouvert avec vérification avant fermeture ko
        with patch.object(UploadAction, "_UploadAction__create_upload") as o_mock__create_upload, \
            patch.object(UploadAction, "_UploadAction__add_tags") as o_mock__add_tags, \
            patch.object(UploadAction, "_UploadAction__add_comments") as o_mock__add_comments, \
            patch.object(UploadAction, "_UploadAction__push_data_files") as o_mock__push_data_files, \
            patch.object(UploadAction, "_UploadAction__push_md5_files") as o_mock__push_md5_files, \
            patch.object(UploadAction, "_UploadAction__check_file_uploaded", return_value=l_error) as o_mock__check_file_uploaded, \
            patch.object(UploadAction, "_UploadAction__close") as o_mock__close:

            o_mock_dataset = MagicMock()
            o_mock_dataset.data_files = {
                Path("file1"): "file1",
                Path("file2"): "file2",
                Path("file3"): "file3",
            }
            o_mock_dataset.md5_files = [Path("md5.md5")]
            o_ua = UploadActionNoPrivate(o_mock_dataset)
            o_mock_upload = MagicMock()
            o_mock_upload.is_open.return_value = True
            o_ua.set_upload(o_mock_upload)
            with self.assertRaises(UploadFileError) as o_err:
                o_upload = o_ua.run(s_datastore, check_before_close=True)

            self.assertEqual(f"Livraison {o_mock_upload['name']} : Problème de livraison pour {len(l_error)} fichiers. Il faut relancer la livraison.", o_err.exception.message)
            self.assertEqual(l_error, o_err.exception.files)
            o_mock__create_upload.assert_called_once_with(s_datastore)
            o_mock__add_tags.assert_called_once_with()
            o_mock__add_comments.assert_called_once_with()
            o_mock__push_data_files.assert_called_once_with(False)
            o_mock__push_md5_files.assert_called_once_with(False)
            o_mock__check_file_uploaded.assert_called_once_with(
                [
                    (Path("file1"), "file1"),
                    (Path("file2"), "file2"),
                    (Path("file3"), "file3"),
                    (Path("md5.md5"), ""),
                ]
            )
            o_mock__close.assert_not_called()

    def test_create_upload(self)->None:
        """vérifie fonction __create_upload"""
        s_datastore="test"
        # find_upload vide
        for s_behavior in UploadAction.BEHAVIORS:
            with patch.object(UploadAction, "find_upload", return_value = None) as o_mock_find_upload, \
                patch.object(Upload, "api_create") as o_mock_api_create:

                o_dataset=MagicMock()
                o_ua = UploadActionNoPrivate(o_dataset, behavior=s_behavior)
                o_ua.create_upload(datastore=s_datastore)
                o_mock_find_upload.assert_called_once_with(s_datastore)
                o_mock_api_create.assert_called_once_with(o_dataset.upload_infos, route_params={"datastore": s_datastore})

        # find_upload non vide et BEHAVIOR_STOP
        s_behavior = UploadAction.BEHAVIOR_STOP
        o_mock_upload = MagicMock()
        o_dataset=MagicMock()
        o_ua = UploadActionNoPrivate(o_dataset, behavior=s_behavior)
        with patch.object(UploadAction, "find_upload", return_value = o_mock_upload) as o_mock_find_upload, \
            patch.object(Upload, "api_create") as o_mock_api_create:
            with self.assertRaises(GpfSdkError) as o_err:
                o_ua.create_upload(datastore=s_datastore)
            self.assertEqual(f"Impossible de créer la livraison, une livraison identique {o_mock_upload} existe déjà.", o_err.exception.message)
            o_mock_find_upload.assert_called_once_with(s_datastore)
            o_mock_api_create.assert_not_called()

        # find_upload non vide et BEHAVIOR_CONTINUE
        s_behavior = UploadAction.BEHAVIOR_CONTINUE
        o_mock_upload = MagicMock()
        o_dataset=MagicMock()
        o_ua = UploadActionNoPrivate(o_dataset, behavior=s_behavior)
        with patch.object(UploadAction, "find_upload", return_value = o_mock_upload) as o_mock_find_upload, \
            patch.object(Upload, "api_create") as o_mock_api_create:

            o_ua.create_upload(datastore=s_datastore)
            o_mock_find_upload.assert_called_once_with(s_datastore)
            o_mock_api_create.assert_not_called()
            o_mock_upload.is_open.assert_called_once_with()
            self.assertEqual(o_ua.upload, o_mock_upload)


        # find_upload non vide et BEHAVIOR_DELETE
        s_behavior = UploadAction.BEHAVIOR_DELETE
        o_mock_upload_old = MagicMock()
        o_mock_upload_new = MagicMock()
        o_dataset=MagicMock()
        o_ua = UploadActionNoPrivate(o_dataset, behavior=s_behavior)
        with patch.object(UploadAction, "find_upload", return_value = o_mock_upload_old) as o_mock_find_upload, \
            patch.object(Upload, "api_create", return_value=o_mock_upload_new) as o_mock_api_create:

            o_ua.create_upload(datastore=s_datastore)
            o_mock_find_upload.assert_called_once_with(s_datastore)
            o_mock_upload_old.api_delete.assert_called_once_with()
            o_mock_api_create.assert_called_once_with(o_dataset.upload_infos, route_params={"datastore": s_datastore})
            self.assertEqual(o_ua.upload, o_mock_upload_new)

        # BEHAVIOR non valide
        s_behavior = "toto"
        o_mock_upload = MagicMock()
        o_dataset=MagicMock()
        o_ua = UploadActionNoPrivate(o_dataset, behavior=s_behavior)
        with patch.object(UploadAction, "find_upload", return_value = o_mock_upload) as o_mock_find_upload, \
            patch.object(Upload, "api_create") as o_mock_api_create:
            with self.assertRaises(GpfSdkError) as e_err:
                o_ua.create_upload(datastore=s_datastore)
            self.assertEqual(f"Le comportement {s_behavior} n'est pas reconnu (STOP|CONTINUE|DELETE), l'exécution de traitement est annulée.", e_err.exception.message)
            o_mock_find_upload.assert_called_once_with(s_datastore)
            o_mock_api_create.assert_not_called()
            o_mock_upload.is_open.assert_not_called()

    def test_add_tags(self) -> None:
        """test de __add_tags"""
        # pas d'upload ou pas de tags => rien de fait
        o_mock_upload = MagicMock()
        for o_upload, o_tags in [
            (None, None),
            (None, {"tag":"val"}),
            (o_mock_upload, []),
            (o_mock_upload, None),
        ]:
            o_dataset=MagicMock()
            o_dataset.tags=o_tags
            o_ua = UploadActionNoPrivate(o_dataset)
            o_ua.set_upload(o_upload)
            o_ua.add_tags()
            o_mock_upload.api_add_tags.assert_not_called()

        # on a upload et tags => ajout des tags
        o_tags =  {"tag":"val"}
        o_dataset=MagicMock()
        o_dataset.tags=o_tags
        o_ua = UploadActionNoPrivate(o_dataset)
        o_ua.set_upload(o_mock_upload)
        o_ua.add_tags()
        o_mock_upload.api_add_tags.assert_called_once_with(o_tags)

    def test_add_comments(self)->None:
        """test de __add_comments"""
        # pas de upload => rien n'est fait
        o_dataset=MagicMock()
        o_ua = UploadActionNoPrivate(o_dataset)
        o_ua.set_upload(None)
        with patch.object(Upload, "api_add_comment") as o_mock_api_add_comment:
            o_ua.add_comments()
            o_mock_api_add_comment.assert_not_called()

        # un upload
        for l_expected_comments, l_upload_comments in [
            (["comm1", "comm2"], []),
            (["comm1", "comm2"], ["comm3", "comm4"]),
        ]:
            o_dataset=MagicMock()
            o_dataset.comments=l_expected_comments + l_upload_comments
            o_mock_upload = MagicMock()
            o_mock_upload.api_list_comments.return_value=[{"text": s_comment} for s_comment in  l_upload_comments]
            o_ua = UploadActionNoPrivate(o_dataset)
            o_ua.set_upload(o_mock_upload)
            o_ua.add_comments()
            self.assertEqual(len(l_expected_comments), o_mock_upload.api_add_comment.call_count)
            for s_comment in l_expected_comments:
                o_mock_upload.api_add_comment.assert_any_call({"text": s_comment})

    def test_push_data_files(self)->None:
        """test de __push_data_files"""
        # pas de upload => rien n'est fait
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(None)
        with patch.object(UploadAction, "_UploadAction__push_files") as o_mock_push_files:
            o_ua.push_data_files()
            o_mock_push_files.assert_not_called()

        # upload :
        o_dataset=MagicMock()
        o_dataset.data_files = {Path("a"): "a", Path("b"): "b"}
        o_ua = UploadActionNoPrivate(o_dataset)

        for b_check_conflict in [True, False]:
            o_mock_upload = MagicMock()
            o_ua.set_upload(o_mock_upload)
            with patch.object(UploadAction, "_UploadAction__push_files") as o_mock_push_files:
                o_ua.push_data_files(b_check_conflict)
            o_mock_push_files.assert_called_once_with(
                list(o_dataset.data_files.items()),
                o_mock_upload.api_push_data_file,
                o_mock_upload.api_delete_data_file,
                b_check_conflict,
            )


    def test_push_md5_files(self)->None:
        """test de __push_md5_files"""
        # pas de upload => rien n'est fait
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(None)
        with patch.object(UploadAction, "_UploadAction__push_files") as o_mock_push_files:
            o_ua.push_md5_files()
            o_mock_push_files.assert_not_called()

        # upload :
        o_dataset=MagicMock()
        o_dataset.md5_files = [Path("a"), Path("b")]
        o_ua = UploadActionNoPrivate(o_dataset)

        for b_check_conflict in [True, False]:
            o_mock_upload = MagicMock()
            o_ua.set_upload(o_mock_upload)
            with patch.object(UploadAction, "_UploadAction__push_files") as o_mock_push_files:
                with patch.object(UploadAction, "_UploadAction__normalise_api_push_md5_file") as o_mock_normalise_api_push_md5_file:
                    o_ua.push_md5_files(b_check_conflict)
                    o_mock_push_files.assert_called_once_with(
                        [(p_file, "") for p_file in o_dataset.md5_files],
                        o_mock_normalise_api_push_md5_file,
                        o_mock_upload.api_delete_md5_file,
                        b_check_conflict,
                    )

    def test_normalise_api_push_md5_file(self)->None:
        """test de __normalise_api_push_md5_file"""
        # pas d"upload
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(None)
        p_path= Path("a")
        s_nom = "a"
        with self.assertRaises(GpfSdkError) as o_err:
            o_ua.normalise_api_push_md5_file(p_path, s_nom)
        self.assertEqual(f"Aucune livraison de définie - impossible de livrer {s_nom}", o_err.exception.message)

        # un upload
        o_mock_upload=MagicMock()
        o_ua.set_upload(o_mock_upload)
        o_ua.normalise_api_push_md5_file(p_path, s_nom)
        o_mock_upload.api_push_md5_file.assert_called_once_with(p_path)



    def run_push_files(self, i_file_err_uploaded, i_file_uploaded, i_files_upload)->None:
        """lancement de test de __push_files dans raise au push"""

        # upload, rien déjà livrer pas de conflict ou timeout sans check_conflict
        o_mock_upload=MagicMock()
        o_mock_upload.api_tree.return_value = []
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(o_mock_upload)
        l_file_err_uploaded=[]
        for i in range(i_file_err_uploaded):
            o_mock = MagicMock()
            o_mock.stat().st_size = 50
            o_mock.name=f"err_uploaded_{i}"
            l_file_err_uploaded.append(o_mock)
        l_file_uploaded =[]
        for i in range(i_file_uploaded):
            o_mock = MagicMock()
            o_mock.stat().st_size = 10
            o_mock.name=f"uploaded_{i}"
            l_file_uploaded.append(o_mock)
        d_destination_taille = {f"base/{l_file.name}" : 10 for l_file in l_file_err_uploaded + l_file_uploaded}
        l_files_upload = []
        for i in range(i_files_upload):
            o_mock = MagicMock()
            o_mock.stat().st_size = 10
            o_mock.name=f"upload_{i}"
            l_files_upload.append(o_mock)
        l_files = [(o_mock, "base") for o_mock in  l_files_upload+l_file_err_uploaded+ l_file_uploaded]
        with patch.object(UploadAction, "parse_tree", return_value=d_destination_taille) as o_mock_parse_tree:
            with patch.object(UploadAction, "_UploadAction__check_file_uploaded") as o_mock_check_file:

                i=o_ua.push_files(l_files, o_mock_upload.push, o_mock_upload.delete, check_conflict=False)
                # récupération de l'arborescence
                o_mock_upload.api_tree.assert_called_once_with()
                o_mock_parse_tree.assert_called_once_with([])
                # suppression
                self.assertEqual(len(l_file_err_uploaded), o_mock_upload.delete.call_count)
                for o_file in l_file_err_uploaded:
                    o_mock_upload.delete.assert_any_call(f"base/{o_file.name}")
                # upload
                self.assertEqual(len(l_files_upload+l_file_err_uploaded), o_mock_upload.push.call_count)
                for o_file in l_files_upload+l_file_err_uploaded:
                    o_mock_upload.push.assert_any_call(o_file, "base")
                self.assertEqual(len(l_files_upload+l_file_err_uploaded), i)
                o_mock_check_file.assert_not_called()





    def test_push_files(self)->None:
        """test de __push_files"""
        # pas d'upload
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(None)
        with self.assertRaises(GpfSdkError) as o_err:
            o_ua.push_files([], MagicMock(), MagicMock())
        self.assertEqual("Aucune livraison de définie", o_err.exception.message)

        # push sans erreur
        for i_file_err_uploaded in [0,4]:
            for i_file_uploaded in [0,4]:
                for i_files_upload in [0,4]:
                    self.run_push_files(i_file_err_uploaded, i_file_uploaded, i_files_upload)

        for e_push_side_effect in [ConflictError("", "", {}, {}, ''), requests.Timeout(request=None, response=None)]:
            # conflict lors du push, pas de vérifications
            o_mock_upload=MagicMock(**{"api_tree.return_value" : [], "push.side_effect": e_push_side_effect})
            o_ua = UploadActionNoPrivate(MagicMock())
            o_ua.set_upload(o_mock_upload)
            l_files_upload = [MagicMock(**{"name": f"upload_{i}"}) for i in range(4)]
            l_files = [(o_mock, f"base/{o_mock.name}") for o_mock in  l_files_upload]
            with patch.object(UploadAction, "parse_tree", return_value={}) as o_mock_parse_tree:
                with patch.object(UploadAction, "_UploadAction__check_file_uploaded") as o_mock_check_file:
                    i=o_ua.push_files(l_files, o_mock_upload.push, o_mock_upload.delete, check_conflict=False)
                    # récupération de l'arborescence
                    o_mock_upload.api_tree.assert_called_once_with()
                    o_mock_parse_tree.assert_called_once_with([])
                    # suppression
                    o_mock_upload.delete.assert_not_called()
                    # upload
                    self.assertEqual(len(l_files_upload), o_mock_upload.push.call_count)
                    for o_file in l_files_upload:
                        o_mock_upload.push.assert_any_call(o_file, f"base/{o_file.name}")
                    self.assertEqual(0, i)
                    o_mock_check_file.assert_not_called()
            # conflict lors du push, avec vérifications ok
            o_mock_upload=MagicMock(**{"api_tree.return_value" : [], "push.side_effect": e_push_side_effect})
            o_ua = UploadActionNoPrivate(MagicMock())
            o_ua.set_upload(o_mock_upload)
            l_files_upload = [MagicMock(**{"name": f"upload_{i}"}) for i in range(4)]
            l_files = [(o_mock, f"base/{o_mock.name}") for o_mock in  l_files_upload]
            with patch.object(UploadAction, "parse_tree", return_value={}) as o_mock_parse_tree:
                with patch.object(UploadAction, "_UploadAction__check_file_uploaded", return_value=[]) as o_mock_check_file:
                    i=o_ua.push_files(l_files, o_mock_upload.push, o_mock_upload.delete, check_conflict=True)
                    # récupération de l'arborescence
                    o_mock_upload.api_tree.assert_called_once_with()
                    o_mock_parse_tree.assert_called_once_with([])
                    # suppression
                    o_mock_upload.delete.assert_not_called()
                    # upload
                    self.assertEqual(len(l_files_upload), o_mock_upload.push.call_count)
                    for o_file in l_files_upload:
                        o_mock_upload.push.assert_any_call(o_file, f"base/{o_file.name}")
                    self.assertEqual(0, i)
                    o_mock_check_file.assert_called_once_with(l_files)
            # conflict lors du push, avec vérifications ko
            o_mock_upload=MagicMock(**{"api_tree.return_value" : [], "push.side_effect": e_push_side_effect})
            o_ua = UploadActionNoPrivate(MagicMock())
            o_ua.set_upload(o_mock_upload)
            l_files_upload = [MagicMock(**{"name": f"upload_{i}"}) for i in range(4)]
            l_files = [(o_mock, f"base/{o_mock.name}") for o_mock in  l_files_upload]
            l_error=l_files[:2]
            with patch.object(UploadAction, "parse_tree", return_value={}) as o_mock_parse_tree:
                with patch.object(UploadAction, "_UploadAction__check_file_uploaded", return_value=l_error) as o_mock_check_file:
                    with self.assertRaises(UploadFileError) as o_err:
                        i=o_ua.push_files(l_files, o_mock_upload.push, o_mock_upload.delete, check_conflict=True)
                    self.assertEqual(f"Livraison {o_mock_upload['name']} : Problème de livraison pour {len(l_error)} fichiers. Il faut relancer la livraison.", o_err.exception.message)
                    self.assertEqual(l_error, o_err.exception.files)
                    # récupération de l'arborescence
                    o_mock_upload.api_tree.assert_called_once_with()
                    o_mock_parse_tree.assert_called_once_with([])
                    # suppression
                    o_mock_upload.delete.assert_not_called()
                    # upload
                    self.assertEqual(len(l_files_upload), o_mock_upload.push.call_count)
                    for o_file in l_files_upload:
                        o_mock_upload.push.assert_any_call(o_file, f"base/{o_file.name}")
                    o_mock_check_file.assert_called_once_with(l_files)

    def test_check_file_uploaded(self)->None:
        """test de __check_file_uploaded"""
        # pas d'upload
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(None)
        with self.assertRaises(GpfSdkError) as o_err:
            o_ua.check_file_uploaded([])
        self.assertEqual("Aucune livraison de définie", o_err.exception.message)

        # upload ok
        o_mock_upload=MagicMock(**{"api_tree.return_value" : []})
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(o_mock_upload)
        l_files_ok = []
        for i in range(4):
            o_mock = MagicMock(**{"name": f"ok_{i}"})
            o_mock.stat().st_size= 10
            l_files_ok.append(o_mock)
        l_files_ko = []
        for i in range(4):
            o_mock = MagicMock(**{"name": f"ko_{i}"})
            o_mock.stat().st_size= 10
            l_files_ko.append(o_mock)
        l_files_pb = [MagicMock(**{"name": f"pb_{i}"}) for i in range(4)]
        l_files = [(p_file, "base") for p_file in l_files_ok + l_files_ko + l_files_pb]
        d_tree = {f"base/{p_file.name}": 10 for p_file in l_files_ok+l_files_pb}
        with patch.object(UploadAction, "parse_tree", return_value=d_tree) as o_mock_parse_tree:
            l_err = o_ua.check_file_uploaded(l_files)
            o_mock_parse_tree.assert_called_once_with([])
            self.assertListEqual([(p_file, "base") for p_file in l_files_ko + l_files_pb], l_err)

    def test_close(self)->None:
        """test de __close"""# pas d'upload
        # upload ok
        o_mock_upload=MagicMock(**{"api_tree.return_value" : []})
        o_ua = UploadActionNoPrivate(MagicMock())
        o_ua.set_upload(o_mock_upload)
        o_ua.close()
        o_mock_upload.api_close.assert_called_once_with()


    def test_monitor_until_end_ok(self) -> None:
        """Vérifie le bon fonctionnement de monitor_until_end si à la fin c'est ok."""
        # 3 réponses possibles pour api_list_checks : il faut attendre sur les 2 premières; tout est ok sur la troisième.
        d_list_checks_wait_1 = {"asked": [{}, {}],"in_progress": [],"passed": [],"failed": []}
        d_list_checks_wait_2 = {"asked": [{}],"in_progress": [{}],"passed": [],"failed": []}
        d_list_checks_ok = {"asked": [],"in_progress": [],"passed": [{},{}],"failed": []}
        # On patch la fonction api_list_checks de l'upload
        # elle renvoie une liste avec des traitements en attente 2 fois puis une liste avec que des succès
        l_returns = [d_list_checks_wait_1, d_list_checks_wait_2, d_list_checks_ok]
        with patch.object(Upload, "api_list_checks", side_effect=l_returns) as o_mock_list_checks:
            # On instancie un Upload
            o_upload = Upload({"_id": "id_upload_monitor"})
            # On instancie un faux callback
            f_callback = MagicMock()
            f_ctrl_c = MagicMock(return_value=False)
            # On effectue le monitoring
            b_result = UploadAction.monitor_until_end(o_upload, f_callback, f_ctrl_c)
            # Vérification sur o_mock_list_checks et f_callback: ont dû être appelés 3 fois
            self.assertEqual(o_mock_list_checks.call_count, 3)
            self.assertEqual(f_callback.call_count, 3)
            f_callback.assert_any_call("Vérifications : 2 en attente, 0 en cours, 0 en échec, 0 en succès")
            f_callback.assert_any_call("Vérifications : 1 en attente, 1 en cours, 0 en échec, 0 en succès")
            f_callback.assert_any_call("Vérifications : 0 en attente, 0 en cours, 0 en échec, 2 en succès")
            # Vérification sur f_ctrl_c : n'a pas dû être appelée
            f_ctrl_c.assert_not_called()
            # Vérifications sur b_result : doit être finalement ok
            self.assertTrue(b_result)

    def test_monitor_until_end_ko(self) -> None:
        """Vérifie le bon fonctionnement de monitor_until_end si à la fin c'est ko."""
        # 3 réponses possibles pour api_list_checks : il faut attendre sur les 2 premières; il y a un pb sur la troisième.
        d_list_checks_wait_1 = {"asked": [{}, {}],"in_progress": [],"passed": [],"failed": []}
        d_list_checks_wait_2 = {"asked": [{}],"in_progress": [{}],"passed": [],"failed": []}
        d_list_checks_ko = {"asked": [],"in_progress": [],"passed": [{}],"failed": [{}]}
        # On patch la fonction api_list_checks de l'upload
        # elle renvoie une liste avec des traitements en attente 2 fois puis une liste avec des erreurs
        l_returns = [d_list_checks_wait_1, d_list_checks_wait_2, d_list_checks_ko]
        with patch.object(Upload, "api_list_checks", side_effect=l_returns) as o_mock_list_checks:
            # On instancie un Upload
            o_upload = Upload({"_id": "id_upload_monitor"})
            # On instancie un faux callback
            f_callback = MagicMock()
            f_ctrl_c = MagicMock(return_value=False)
            # On effectue le monitoring
            b_result = UploadAction.monitor_until_end(o_upload, f_callback, f_ctrl_c)
            # Vérification sur o_mock_list_checks et f_callback: ont dû être appelés 3 fois
            self.assertEqual(o_mock_list_checks.call_count, 3)
            self.assertEqual(f_callback.call_count, 3)
            f_callback.assert_any_call("Vérifications : 2 en attente, 0 en cours, 0 en échec, 0 en succès")
            f_callback.assert_any_call("Vérifications : 1 en attente, 1 en cours, 0 en échec, 0 en succès")
            f_callback.assert_any_call("Vérifications : 0 en attente, 0 en cours, 1 en échec, 1 en succès")
            # Vérification sur f_ctrl_c : n'a pas dû être appelée
            f_ctrl_c.assert_not_called()
            # Vérifications sur b_result : doit être finalement ko
            self.assertFalse(b_result)

    def test_interrupt_monitor_until_end(self) -> None:
        """Vérifie le bon fonctionnement de monitor_until_end si il y a interruption en cours de route."""
        # tout déjà traité
        with patch.object(Upload, "api_list_checks", side_effect=[KeyboardInterrupt(), {"asked":[], "in_progress": []}] ) as o_mock_list_checks:
            with patch.object(Upload, "api_open") as o_mock_api_open:
                # On instancie un Upload
                o_upload = Upload({"_id": "id_upload_monitor"})
                # On instancie un faux callback
                f_callback = MagicMock()
                f_ctrl_c = MagicMock(return_value=True)
                # On effectue le monitoring
                with self.assertRaises(KeyboardInterrupt):
                    UploadAction.monitor_until_end(o_upload, f_callback, f_ctrl_c)

            # Vérification sur les appels de fonction
            self.assertEqual(2, o_mock_list_checks.call_count)
            f_ctrl_c.assert_called_once_with()
            o_mock_api_open.assert_not_called()
        # tout traitement en cours
        with patch.object(Upload, "api_list_checks", side_effect=[KeyboardInterrupt(), {"asked":[], "in_progress": [{'_id': "1"}, {'_id': "2"}]}] ) as o_mock_list_checks:
            with patch.object(CheckExecution, "api_delete") as o_mock_delete:
                with patch.object(Upload, "api_open") as o_mock_api_open:
                    # On instancie un Upload
                    o_upload = Upload({"_id": "id_upload_monitor"})
                    # On instancie un faux callback
                    f_callback = MagicMock()
                    f_ctrl_c = MagicMock(return_value=True)
                    # On effectue le monitoring
                    with self.assertRaises(KeyboardInterrupt):
                        UploadAction.monitor_until_end(o_upload, f_callback, f_ctrl_c)

            # Vérification sur les appels de fonction
            self.assertEqual(2, o_mock_list_checks.call_count)
            self.assertEqual(2, o_mock_delete.call_count)
            f_ctrl_c.assert_called_once_with()
            o_mock_api_open.assert_called_once_with()
        # traitement en cours et en attente
        o_mock_1 = MagicMock()
        o_mock_1.__getitem__.side_effect = ["WAITING", "WAITING", "PROGRESS", "PROGRESS"]
        o_mock_1.api_update.return_value = None
        o_mock_1.api_delete.return_value = None
        o_mock_2 = MagicMock()
        o_mock_2.__getitem__.side_effect = ["WAITING", "WAITING", "FAIL", "FAIL"]
        o_mock_2.api_update.return_value = None
        o_mock_2.api_delete.return_value = None
        with patch.object(Upload, "api_list_checks", side_effect=[KeyboardInterrupt(), {"asked":[{'_id': "3"}, {'_id': "4"}], "in_progress": [{'_id': "1"}, {'_id': "2"}]}] ) as o_mock_list_checks:
            with patch.object(CheckExecution, "api_delete") as o_mock_delete:
                with patch.object(CheckExecution, "api_get", side_effect=[o_mock_1, o_mock_2]) as o_mock_get:
                    with patch.object(Upload, "api_open") as o_mock_api_open:
                        # On instancie un Upload
                        o_upload = Upload({"_id": "id_upload_monitor"}, "test")
                        # On instancie un faux callback
                        f_callback = MagicMock()
                        f_ctrl_c = MagicMock(return_value=True)
                        # On effectue le monitoring
                        with self.assertRaises(KeyboardInterrupt):
                            UploadAction.monitor_until_end(o_upload, f_callback, f_ctrl_c)

            # Vérification sur les appels de fonction
            self.assertEqual(2, o_mock_list_checks.call_count)
            self.assertEqual(2, o_mock_delete.call_count)
            self.assertEqual(2, o_mock_get.call_count)
            o_mock_get.assert_any_call("3", "test")
            o_mock_get.assert_any_call("4", "test")
            f_ctrl_c.assert_called_once_with()
            o_mock_api_open.assert_called_once_with()
            self.assertEqual(2, o_mock_1.api_update.call_count)
            self.assertEqual(2, o_mock_2.api_update.call_count)
            o_mock_1.api_delete.assert_called_once_with()
            o_mock_2.api_delete.assert_not_called()

    def test_api_tree_not_empty(self) -> None:
        """Vérifie le bon fonctionnement de api_tree si ce n'est pas vide."""
        # Arborescence en entrée
        l_tree: List[Dict[str, Any]] = [
            {
                "name": "data",
                "children": [
                    {
                        "name": "toto",
                        "children": [
                            {
                                "name": "titi",
                                "children": [
                                    {
                                        "name": "fichier_2.pdf",
                                        "size": 467717,
                                        "extension": ".pdf",
                                        "type": "file",
                                    }
                                ],
                                "size": 467717,
                                "type": "directory",
                            },
                            {
                                "name": "fichier_1.pdf",
                                "size": 300000,
                                "extension": ".pdf",
                                "type": "file",
                            },
                        ],
                        "size": 767717,
                        "type": "directory",
                    }
                ],
                "size": 767717,
                "type": "directory",
            },
            {"name": "md5sum.md5", "size": 78, "extension": ".md5", "type": "file"},
        ]
        # Valeurs attendues
        d_files_wanted: Dict[str, int] = {
            "data/toto/titi/fichier_2.pdf": 467717,
            "data/toto/fichier_1.pdf": 300000,
            "md5sum.md5": 78,
        }
        # Parsing
        d_files = UploadAction.parse_tree(l_tree)
        # Vérification
        self.assertDictEqual(d_files, d_files_wanted)

    def test_api_tree_empty(self) -> None:
        """Vérifie le bon fonctionnement de api_tree si c'est vide."""
        # Arborescence en entrée
        l_tree: List[Dict[str, Any]] = []
        # Valeurs attendues
        d_files_wanted: Dict[str, int] = {}
        # Parsing
        d_files = UploadAction.parse_tree(l_tree)
        # Vérification
        self.assertDictEqual(d_files, d_files_wanted)
