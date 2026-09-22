"""Client pour le service de routage OSRM (calcul de vrais itinéraires routiers).

Utilise le serveur de démonstration public d'OSRM (router.project-osrm.org),
gratuit et sans clé. C'est un service de démonstration, sans garantie de
disponibilité ni de débit : on limite donc le nombre de stations envoyées
(voir POOL_ROUTAGE_MAX dans calcul.py) et l'appelant doit prévoir un repli sur
la distance à vol d'oiseau en cas d'échec (voir app/main.py).
"""
import httpx

BASE_URL = "https://router.project-osrm.org/table/v1/driving/"


class RoutageIndisponible(Exception):
    """Levée quand OSRM ne répond pas, répond une erreur, ou met trop de temps."""


def _coord(lat: float, lon: float) -> str:
    return f"{lon},{lat}"  # OSRM attend "longitude,latitude", à l'inverse de l'usage courant


async def _table(
    coords: list[tuple[float, float]], sources: list[int], destinations: list[int]
) -> dict:
    coord_str = ";".join(_coord(lat, lon) for lat, lon in coords)
    params = {
        "sources": ";".join(map(str, sources)),
        "destinations": ";".join(map(str, destinations)),
        "annotations": "distance,duration",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{BASE_URL}{coord_str}", params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise RoutageIndisponible(str(e)) from e

    if data.get("code") != "Ok":
        raise RoutageIndisponible(data.get("message", "réponse OSRM invalide"))
    return data


async def trajets_depuis_depart(
    depart: tuple[float, float],
    stations: list[tuple[float, float]],
    arrivee: tuple[float, float] | None,
) -> dict:
    """Calcule les trajets routiers nécessaires, en 1 ou 2 appels à OSRM (peu
    importe le nombre de stations, grâce au service "table" qui calcule une
    matrice de trajets en une seule requête) :

    - "aller" : distance et durée de `depart` vers chaque station.
    - "directe" : distance et durée de `depart` vers `arrivee` (calculée dans
      le même appel que "aller"), ou None si `arrivee` n'est pas fournie.
    - "retour" : distance et durée de chaque station vers `arrivee` (second
      appel), ou None si `arrivee` n'est pas fournie.

    Lève RoutageIndisponible si OSRM ne répond pas correctement ; à l'appelant
    de prévoir un repli (voir app/main.py).
    """
    n = len(stations)
    coords = [depart] + stations
    destinations = list(range(1, n + 1))
    if arrivee is not None:
        coords = coords + [arrivee]
        destinations = destinations + [n + 1]

    data = await _table(coords, sources=[0], destinations=destinations)
    distances = data["distances"][0]
    durees = data["durations"][0]

    aller = [
        {"distance_km": distances[i] / 1000, "duree_min": durees[i] / 60} for i in range(n)
    ]

    directe = None
    retour = None
    if arrivee is not None:
        directe = {"distance_km": distances[n] / 1000, "duree_min": durees[n] / 60}

        data2 = await _table(coords, sources=list(range(1, n + 1)), destinations=[n + 1])
        retour = [
            {
                "distance_km": data2["distances"][i][0] / 1000,
                "duree_min": data2["durations"][i][0] / 60,
            }
            for i in range(n)
        ]

    return {"aller": aller, "directe": directe, "retour": retour}
