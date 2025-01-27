# Tutoriel : publier un flux PCRS

La Géoplateforme permet d'héberger et diffuser vos données PCRS (Plan Corps de Rue Simplifié).

Pour cela, vous devez téléverser des dalles « PCRS » qui permettront de créer une pyramide image qui sera diffusée en flux.

Vous allez avoir besoin de 3 fichiers :

* un fichier de configuration pour définir vos paramètres
* un fichier descripteur qui détaille votre livraison
* un fichier de workflow en plusieurs étapes qui effectuera les traitements

## Définition de la configuration

Vous allez devoir déposer à la racine de votre projet un fichier `config.ini` contenant les informations suivantes :

```text
# Informations pour l'authentification
[store_authentification]
# paramètres du SDK
client_id=gpf-warehouse
client_secret=BK2G7Vvkn7UDc8cV7edbCnHdYminWVw2
# Votre login
login=********
# Votre mot de passe
password=********

# Informations pour l'API
[store_api]
# L'identifiant sandbox
datastore=********
```

Il faut compléter le fichier avec votre login/mot de passe et l'identifiant du datastore qui vous a été aloué à la création de votre compte.

Vous pouvez tester la validité de votre fichier avec la commande suivante :

```text
python3 -m sdk_entrepot_gpf me
```

Il peut être nécessaire de rajouter certains paramètres pour que cela fonctionne comme le proxy. Vous pouvez suivre la page [configuration](configuration.md) pour compléter votre fichier si nécessaire.

## Fichier descripteur de livraison

Vous allez devoir créer un fichier `PCRS_descriptor.json` avec les inforamtions suivantes :

```text
{
    "datasets": [
        {
            "data_dirs": [
                "$votre_chantier_PCRS"
            ],
            "upload_infos": {
                "description": "Description de votre chantier (département, zone, date...)",
                "name": "$votre_chantier_PCRS",
                "srs": "EPSG:2154",
                "type": "RASTER"
            },
            "comments": [
                "Votre commentaire"
            ],
            "tags": {
                "datasheet_name": "$votre_chantier_PCRS",
                "type": "PCRS"
            }
        }
    ]
}
```

Il faut compléter le fichier avec `$votre_chantier_PCRS` (qui vous permettra de retrouver votre fiche de données sur cartes.gouv.fr), une description et éventuellement un commentaire.

Vous déposerez vos données dans un répertoire `$votre_chantier_PCRS` comme suit (vous pouvez ajouter un fichier md5 qui vérifiera que la livraison s'est correctement terminée) :

```text
votre_dossier/
├── $votre_chantier_PCRS
│   ├── dalle_1.tif
│   ├── dalle_2.tif
│   ├── ...
├── PCRS_chantier.md5
└── PCRS_descriptor.jsonc
```
Vous pouvez maintenant effectuer la livraison en indiquant le chemin du fichier descripteur au programme :

```sh
python -m sdk_entrepot_gpf upload -f /chemin/PCRS_descriptor.jsonc
```

Le programme doit vous indiquer que le transfert est en cours, puis qu'il attend la fin des vérification côté API avant de conclure que tout est bon (cela peut être long selon la taille de la livraison et la qualité de votre connexion).

## Workflow

Une fois les données livrées, il faut créer la pyramide image avant de la diffuser en flux (WMSRaster et WMTS).

Ces étapes sont décrites grâces à un workflow.

Vous pouvez récupérer le template du workflow grâce à la commande suivante :

```sh
python -m sdk_entrepot_gpf workflow -n PCRS.jsonc
```

Ouvrez le fichier et remplacez `$votre_chantier_PCRS` par votre valeur. Pour plus de détails, consultez la [documentation sur les workflows](workflow.md).

Le workflow `PCRS.jsonc` est composé de 2 étapes (une pour la génération de la pyramide et une pour la publication des flux). Il faudra lancer une commande pour chacune d'elles.

Les commandes à lancer sont les suivantes :

```sh
# partie génération de la pyramide
python -m sdk_entrepot_gpf workflow -f generic_raster.jsonc -s pyramide
# partie publication
python -m sdk_entrepot_gpf workflow -f generic_raster.jsonc -s publication
```

La première commande peut être longue selon le nombre de dalles livrées. Des logs doivent vous être remontés.

Avec la deuxième commande, vous pourrez récupérer les liens de vos fluxs.
