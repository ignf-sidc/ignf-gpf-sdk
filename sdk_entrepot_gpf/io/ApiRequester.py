from __future__ import unicode_literals

import re
import time
import traceback
from io import BufferedReader
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Union
import requests
from requests_toolbelt import MultipartEncoder

from sdk_entrepot_gpf.Errors import GpfSdkError
from sdk_entrepot_gpf.auth.Authentifier import Authentifier
from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper
from sdk_entrepot_gpf.pattern.Singleton import Singleton
from sdk_entrepot_gpf.io.JsonConverter import JsonConverter
from sdk_entrepot_gpf.io.Errors import ApiError, ConflictError, RouteNotFoundError, InternalServerError, NotFoundError, NotAuthorizedError, BadRequestError, StatusCodeError
from sdk_entrepot_gpf.io.Config import Config


class ApiRequester(metaclass=Singleton):
    """Classe singleton pour gérer l'enrobage des requêtes à l'API GPF : gestion du proxy, du HTTPS et des erreurs."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

    regex_content_range = re.compile(Config().get_str("store_api", "regex_content_range"))

    def __init__(self) -> None:
        # Récupération du convertisseur Json
        self.__jsonConverter = JsonConverter()
        self.__nb_attempts = Config().get_int("store_api", "nb_attempts")
        self.__sec_between_attempt = Config().get_int("store_api", "sec_between_attempt")
        # Récupération des paramètres du proxy
        self.__proxy = {
            "http": Config().get_str("store_api", "http_proxy"),
            "https": Config().get_str("store_api", "https_proxy"),
        }

    def route_request(
        self,
        route_name: str,
        route_params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        files: Optional[Dict[str, Tuple[str, BufferedReader]]] = None,
        timeout: Optional[int] = -1000,
    ) -> requests.Response:
        """Exécute une requête à l'API à partir du nom d'une route. La requête est retentée plusieurs fois s'il y a un problème.

        Args:
            route_name (str): Route à utiliser
            route_params (Optional[Dict[str, Any]], optional): Paramètres obligatoires pour compléter la route.
            params (Optional[Dict[str, Any]], optional): Paramètres optionnels de l'URL.
            method (str, optional): méthode de la requête.
            data (Optional[Dict[str, Any]], optional): Données de la requête.
            files (Optional[Dict[str, Tuple[Any]]], optional): Liste des fichiers à envoyer {"file":('fichier.ext', File)}.
            timeout (Optional[int], optional): timeout en seconde ou None pour désactiver le timeout.

        Raises:
            RouteNotFoundError: levée si la route demandée n'est pas définie dans les paramètres
            InternalServerError: levée si erreur interne de l'API
            NotFoundError: levée si l'entité demandée n'est pas trouvée par l'API
            NotAuthorizedError: levée si l'action effectuée demande d'autres autorisations
            BadRequestError: levée si la requête envoyée n'est pas correcte
            StatusCodeError: levée si un "status code" non prévu est récupéré

        Returns:
            réponse vérifiée
        """
        Config().om.debug(f"route_request(route={route_name}, route_params={route_params})")

        # gestion timeout
        if timeout and timeout < 0:
            s_timeout = Config().get("routing", f"{route_name}_timeout", "-1000")
            timeout = None if not s_timeout or s_timeout == "null" else int(s_timeout)

        # La valeur par défaut est transformée en un dict valide
        if route_params is None:
            route_params = {}

        # Si la clef 'datastore' n'est pas définie ou vide, on le récupère dans la config
        if not route_params.get("datastore", None):
            route_params["datastore"] = Config().get("store_api", "datastore", fallback=None)

        # Si la clef est toujours None ou vide, on affiche un warning
        if not route_params.get("datastore", None):
            Config().om.warning("Le datastore (entrepôt) à utiliser n'est pas défini. Consultez l'aide pour corriger ce problème.")

        # On convertie les données Python en text puis en JSON
        data = self.__jsonConverter.convert(data)

        # On récupère la route
        s_route = Config().get("routing", route_name, fallback=None)
        if s_route is None:
            raise RouteNotFoundError(route_name)
        # On formate l'URL
        s_url = s_route.format(**route_params)

        # récupération du header additionnel
        s_header = Config().get("routing", route_name + "_header", fallback=None)
        d_header = {}
        if s_header is not None:
            d_header = JsonHelper.loads(s_header, f"config.routing.{route_name}_header")

        # Exécution de la requête en boucle jusqu'au succès (ou erreur au bout d'un certains temps)
        return self.url_request(s_url, method, params, data, files, d_header, timeout)

    def url_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        files: Optional[Dict[str, Tuple[str, BufferedReader]]] = None,
        header: Dict[str, str] = {},
        timeout: Optional[int] = -1000,
    ) -> requests.Response:
        """Effectue une requête à l'API à partir d'une url. La requête est retentée plusieurs fois s'il y a un problème.

        Args:
            url (str): url absolue de la requête
            method (str, optional): méthode de la requête
            params (Optional[Dict[str, Any]], optional): paramètres de la requête (ajouté à l'url)
            data (Optional[Union[Dict[str, Any], List[Any]]], optional): contenue de la requête (ajouté au corp)
            files (Optional[Dict[str, Tuple[Any]]], optional): fichiers à envoyer
            header (Dict[str, str], optional): Header additionnel pour la requête
            timeout (Optional[int], optional): timeout en seconde ou None pour désactiver le timeout.

        Returns:
            réponse si succès
        """

        # gestion timeout
        if timeout and timeout < 0:
            s_timeout = Config().get("store_api", "timeout")
            timeout = None if not s_timeout or s_timeout == "null" else int(s_timeout)

        i_nb_attempts = 0
        while True:
            i_nb_attempts += 1
            try:
                # On fait la requête
                return self.__url_request(url, method, params=params, data=data, files=files, header=header, timeout=timeout)

            except (requests.HTTPError, requests.URLRequired) as e_error:
                # S'il y a une erreur d'URL, on ne retente pas, on indique de contacter le support
                s_message = "L'URL indiquée en configuration est invalide ou inexistante. Contactez le support."
                raise GpfSdkError(s_message) from e_error

            except BadRequestError as e_error:
                # S'il y a une erreur de requête incorrecte, on ne retente pas, on indique de contacter le support
                s_message = f"La requête formulée par le programme est incorrecte ({e_error.message}). Contactez le support."
                raise GpfSdkError(s_message) from e_error

            except (ConflictError, NotFoundError, requests.Timeout) as e_error:
                # S'il y a un conflit, un 404 ou un timeout, on ne retente pas, on ne fait rien. On propage l'erreur.
                raise e_error

            except (ApiError, requests.RequestException) as e_error:
                # Pour les autres erreurs, on retente selon les paramètres indiqués.
                # On récupère la classe de l'erreur histoire que ce soit plus parlant...
                s_title = e_error.__class__.__name__
                Config().om.warning(f"L'exécution d'une requête a échoué (tentative {i_nb_attempts}/{self.__nb_attempts})... ({s_title})")
                # Affiche la pile d'exécution
                Config().om.debug(traceback.format_exc())
                # Une erreur s'est produite : attend un peu et relance une nouvelle fois la fonction
                if i_nb_attempts < self.__nb_attempts:
                    time.sleep(self.__sec_between_attempt)
                # Le nombre de tentatives est atteint : comme dirait Jim, this is the end...
                else:
                    s_message = f"L'exécution d'une requête a échoué après {i_nb_attempts} tentatives."
                    raise GpfSdkError(s_message) from e_error

    def __url_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        files: Optional[Dict[str, Tuple[str, BufferedReader]]] = None,
        header: Dict[str, str] = {},
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Effectue une requête à l'API à partir d'une url. Ne retente pas plusieurs fois si problème.

        Args:
            url (str): url absolue de la requête
            method (str, optional): méthode de la requête.
            params (Optional[Dict[str, Any]], optional): paramètres.
            data (Optional[Union[Dict[str, Any], List[Any]]], optional): données.
            files (Optional[Dict[str, Tuple[Any]]], optional): fichiers.
            header (Dict[str, str], optional): Header additionnel pour la requête.
            timeout (Optional[int], optional): timeout en seconde ou None pour désactiver le timeout.

        Returns:
            réponse si succès
        """
        Config().om.debug(f"__url_request(url={url}, method={method}, params={params}, data={data}, timeout={timeout})")

        # Définition du header
        d_headers = Authentifier().get_http_header(json_content_type=files is None)
        d_headers.update(header)

        # Création du MultipartEncoder (cf. https://github.com/requests/toolbelt#multipartform-data-encoder)
        d_requests: Dict[str, Any] = {
            "url": url,
            "method": method,
            "headers": d_headers,
            "proxies": self.__proxy,
            "params": params,
            "timeout": timeout,
        }
        if files:
            d_fields = {**files}
            o_me = MultipartEncoder(fields=d_fields)
            d_headers["content-type"] = o_me.content_type
            # Execution de la requête
            d_requests.update({"data": o_me})
        else:
            d_requests.update({"params": params, "json": data})

        # exécution de la requête
        r = requests.request(**d_requests)

        # Vérification du résultat...
        if r.status_code >= 200 and r.status_code < 300:
            # Si c'est ok, on renvoie la réponse
            return r
        # Erreur sans retour attendu/possible
        if r.status_code == 500:
            # Erreur interne (pas de retour)
            raise InternalServerError(url, method, params, data)
        # Erreurs avec retour attendu/possible
        if r.status_code == 404:
            # Element non trouvé (pas de retour)
            raise NotFoundError(url, method, params, data, r.text)
        if r.status_code in (403, 401):
            # Action non autorisée
            Authentifier().revoke_token()  # On révoque le token
            raise NotAuthorizedError(url, method, params, data, r.text)
        if r.status_code == 400:
            # Requête incorrecte
            raise BadRequestError(url, method, params, data, r.text)
        if r.status_code == 409:
            # Conflit
            raise ConflictError(url, method, params, data, r.text)
        # Autre erreur
        raise StatusCodeError(url, method, params, data, r.status_code, r.text)

    def route_upload_file(
        self,
        route_name: str,
        file_path: Path,
        file_key: str,
        route_params: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[int] = -1000,
    ) -> requests.Response:
        """Exécute une requête à l'API à partir du nom d'une route. La requête est retentée plusieurs fois s'il y a un problème.

        Args:
            route_name (str): Route à utiliser
            file_path (Path): Chemin du fichier à uploader
            file_key (str): nom de la clef dans le dictionnaire
            route_params (Optional[Dict[str, Any]], optional): Paramètres obligatoires pour compléter la route.
            params (Optional[Dict[str, Any]], optional): Paramètres optionnels de l'URL.
            method (str, optional): méthode de la requête.
            data (Optional[Dict[str, Any]], optional): Données de la requête.

        Returns:
            réponse vérifiée
        """

        # gestion timeout
        if timeout and timeout < 0:
            s_timeout = Config().get("routing", f"{route_name}_timeout", "-1000")
            if not s_timeout or s_timeout.lower() == "null" or s_timeout.lower() == "none":
                # timeout directe ou None (pas de timeout)
                timeout = None
            elif re.search(r"^ *-? *\d+ *$", s_timeout):
                timeout = int(s_timeout)
            else:
                # timeout selon la taille du fichier
                d_timeout_dict: Dict[str, Optional[int]] = dict(JsonHelper.loads(s_timeout, "du dictionnaire des timeout pour {route_name}"))
                # on rajoute une valeur par défaut
                d_timeout_dict["-1000"] = -1000
                i_index_timeout = max(int(i) for i in d_timeout_dict if int(i) <= file_path.stat().st_size)
                timeout = d_timeout_dict[str(i_index_timeout)]

        if timeout and timeout < 0:
            s_default_timeout = Config().get("store_api", "timeout")
            timeout = None if not s_default_timeout or s_default_timeout == "null" else int(s_default_timeout)

        # Ouverture du fichier et remplissage du tuple de fichier
        with file_path.open("rb") as o_file_binary:
            o_tuple_file = (file_path.name, o_file_binary)
            o_dict_files = {file_key: o_tuple_file}

            # Requête
            return self.route_request(route_name, route_params=route_params, method=method, params=params, data=data, files=o_dict_files, timeout=timeout)

    @staticmethod
    def range_next_page(content_range: Optional[str], length: int) -> bool:
        """Fonction analysant le `Content-Range` d'une réponse pour indiquer s'il
        faut faire d'autres requêtes ou si tout est déjà récupéré.

        Args:
            content_range (Optional[str]): Content-Range renvoyé par l'API
            length (int): nombre d'éléments déjà récupérés

        Returns:
            True s'il faut continuer, False sinon
        """
        # On regarde le Content-Range de la réponse pour savoir si on doit refaire une requête pour récupérer la fin
        if content_range is None:
            # S'il n'est pas renseigné, on arrête là
            return False
        # Sinon on tente de le parser
        o_result = ApiRequester.regex_content_range.search(content_range)
        if o_result is None:
            # Si le parsing a raté, on met un warning en on s'arrête là niveau requête
            Config().om.warning(f"Impossible d'analyser le nombre d'éléments à requêter. Contactez le support. (Content-Range : {content_range})")
            return False
        # Sinon, on compare la len indiquée par le serveur à celle de notre liste, si c'est égal ou supérieur on arrête
        return not length >= int(o_result.group("len"))
