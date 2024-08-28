# Utilisation comme exécutable

## Configuration

Pensez à [créer un fichier de configuration](configuration.md) indiquant au minimum vos identifiants.

## Vérification de la configuration

Un bon moyen de vérifier que la configuration est correcte est de s'authentifier via l'exécutable (commande `auth`) :

```sh
# Le fichier de configuration est directement trouvé s'il est
# nommé "config.ini" et qu'il est situé dans le dossier de travail
python -m sdk_entrepot_gpf auth
# Sinon indiquez son chemin
python -m sdk_entrepot_gpf --ini /autre/chemin/config.ini auth
```

Cela devrait renvoyer :

``` txt
Authentification réussie.
```

## Mes datastores

Dans la configuration, vous devez indiquer l'identifiant du datastore à utiliser.

Si vous ne le connaissez pas, il est possible de lister les communautés auxquelles vous participez et, pour chacune d'elles, le datastore qui lui est associé.

La commande `me` permet de lister les communautés auxquelles vous appartenez :

```sh
python -m sdk_entrepot_gpf me
```

Cela devrait renvoyer :

```txt
Vos informations :
  * email : prenom.nom@me.io
  * nom : Prénom Nom
  * votre id : 11111111111111111111

Vous êtes membre de 1 communauté(s) :

  * communauté « Bac à sable » :
      - id de la communauté : 22222222222222222222
      - id du datastore : 33333333333333333333
      - nom technique : bac-a-sable
      - droits : community, uploads, processings, datastore, stored_data, broadcast
```

Dans cet exemple, l'identifiant du datastore à utiliser est `33333333333333333333`.

