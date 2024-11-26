from datetime import datetime
from unittest.mock import patch
from dateutil.relativedelta import relativedelta

from sdk_entrepot_gpf.workflow.resolver.DateResolver import DateResolver
from sdk_entrepot_gpf.workflow.resolver.Errors import ResolverError
from tests.GpfTestCase import GpfTestCase


class DateResolverTestCase(GpfTestCase):
    """Tests DateResolver class.

    cmd : python3 -m unittest -b tests.workflow.resolver.DateResolverTestCase
    """

    def test_resolve(self) -> None:
        """Vérifie le bon fonctionnement de la fonction resolve."""
        # on force la configuration de la date
        # TODO

        # date actuelle que l'on utilisera
        o_date = datetime.now()

        # Instanciation du résolveur
        o_resolver = DateResolver("4t")

        d_data = {
            # date actuel
            "now.date": o_date.strftime("%d/%m/%Y"),
            "now.time": o_date.strftime("%H:%M"),
            "now.datetime": o_date.strftime("%d/%m/%Y %H:%M"),
            "now.strtime(%Y-%m-%dT%H:%M:%S)": o_date.strftime("%Y-%m-%dT%H:%M:%S"),
            # add/remove
            "now.add(year=1,month=2,day=3,hour=4,minute=5).datetime": (o_date + relativedelta(years=1, months=2, days=3, hours=4, minutes=5)).strftime("%d/%m/%Y %H:%M"),
            "now.add(year=-1,minute=-5,month=2,day=3,hour=4).datetime": (o_date + relativedelta(years=-1, months=2, days=3, hours=4, minutes=-5)).strftime("%d/%m/%Y %H:%M"),
            "now.add(year=-1,month=2).datetime": (o_date + relativedelta(years=-1, months=2)).strftime("%d/%m/%Y %H:%M"),
            "now.add(weeks=2).datetime": (o_date + relativedelta(weeks=2)).strftime("%d/%m/%Y %H:%M"),
        }
        # test en mode réussite (avec toutes les clefs/valeurs de notre dict)
        ## on fixe la date
        with patch("sdk_entrepot_gpf.workflow.resolver.DateResolver.datetime") as o_mock_now:
            o_mock_now.now.return_value = o_date
            ## test de la résolution
            for k, v in d_data.items():
                self.assertEqual(o_resolver.resolve(k), v)

        # test en mode erreur (exception levée + message ok)
        ## pattern faux
        s_to_solve = "non_existant"
        with self.assertRaises(ResolverError) as o_arc:
            o_resolver.resolve(s_to_solve)
        self.assertEqual(o_arc.exception.message, f"Erreur du résolveur '4t' avec la chaîne '{s_to_solve}'.")
