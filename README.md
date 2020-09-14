# projet Friendly Fruit


### Installation

Dans le dossier src/data/model:
- Décompresser le fichier model_WD (en 2 parties)

Dans le dossier src/installation:

- Installer python-3.7.1rc2-amd64.exe (Python 3.7.1)
- Installer VC_redist.x64.exe (Visual C++ 2015, 2017 et 2019 64-bits)
- Créer un environnement virtuel via le terminal:
```sh
$ cd src\installation
$ python3 -m venv venvFriendlyFruit
$ .\venvFriendlyFruit\Scripts\activate
```
- Installer les bibliothèques nécessaires :
```sh
$ pip install -r requirements.txt
$ pip install GDAL-3.1.2-cp37-cp37m-win_amd64.whl
```
- Lancer le projet
```sh
$ cd src
$ .\installation\venvFriendlyFruit\Scripts\activate
$ cd flask_mapbox\
$ python server.py
```
- Ouvrir le navigateur en 127.0.0.1:5000 pour accéder à l'application