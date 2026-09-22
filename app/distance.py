"""Calculs géographiques à vol d'oiseau (formule de Haversine).

Sert de repli léger, sans appel réseau, quand le vrai calcul d'itinéraire
(OSRM, voir app/routage.py) est indisponible, et de présélection rapide avant
de solliciter OSRM (voir app/main.py).
"""
import math

RAYON_TERRE_KM = 6371.0


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance à vol d'oiseau entre deux points GPS (formule de Haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * RAYON_TERRE_KM * math.asin(math.sqrt(a))


def detour_km(
    depart: tuple[float, float],
    station: tuple[float, float],
    arrivee: tuple[float, float] | None,
) -> float:
    """Distance supplémentaire (en km) pour passer par la station.

    - Avec un trajet complet (départ + arrivée) : détour = dist(départ, station)
      + dist(station, arrivée) - dist(départ, arrivée). C'est la distance en plus
      par rapport à un trajet direct, en passant par la station comme étape.
    - Sans arrivée précisée : on suppose un aller-retour depuis le point de départ
      (on va faire le plein puis on revient), donc détour = 2 * dist(départ, station).
    """
    dist_depart_station = distance_km(*depart, *station)

    if arrivee is None:
        return 2 * dist_depart_station

    dist_station_arrivee = distance_km(*station, *arrivee)
    dist_directe = distance_km(*depart, *arrivee)

    detour = dist_depart_station + dist_station_arrivee - dist_directe
    return max(detour, 0.0)  # évite un résultat légèrement négatif dû à l'approximation


def points_le_long_du_trajet(
    depart: tuple[float, float],
    arrivee: tuple[float, float] | None,
    espacement_km: float = 25,
    max_points: int = 8,
) -> list[tuple[float, float]]:
    """Répartit des points entre `depart` et `arrivee`, pour chercher des
    stations tout au long du trajet plutôt qu'uniquement autour du départ.

    Sans arrivée, renvoie simplement [depart] (recherche classique, aller-retour).
    Avec une arrivée, ajoute des points intermédiaires par interpolation linéaire
    (en ligne droite, pas sur la route réelle : suffisant pour couvrir la zone
    à chercher, une route ne s'écarte pas énormément d'une ligne droite entre
    deux villes à l'échelle où l'on cherche des stations).
    """
    if arrivee is None:
        return [depart]

    distance_totale = distance_km(*depart, *arrivee)
    nb_segments = max(1, min(max_points - 1, round(distance_totale / espacement_km)))

    points = []
    for i in range(nb_segments + 1):
        t = i / nb_segments
        lat = depart[0] + (arrivee[0] - depart[0]) * t
        lon = depart[1] + (arrivee[1] - depart[1]) * t
        points.append((lat, lon))
    return points