> [!WARNING]
> Cela ne fonctionnera que si les autres paramètres (nom d'utilisateur, mot de passe et urls) sont corrects.

## Afficher toute la configuration

Vous pouvez afficher toute la configuration via une commande. Cela peut vous permettre d'avoir une liste exhaustive des paramètres disponibles et de vérifier que votre fichier de configuration a bien le dernier mot sur les paramètres à utiliser.

Affichez la configuration (commande `config`) :

```sh
# Toute la configuration
python -m sdk_entrepot_gpf config
# Une section
python -m sdk_entrepot_gpf config -s store_authentification
# Une option d'une section
python -m sdk_entrepot_gpf config -s store_authentification -o password
```

## Récupérer des jeux de données d'exemple

Il est possible de récupérer des jeux de données d'exemple via l'exécutable avec la commande `dataset`.

Lancez la commande `dataset` sans paramètre pour lister les jeux disponibles :

```sh
python -m sdk_entrepot_gpf dataset
```

Lancez la commande `dataset` en précisant le nom (`-n`) du jeu de données à extraire pour récupérer un jeu de données :

```sh
python -m sdk_entrepot_gpf dataset -n 1_dataset_vector
```

Les données seront extraites dans le dossier courant, vous pouvez préciser la destination avec le paramètre `--folder` (ou `-f`).

## Envoyer des données

Pour envoyer des données, vous devez générer un [fichier descripteur de livraison](upload_descriptor.md).

C'est un fichier au format JSON permettant de décrire les données à livrer et les livraisons à créer.

Ensuite, vous pouvez simplement livrer des données avec la commande `upload` :

```sh
python -m sdk_entrepot_gpf upload -f mon_fichier_descripteur.json
```

Les jeux de données d'exemple sont fournis avec le fichier descripteur (voir [Récupérer des jeux de données d'exemple](#récupérer-des-jeux-de-données-dexemple)).

## Réaliser des traitements et publier des données

Pour réaliser des traitements et publier des données géographiques, vous devez générer un [fichier workflow](workflow.md).

C'est un fichier au format JSON permettant de décrire, en une suite d'étapes, les traitements et les publications à effectuer.

Vous pouvez valider votre workflow :

```sh
python -m sdk_entrepot_gpf workflow -f mon_workflow.json
```

Ensuite, vous pouvez simplement lancer une étape :

```sh
python -m sdk_entrepot_gpf workflow -f mon_workflow.json -s mon_étape
```

En lançant des workflows via l'executable du SDK, vous pouvez utiliser les 4 résolveurs suivants :

* `store_entity` : de type `StoreEntityResolver` pour récupérer des entités de l'API ;
* `user` : de type `UserResolver` pour récupérer des informations sur l'utilisateur connecté ;
* `datetime` : de type `DateResolver` pour récupérer des informations sur la date et l'heure ;
* `params` : de type `DictResolver` pour récupérer des informations arbitraires que vous aurez passé en ligne de commande (via `-p`).

Par exemple, la ligne de commande suivante :

```sh
python -m sdk_entrepot_gpf workflow -f mon_workflow.json -s mon_étape -p edition 2024-01
```

Permet d'avoir un workflow avec une gestion dynamique de l'édition traitée grâce au résolveur `params` :

```txt
{store_entity.stored_data.infos._id [INFOS(name=MES_DONNÉES_{params.edition})]}
```

## Suppression d'entités

Le programme permet de supprimer des entités de type `upload`, `stored_data`, `configuration`, `offering`, `permission` et `key`.

Avant la suppression la liste des entités supprimées sera affichée et l'utilisateur devra valider la suppression (sauf si utilisation de `--force`).

Commande générale :

```sh
python -m sdk_entrepot_gpf delete --type {upload,stored_data,configuration,offering,permission,key} --id UUID
```

Avec comme options supplémentaires :

* `--force` : aucune question ne sera posée avant la suppression
* `--cascade` : suppression des éléments liés en aval, fonctionne uniquement pour :
  * `stored_data` : suppression des configuration et offres liées
  * `configuration` : suppression des offres liées

NB : s'il y a des des éléments liés en aval et que vous ne demandez pas la suppression il sera impossible de supprimer l'élément ciblé.

Exemples :

```sh
# Suppression d'une livraison
python -m sdk_entrepot_gpf delete --type upload --id UUID
# Suppression d'une donnée stockée (sans demander confirmation, sans supprimer les éléments liés)
python -m sdk_entrepot_gpf delete --type stored_data --id UUID --force
# Suppression d'une configuration (et d'une éventuelle offre liée)
python -m sdk_entrepot_gpf delete --type configuration --id UUID --cascade
```

## Fichiers annexes

Base : `python -m sdk_entrepot_gpf annexe`

Quatre types de lancement :

* livraison d'annexes : `-f FICHIER`
* liste des annexes, avec filtre en option : `[--info filtre1=valeur1,filtre2=valeur2]`
* afficher des détails d'une annexe, avec option publication / dépublication : `--id ID [--publish|--unpublish]`
* publication / dépublication par label : `--publish-by-label label1,label2` et `--unpublish-by-label label1,label2`

Exemple de fichier pour la livraison :

```json
{
  "annexe" : [
    {
      "file": "/chemin/du/fichier.pdf",
      "paths": ["test2.xml"],
      "labels": ["label1", "label2"],
      "published": false
    }
  ]
}
```

## Fichiers statiques

Base : `python -m sdk_entrepot_gpf static`

Trois types de lancement :

* livraison de fichiers statics : `-f FICHIER`
* liste des fichiers statics, avec filtre en option : `[--info filtre1=valeur1,filtre2=valeur2]`
* afficher des détails d'un ficher statique : `--id ID`

Exemple de fichier pour la livraison :

```json
{
  "static" : [
    {
      "file": "mon_style.sld",
      "name": "mon_style",
      "type": "GEOSERVER-STYLE",
      "description": "description"
    }
  ]
}
```

## Fichiers de métadonnées

Base : `python -m sdk_entrepot_gpf metadata`

Quatre types de lancement :

* livraison d'une métadonnée : `-f FICHIER`
* liste des métadonnées, avec filtre en option : `[--info filtre1=valeur1,filtre2=valeur2]`
* afficher les détails d'une métadonnée : `--id ID`
* publication / dépublication : `--publish NOM_FICHIER [NOM_FICHIER] --id-endpoint ID_ENDPOINT` et `--unpublish NOM_FICHIER [NOM_FICHIER] --id-endpoint ID_ENDPOINT`

Exemple de fichier pour la livraison :

```json
{
  "metadata": [
    {
      "file": "metadata.xml",
      "type": "INSPIRE"
    }
  ]
}
```

## Gestion des clefs de l'utilisateur

Base : `python -m sdk_entrepot_gpf key`

Trois types de lancement :

* liste des clefs : `` (aucun paramètres)
* afficher les détails d'une clef : `--id ID`
* création de clefs : `--f FICHIER`

Exemple de fichier pour la création :

```json
{
  "key": [
    {
      "name": "nom",
      "type": "HASH",
      "type_infos": {
        "hash": "hash"
      }
    }
  ]
}

```

## Tutoriels

Vous pouvez maintenant livrer et publier vos données en utilisant le module comme un exécutable. Voici quelques exemples :

* [Tutoriel 1 : héberger une archive pour la rendre téléchargeable](tutoriel_1_archive.md)
* [Tutoriel 2 : téléverser des données vecteur les publier en flux](tutoriel_2_flux_vecteur.md)
* [Tutoriel 3 : téléverser des données raster les publier en flux](tutoriel_3_flux_raster.md)
