declare -i code=0

# Lancement de pylint
pylint --rcfile=.pylintrc --disable=fixme sdk_entrepot_gpf --recursive=y
code+=$?
pylint --rcfile=.pylintrc --disable=fixme tests --recursive=y
code+=$?
echo

# Lancement de black
black sdk_entrepot_gpf tests
code+=$?
echo

# Lancement de mypy
mypy --strict --config-file mypy.ini sdk_entrepot_gpf tests
code+=$?
echo

# Lancement des tests et vérification de la couverture
coverage run -m unittest discover -b -p *TestCase.py
code+=$?
coverage report -m --skip-covered --fail-under=75
code+=$?
coverage html

# Affichage synthétique
if [ $code -eq 0 ]
then
    printf "\n\033[0;32mOK\033[0m\n";
else
    printf "\n\033[0;31mKO\033[0m\n";
fi

# Retour
exit $code
