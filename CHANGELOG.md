# CHANGE LOG

## v0.1.28

### [Added]

* cli : possibilité d'ajouter des clefs-valeurs à la résolution du workflow
* Config: erreur spécifique pour les char spéciaux (`get()`, `get_str()`). #155
* Authentifier: ajout erreur spécifique pour "Account is not fully set up", mot de passe expiré. #155
* ajout classe Access : gère les accès sur les offres #97
* ajout classe AccessAction : gère les accès sur les offres depuis le workflow #95

### [Changed]

* ci : mise à jour des GitHub Actions
* ApiRequester: réduction de l'affichage #150
* EditAction : entités `Key` et `Permission` gérées
* DeleteAction : entités `Key` et `Permission` gérées
* Doc : ajout de la création des permission et des accès via workflow
* Doc : ajout des classes manquantes
* Dataset: les fichiers dans .md5 sont ordonnés dans ordre alphabétique #162

### [Fixed]

* orthographe : corrections diverses
* tag de `uniqueness_constraint_tags` non obligatoire #159

## v0.1.27

### [Added]

* ProcessingExecutionAction: ajout d'un mode reprise (`RESUME`). #143
* EditUsedDataConfigurationAction: possibilité de mise à jour de la BBox de la configuration selon les données. #140

### [Changed]

* Mise à jour de la documentation de publication d'une archive pour ajouter l'étape de patch sur la donnée stockée
* affichage des actions: harmonisation des affichages pour les actions #138
* utilisation en ligne de commande : enrichissement de l'aide.

### [Fixed]

* upload_descriptor_file.json: ajout de type_infos suite à l'ajout du paramètre dans la requête GPF. #117
* LogsInterface: récupération des logs en prenant compte de la pagination (+ refonte test api_logs). #135

## v0.1.26

### [Added]

* UploadAction: possibilité vérification totale des fichiers livrés avant de fermer la livraison #124

### [Changed]

* Plus de limitation sur le type de l'upload dans le fichier upload_descriptor, permet la livraison des nouveaux types sans mise à jour du SDK. #117
* Authentification : affichage du code TOTP en mode debug et affichage de la pile d'exécution que si l'authentification échoue complètement.

### [Fixed]

* Timeout mauvaise gestion valeur par défaut pour les upload de fichiers #125
* ajout upload_partial_edit et stored_data_partial_edit #129

## v0.1.25

### [Added]

* workflow : ajout de EditUsedDataConfigurationAction #105
* DeleteAction: meilleur gestion cas sans élément à supprimé #115
* UploadAction: les conflits de livraisons et timeout lors de la livraison ne bloquent pas la suite du traitement #119, #121
* ApiRequester: ajout de timeout #121

### [Changed]

* ajout d'une `LogsInterface` pour gérer les logs (mutualisation de `api_logs`).
* utilisation systématique de la fonction `JsonHelper.loads` (au lieu de `json.loads`) pour afficher un message d'erreur et le JSON posant problème en cas de besoin (sauf si raison particulière, à expliquer).
* UploadAction: mise en commun fonctions__push_data_files et __push_md5_files

### [Fixed]

* correction de la résolution de la valeur d'itération dans les workflows.
* OfferingAction: utilisation du bon datastore #116
* DeleteAction: debug mauvaise utilisation des filtres #114
* Configuration: création/récupération des offres avec le bon datastore

## v0.1.24

### [Added]

* StoreEntityResolver: possibilité de récupérer une liste d'entités ou d’informations sur une entité #85
* ajout classe Permission : gère les permissions sur les offres #93
* ajout classe PermissionAction : gère les permissions sur les offres depuis le workflow #94

### [Changed]

* workflow:
  * ajout de PermissionAction #94
  * possibilité d'utiliser un résolveur pour créer la liste de "Iter_vals" #106
  * possibilité de définir un datastore au niveau de l'étape

### [Fixed]

