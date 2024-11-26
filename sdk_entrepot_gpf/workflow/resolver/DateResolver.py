from datetime import datetime
import re
from typing import Any, Pattern
from dateutil.relativedelta import relativedelta

from sdk_entrepot_gpf.workflow.resolver.AbstractResolver import AbstractResolver
from sdk_entrepot_gpf.io.Config import Config
from sdk_entrepot_gpf.workflow.resolver.Errors import ResolverError


class DateResolver(AbstractResolver):
    """Classe permettant de résoudre une date.

    Attributes:
        __name (str): nom de code du resolver
    """

    def __init__(self, name: str) -> None:
        """À l'instanciation, le résolveur est nommé selon ce qui est indiqué dans la Config.

        Args:
            name (str): nom du résolveur
        """
        super().__init__(name)
        self.__regex: Pattern[str] = re.compile(Config().get_str("workflow_resolution_regex", "date_regex"))
        self.__datetime_pattern: str = Config().get_str("workflow_resolution_regex", "datetime_pattern")
        self.__date_pattern: str = Config().get_str("workflow_resolution_regex", "date_pattern")
        self.__time_pattern: str = Config().get_str("workflow_resolution_regex", "time_pattern")

    def resolve(self, string_to_solve: str, **kwargs: Any) -> str:
        """Résolution bête : on retourne la chaîne à résoudre.

        Args:
            string_to_solve (str): chaîne à résoudre.
            kwargs (Any): paramètres supplémentaires.

        Returns:
            str: chaîne résolue
        """

        # On parse la chaîne à résoudre
        o_result = self.__regex.search(string_to_solve)
        if o_result is None:
            raise ResolverError(self.name, string_to_solve)
        d_groups = o_result.groupdict()

        # date de référence
        if d_groups["date"] == "now":
            o_date = datetime.now()
        else:
            raise ResolverError(self.name, string_to_solve)
        # print(string_to_solve, d_groups["add_param"])
        # ajout si besoin (nom négatif accepté)
        if "add_param" in d_groups and d_groups["add_param"]:
            # récupération des valeur à ajouter
            d_add_info = {s.split("=")[0].strip(): int(s.split("=")[1]) for s in d_groups["add_param"].split(",")}
            # création et ajout du delta
            o_date += relativedelta(
                years=d_add_info.get("years", d_add_info.get("year", 0)),
                months=d_add_info.get("months", d_add_info.get("month", 0)),
                days=d_add_info.get("days", d_add_info.get("day", 0)),
                hours=d_add_info.get("hours", d_add_info.get("hour", 0)),
                minutes=d_add_info.get("minutes", d_add_info.get("minute", 0)),
                weeks=d_add_info.get("weeks", d_add_info.get("week", 0)),
                seconds=d_add_info.get("seconds", d_add_info.get("second", 0)),
            )

        # passage de la date en texte avec le bon pattern
        if d_groups["output"] == "date":
            return o_date.strftime(self.__date_pattern)
        if d_groups["output"] == "time":
            return o_date.strftime(self.__time_pattern)
        if d_groups["output"] == "datetime":
            return o_date.strftime(self.__datetime_pattern)
        if d_groups["output"].startswith("strtime"):
            return o_date.strftime(d_groups["output_pattern"])

        # pattern de sortie non gérer
        raise ResolverError(self.name, string_to_solve)
