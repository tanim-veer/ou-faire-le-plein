"""Calculs géographiques : distance à vol d'oiseau et coût d'un détour.

On n'utilise pas de moteur de routage réel (type OSRM) pour rester simple et
sans dépendance externe payante : les distances sont calculées à vol d'oiseau
(formule de Haversine). C'est une approximation qui sous-estime légèrement les
distances réelles sur route, mais elle reste pertinente pour comparer des
stations entre elles sur une même zone.
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