* schema workflow: ajout du type "edit-entity"
* Edit Configuration : correction de la gestion de `used_data` (#107)

## v0.1.23

### [Added]

* DateResolver: ajout d'un résolveur pour les dates #86

## v0.1.22

### [Added]

* Dans une étape d'un workflow, itération possible sur les actions. (V0, sera amélioré suite à la modification des résolveurs #87, #85)

### [Changed]

* Renommage de `CopieConfigurationAction` en `CopyConfigurationAction`

### [Fixed]

* #83 : fusion de la liste des used_data en gardant l'ordre de la liste lors de l'édition de configurations
* #80 : Upload.api_delete_data_file(): suppression exception pour répertoire "data"
* #78 : ajout route `upload_delete_data` dans la configuration
* Bug #77 : problème de nommage de l'action de copie de configuration entre le code est la doc : utilisation de `copy-configuration`
* Bug #98 : problème de datastore lors de la création d'une ProcessingExecution

## v0.1.21

### [Added]

* Résolveurs: possibilité de descendre dans les tests et les listes #87

### [Changed]

### [Fixed]

* Upload: modification de la requête suite modification de l'API GPF #54

## v0.1.20

### [Added]

* DeleteAction : suppression des upload, stored_data, configuration et offering dans un workflow #63
* EditAction : édition(modification) des upload, stored_data, configuration et offering dans un workflow (entité + tags + commentaires) #66
* CopieConfigurationAction: création d'une configuration à partir d'une configuration déjà existante #67
* Offering #58 :
    * ajout fonction Offering.api_synchronize() : synchronisation de l'offre avec la configuration
    * ajout de la fonction Offering.get_url() : récupération de la liste des urls d'une offre
    * ajout de l'action `SynchronizeOfferingAction` : synchronisation de l'offre avec la configuration depuis un workflow
* Documentation sur les [workflow](./docs/workflow.md) et les [résolveurs](./docs/resolveurs.md)

### [Changed]

* GlobalREsolver et Resolver : il est possible d'ajouter des couples clefs-valeurs dans la fonction `resolve()` de GlobalResolver et ils sont transmis aux résolveurs. Cela permet de base de résoudre la récupération d'entités (#68).
* Workflow : ajout des actions DeleteAction, EditAction, SynchronizeOfferingAction
* StoreEntity: ajout de `edit()` permettant de gérer l'édition des entités si possible. Ici impossible de mettre à jour les entités.
* PartialEditInterface: surcharge de `edit()` pour permettre l’édition partielle
* FullEditInterface: surcharge de `edit()` pour permettre l’édition complète

### [Fixed]

* #68 : le datastore est transmis au moment de la résolution ce qui corriger le problème.
* StoreEntityResolver: avant l'utilisation de l'entité, récupération de toutes ses informations
* Endpoint: neutralisation des fonctions inutilisables

## v0.1.19

### [Added]

* Classe Metadata + configuration associée et tests
* Classe DescriptorFileReader pour la livraisons des fichiers static, metadata et annexe
* Main: gestion des fichiers static, metadata et annexe (upload, liste, détail, publication et dépublication)
* Main: fonction ctrl_c_upload() pour la gestion du Ctrl+C pendant le monitoring des vérifications

### [Changed]

* Résolution des workflows :
    * `ActionAbstract` : si l'action après résolution n'est plus un JSON valide, on log le texte obtenue en niveau debug ;
    * `ActionAbstract` : on n'indente pas le JSON avant résolution
    * Regex resolver : ajout de `_` avant et après le nom du résolveur si format list ou dict.
* renommage DescriptorFileReader en UploadDescriptorFileReader
* valeur définie dans la configuration pour `client_secret` et `client_id` et mise à jour de la documentation
* conservation de NotFoundError lors de ApiRequester.url_request()
* ApiRequester.url_request(): suppression de l'affichage automatique des erreurs
* main : meilleure gestion globale des erreurs
* Attente à la suppression des offres (non instantanée) pour éviter bug avec -b DELETE #57 et suppression en cascade.

### [Fixed]

* Bug de config pour les URL des fichiers statics
* Bug absence de transmission des behavior venant de la commande pour ConfigurationAction et OfferingAction
* Gestion du Ctrl+C pendant le monitoring des vérification, suppression des vérifications non fini et réouverture de la livraison

## v0.1.18

### [Added]

* Ajout d'un fichier de listing des modifications.

### [Changed]

* La livraison de plusieurs jeux de données est plus efficace (livraison des jeux de données puis attente des vérifications)
* Documentation : uniformisation du style + maj liens et noms

### [Fixed]

* Bug de config `upload_push_data` manquante.
