# ⛽ Où faire le plein

Trouve la station-service la moins chère **en tenant compte du détour** pour s'y rendre — une station moins chère au litre mais loin de ta route peut coûter plus cher au final, une fois le carburant du trajet compté.

## Démo

**[ou-faire-le-plein.onrender.com](https://ou-faire-le-plein.onrender.com)**

> Hébergé sur le plan gratuit de Render : le service se met en veille après inactivité, la première requête peut prendre 30 à 50 secondes le temps qu'il redémarre.

## Le problème que ça résout

Les sites de comparaison de prix de carburant classent les stations par prix affiché. Mais si la moins chère est à 15 minutes de détour, le carburant brûlé pour s'y rendre (et en revenir) peut annuler l'économie. Cette appli calcule, pour chaque station, un **coût réel** = prix du plein + coût du détour, et classe par ce coût réel plutôt que par le prix affiché.

## Fonctionnement

1. Tu donnes un point de départ (et une arrivée si tu as un trajet), le carburant, et ce que tu veux mettre (en € ou en L).
2. L'appli récupère les stations via l'API officielle du gouvernement. Avec une arrivée, elle cherche autour de **plusieurs points répartis sur tout le trajet** (pas seulement près du départ), pour aussi trouver les stations proches du milieu du parcours ou de la destination.
3. Pour chaque station, elle calcule un **vrai itinéraire routier** (via OSRM, pas une distance à vol d'oiseau) pour estimer le détour :
   - avec un trajet (départ + arrivée) : distance et temps supplémentaires pour passer par la station plutôt que d'aller directement à destination (calculés à partir de trois vrais trajets : départ→station, station→arrivée, départ→arrivée direct) ;
   - sans arrivée précisée : aller-retour routier depuis le départ.
   - Toutes les stations sont routées en 1 à 2 requêtes seulement, quel que soit leur nombre, grâce au service "table" d'OSRM qui calcule une matrice de trajets en un seul appel.
4. Elle en déduit le carburant brûlé pour ce détour, son coût (valorisé au prix de la station), et l'ajoute au prix du plein pour obtenir le coût réel.
5. Les stations sont classées par coût réel croissant (mode litres) ou par volume net obtenu décroissant (mode euros — voir `app/calcul.py` pour le raisonnement).
6. L'itinéraire est tracé sur la carte (service `route` d'OSRM) : le trajet direct dès la recherche, puis départ → station → arrivée dès qu'on clique sur une station.

Si OSRM est indisponible (c'est un serveur de démonstration public, sans garantie), l'appli retombe automatiquement sur une estimation à vol d'oiseau plutôt que d'échouer.

## Sources de données

- **Prix des carburants** : [API officielle du gouvernement](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2) — ~9 800 stations en France, prix mis à jour en continu (obligation légale des stations). Gratuite, sans clé d'API.
- **Géocodage des adresses** : [Base Adresse Nationale](https://adresse.data.gouv.fr) (api-adresse.data.gouv.fr) — service officiel gratuit, sans clé.
- **Calcul d'itinéraire** : [OSRM](http://project-osrm.org/) — serveur de démonstration public, gratuit et sans clé, mais non garanti (voir Limites).
- **Fond de carte** : [OpenStreetMap](https://www.openstreetmap.org).

## Stack

Python · FastAPI · httpx (appels API asynchrones) · Pydantic · HTML/JS vanilla · Leaflet

## Limites connues (assumées)

- **OSRM est un service de démonstration public**, sans garantie de disponibilité ni de débit. En cas d'échec, l'appli retombe sur une estimation à vol d'oiseau (moins précise, avec une vitesse moyenne fixe de 60 km/h par défaut) plutôt que de planter — chaque résultat indique s'il vient d'un vrai itinéraire ou d'une estimation.
- **Pas de trafic en temps réel** : OSRM calcule un itinéraire à vitesse libre, pas les conditions de circulation du moment (contrairement à Waze ou Google Maps).
- **Le géocodage ne connaît que des adresses**, pas des lieux-dits ou des monuments : chercher "Tour Eiffel" peut renvoyer une rue portant ce nom ailleurs en France plutôt que le monument parisien. Une adresse ou un nom de ville fonctionne toujours.

## Installation

```bash
git clone https://github.com/tanim-veer/ou-faire-le-plein.git
cd ou-faire-le-plein
python -m venv venv
venv\Scripts\activate        # Linux/macOS : source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

L'application est ensuite disponible sur `http://127.0.0.1:8000`.

## Tests

```bash
pip install pytest
pytest
```

18 tests couvrent le calcul de distance et le calcul du coût réel, notamment :
- une station plus chère au litre mais très proche doit passer devant une station moins chère mais lointaine (mode litres) ;
- en mode euros, le prix doit vraiment influencer le classement (voir `test_euros_favorise_le_prix_bas_meme_avec_un_leger_detour`, qui documente un bug corrigé : classer par coût total en mode euros ignorait presque totalement le prix) ;
- un vrai trajet routier fourni est utilisé tel quel plutôt que l'estimation à vol d'oiseau ;
- les points de recherche répartis le long du trajet couvrent bien tout le parcours, sans dépasser le nombre maximum fixé.

## Pistes d'amélioration

- Tenir compte du trafic en temps réel (nécessiterait une API payante type Google Maps ou TomTom).
- Géolocalisation automatique du départ depuis le navigateur.
- Historique des prix par station (l'API expose une date de dernière mise à jour).
- Filtrer par services disponibles (station ouverte 24h/24, paiement carte, etc. — déjà présents dans les données brutes).

## Auteur

Tanim Veer, étudiant en BUT Informatique (parcours Data & IA)

[GitHub](https://github.com/tanim-veer) · [Portfolio](https://tanim-veer.fr)
