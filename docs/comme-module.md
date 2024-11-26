<!--
CE DOCUMENT N'A PAS VOCATION A ÊTRE LU DIRECTEMENT OU VIA GITHUB :
les liens seront cassés, l'affichage ne sera pas correcte. Ne faites ça !

Consultez la doc en ligne ici : https://geoplateforme.github.io/sdk-entrepot/

Le lien vers cette page devrait être : https://geoplateforme.github.io/sdk-entrepot/comme-module/
-->

# Utilisation comme module Python

## Configuration

Afin d'utiliser cette librairie comme module, vous devrez [écrire un fichier de configuration](configuration.md) comme pour les autres utilisations.

Ce fichier devra être chargé au début de votre script grâce à la classe `Config` :

```py
# Importation de la classe Config
from sdk_entrepot_gpf.io.Config import Config

# Chargement de mon fichier de config
Config().read("config.ini")
```

## Livraison de données

### Avec la classe `UploadAction`

Pour livrer des données, vous pouvez utiliser les [fichiers descripteurs de livraison](upload_descriptor.md) et appeler la classe `UploadAction`.
Cela sera plus simple d'un point de vue Python mais moins modulaire.

Voici un exemple de code Python permettant de le faire (à lancer après le chargement de la config !) :

```py
# Importation des classes UploadDescriptorFileReader et UploadAction
from sdk_entrepot_gpf.io.UploadDescriptorFileReader import UploadDescriptorFileReader
from sdk_entrepot_gpf.workflow.action.UploadAction import UploadAction

# Instanciation d'une UploadDescriptorFileReader
descriptor_file_reader = UploadDescriptorFileReader(p_descriptor)

# Instanciation d'une UploadAction à partir du Reader
o_upload_action = UploadAction(o_dataset, behavior=s_behavior)
# On crée la livraison
o_upload = o_upload_action.run()
# On ferme la livraison et on monitore les exécutions de vérification
b_status = UploadAction.monitor_until_end(o_upload, Livraison.callback_check)
```

???+ note "Utiliser un datastore spécifique**
    Vous pouvez préciser l'id d'un autre datastore s'il ne faut pas utiliser celui indiqué en configuration :

```py
# On crée la livraison en précisant un datastore spécifique
o_upload = o_upload_action.run(datastore='id-datastore-spécifique')
```

### Sans la classe `UploadAction`

Si vous souhaitez livrer les données de manière plus flexible, vous pouvez également utiliser directement la classe `Upload` pour créer, compléter et fermer votre livraison.

Voici un exemple de code Python permettant de le faire (à lancer après le chargement de la config !) :

```py
from pathlib import Path
# Importation de la classe Upload
from sdk_entrepot_gpf.store.Upload import Upload

# Attributs pour créer ma livraison (cf. la documentation)
# https://data.geopf.fr/api/swagger-ui/index.html#/Livraisons%20et%20vérifications/create
info = {
  "name": "Nom de la livraison à créer",
  "description": "Description de la livraison à créer",
  "type": "VECTOR",
  "srs": "EPSG:2154",
}

# Création d'une livraison
upload = Upload.api_create(info)

# Ajout des informations complémentaires (commentaires et étiquettes)
upload.api_add_comment({"text": "mon commentaire"})
upload.api_add_tags({"tag1": "valeur1", "tag2": "valeur2"})

# Téléversement des fichiers
# Listes des fichiers : chemin local -> chemin distant
files = {Path('mon_fichier.zip') : 'chemin/api/'}
# Pour chaque fichier
for local_path, api_path in files.items():
    # On le téléverse en utilisant la méthode api_push_data_file
    upload.api_push_data_file(local_path, api_path)

# Téléversement des fichiers md5
upload.api_push_md5_file(Path('checksum.md5'))

# Fermeture de la livraison
upload.api_close()
```

???+ note "Utiliser un datastore spécifique**
    Vous pouvez préciser l'id d'un autre datastore s'il ne faut pas utiliser celui indiqué en configuration :

```py
# Création d'une livraison en précisant un datastore spécifique
upload = Upload.api_create(info, datastore='id-datastore-spécifique')
```


## Traitement et publications des données

D'un point de vue API Entrepôt, pour traiter et publier des données, vous allez créer :

* des exécutions de traitement (`processing execution`) ;
* des configurations (`configuration`) ;
* des offres (`offering`).

Avec ce SDK, vous pouvez le faire en manipulant des workflows ou directement en manipulant les classes ProcessingExecution, Configuration et Offering.

La première méthode est plus simple (et généreusement configurable !), la seconde méthode sera plus complexe mais très flexible.

### En utilisant des workflows

On part ici du principe que vous avez déjà écrit [votre workflow](workflow.md).

```py
# Importation de la classe JsonHelper
from sdk_entrepot_gpf.helper.JsonHelper import JsonHelper
# Importation des classes Workflow, GlobalResolver et StoreEntityResolver
from sdk_entrepot_gpf.workflow.Workflow import Workflow
from sdk_entrepot_gpf.workflow.resolver.GlobalResolver import GlobalResolver
from sdk_entrepot_gpf.workflow.resolver.StoreEntityResolver import StoreEntityResolver
```

La première étape consiste à charger le fichier de workflow et à instancier la classe associée. Vous pouvez utiliser notre classe de lecture JSON qui gère les fichier `.jsonc` (c'est à dire avec des commentaires).

```py
p_workflow = Path("mon_workflow.jsonc").absolute()
o_workflow = Workflow(p_workflow.stem, JsonHelper.load(p_workflow))
```

*Rédaction en cours...*
