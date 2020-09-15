# projet Friendly Fruit


### Installation

Lancer setup.exe, qui comprend :
- Installation de python-3.7.1rc2-amd64.exe (Python 3.7.1)
- Installation de VC_redist.x64.exe (Visual C++ 2015, 2017 et 2019 64-bits)
- Création d'un environnement virtuel dans /src/installation/venvFriendlyFruit

### Utilisation
Lancer run.exe :
- Raffraîchir la page 127.0.0.1:5000 après que le serveur soit lancé sur le terminal
- Mettre les images issues de la carte SD dans le dossier /src/data/images
- Appuyer sur le bouton de choix de prédiction entre WD et WD + OW
- Appuyer sur "Démarrer" pour lancer le prétraitement et la prédiction

## Architecture :
- installation/ : Dossier contenant les dépendances de l'installation du projet
- data/ : Dossier contenant le dossier des images brutes (/images) et le dossier du modèle à dézipper (/model)
- flask_mapbox/ : Dossier du projet avec les pages html (/templates) et le js/css associé (/static) et 
		  le programme principal (server.py) comprenant les scripts de pré-traitement et la prédiction du réseau
