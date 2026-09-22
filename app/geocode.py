"""Client pour l'API Adresse (Base Adresse Nationale, data.gouv.fr).

Convertit une adresse ou un nom de ville en coordonnées GPS. Service officiel,
gratuit, sans clé d'API. Documentation : https://adresse.data.gouv.fr/api-doc/adresse
"""
import httpx

BASE_URL = "https://api-adresse.data.gouv.fr/search/"


async def geocoder(adresse: str) -> tuple[float, float] | None:
    """Renvoie (latitude, longitude) pour une adresse donnée, ou None si rien trouvé."""
    params = {"q": adresse, "limit": 1}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    features = data.get("features", [])
    if not features:
        return None

    lon, lat = features[0]["geometry"]["coordinates"]
    return lat, lon
