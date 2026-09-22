# ⛽ Où faire le plein

Trouve la station-service la moins chère **en tenant compte du détour** pour s'y rendre — une station moins chère au litre mais loin de ta route peut coûter plus cher au final, une fois le carburant du trajet compté.

## Démo

_Lien de la démo à ajouter une fois déployé._

## Le problème que ça résout

Les sites de comparaison de prix de carburant classent les stations par prix affiché. Mais si la moins chère est à 15 minutes de détour, le carburant brûlé pour s'y rendre (et en revenir) peut annuler l'économie. Cette appli calcule, pour chaque station, un **coût réel** = prix du plein + coût du détour, et classe par ce coût réel plutôt que par le prix affiché.

## Fonctionnement

1. Tu donnes un point de départ (et une arrivée si tu as un trajet), le carburant, et ce que tu veux mettre (en € ou en L).
2. L'appli récupère les stations à proximité via l'API officielle du gouvernement.
3. Pour chaque station, elle calcule la distance du détour :
   - avec un trajet (départ + arrivée) : distance supplémentaire pour passer par la station plutôt que d'aller directement à destination ;
   - sans arrivée précisée : aller-retour depuis le départ.
4. Elle en déduit le carburant brûlé pour ce détour, son coût (valorisé au prix de la station), et l'ajoute au prix du plein pour obtenir le coût réel.
5. Les stations sont classées par coût réel croissant.

## Sources de données

- **Prix des carburants** : [API officielle du gouvernement](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2) — ~9 800 stations en France, prix mis à jour en continu (obligation légale des stations). Gratuite, sans clé d'API.
- **Géocodage des adresses** : [Base Adresse Nationale](https://adresse.data.gouv.fr) (api-adresse.data.gouv.fr) — service officiel gratuit, sans clé.
- **Fond de carte** : [OpenStreetMap](https://www.openstreetmap.org).

## Stack

Python · FastAPI · httpx (appels API asynchrones) · Pydantic · HTML/JS vanilla · Leaflet

## Limites connues (assumées)

- **Distance à vol d'oiseau**, pas un vrai calcul d'itinéraire routier (pas de moteur de routage type OSRM). Ça sous-estime légèrement les distances réelles sur route, mais ça reste pertinent pour comparer des stations entre elles sur une même zone.
- **Le géocodage ne connaît que des adresses**, pas des lieux-dits ou des monuments : chercher "Tour Eiffel" peut renvoyer une rue portant ce nom ailleurs en France plutôt que le monument parisien. Une adresse ou un nom de ville fonctionne toujours.
- **Vitesse moyenne fixe** (60 km/h par défaut) pour estimer le temps du détour — ne tient pas compte du trafic réel.

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

10 tests couvrent le calcul de distance et le calcul du coût réel, notamment le cas central du projet : une station plus chère au litre mais très proche doit passer devant une station moins chère mais lointaine.

## Pistes d'amélioration

- Remplacer la distance à vol d'oiseau par un vrai calcul d'itinéraire (API de routage type OSRM ou GraphHopper).
- Géolocalisation automatique du départ depuis le navigateur.
- Historique des prix par station (l'API expose une date de dernière mise à jour).
- Filtrer par services disponibles (station ouverte 24h/24, paiement carte, etc. — déjà présents dans les données brutes).

## Auteur

Tanim Veer, étudiant en BUT Informatique (parcours Data & IA)

[GitHub](https://github.com/tanim-veer) · [Portfolio](https://tanim-veer.fr)
