"""Client pour l'API officielle des prix des carburants (data.economie.gouv.fr).

Documentation : https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2
Données publiques, gratuites, mises à jour en continu par les stations elles-mêmes
(obligation légale). Aucune clé d'API requise.
"""
import httpx

from app.schemas import Carburant

BASE_URL = "https://data.economie.gouv.fr/api/records/1.0/search/"
DATASET = "prix-des-carburants-en-france-flux-instantane-v2"

# Nom du champ prix dans l'API, pour chaque carburant.
CHAMP_PRIX = {
    Carburant.sp95: "sp95_prix",
    Carburant.sp98: "sp98_prix",
    Carburant.e10: "e10_prix",
    Carburant.e85: "e85_prix",
    Carburant.gazole: "gazole_prix",
    Carburant.gplc: "gplc_prix",
}


async def chercher_stations(
    lat: float, lon: float, rayon_km: float, carburant: Carburant, limite: int = 100
) -> list[dict]:
    """Récupère les stations disposant du carburant demandé dans un rayon donné.

    Renvoie une liste de dicts bruts (station + prix + coordonnées), filtrée pour
    ne garder que les stations où le carburant demandé est effectivement disponible
    (le prix peut être absent si la station est en rupture).
    """
    champ_prix = CHAMP_PRIX[carburant]

    params = {
        "dataset": DATASET,
        "rows": limite,
        "geofilter.distance": f"{lat},{lon},{int(rayon_km * 1000)}",
        "sort": champ_prix,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    stations = []
    for record in data.get("records", []):
        fields = record["fields"]
        prix = fields.get(champ_prix)
        geom = fields.get("geom")
        if prix is None or not geom:
            continue  # carburant indisponible à cette station, ou coordonnées manquantes
        stations.append(
            {
                "id": record["recordid"],
                "nom": fields.get("adresse", "Station"),
                "adresse": fields.get("adresse", ""),
                "ville": fields.get("ville", ""),
                "lat": geom[0],
                "lon": geom[1],
                "prix_carburant": prix,
                "maj": fields.get(f"{carburant.value}_maj"),
            }
        )
    return stations
