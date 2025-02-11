<!--
CE DOCUMENT N'A PAS VOCATION A ÊTRE LU DIRECTEMENT OU VIA GITHUB :
les liens seront cassés, l'affichage ne sera pas correcte. Ne faites ça !

Consultez la doc en ligne ici : https://geoplateforme.github.io/sdk-entrepot/

Le lien vers cette page devrait être : https://geoplateforme.github.io/sdk-entrepot/
-->

# SDK Python

L'API Entrepôt Géoplateforme vous permet de téléverser, traiter puis publier vos données géographiques. Bien que très puissante, cette API n'est pas aisée à prendre en main. Ce module Python a été créé afin de vous permettre d'utiliser la Géoplateforme facilement.

Vous pouvez l'utiliser directement en ligne de commande pour un usage simple ou l'intégrer dans vos scripts Python pour un usage avancé entièrement personnalisable.

![Schéma de l'utilisation du module sdk_entrepot_gpf](assets/images/index__utilisation_module.png)

## Installation

Installez le module via pip :

```sh
pip install sdk_entrepot_gpf
```

Vous pouvez ensuite l'[utiliser comme exécutable](comme-executable.md) ou l'[importer dans vos scripts Python](comme-module.md).

## Tutoriels

Des tutoriels sont disponibles pour voir des cas concrets d'utilisation de A à Z :

* [Tutoriel 1 : héberger une archive pour la rendre téléchargeable](tutoriel_1_archive.md)
* [Tutoriel 2 : téléverser des données vecteur et les publier en flux](tutoriel_2_flux_vecteur.md)
* [Tutoriel 3 : téléverser des données raster et les publier en flux](tutoriel_3_flux_raster.md)
* [Tutoriel PCRS : téléverser des images PCRS et les publier en flux](tutoriel_pcrs.md)

## Développement

Si vous souhaitez participer au développement du projet, consultez le [document détaillant comment procéder](development.md).
