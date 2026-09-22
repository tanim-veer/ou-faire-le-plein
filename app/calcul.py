"""Calcule, pour chaque station candidate, le coût réel du plein en tenant
compte du détour (carburant brûlé + temps perdu pour s'y rendre), et pas
uniquement du prix affiché à la pompe.
"""
from app.distance import detour_km, distance_km
from app.schemas import RechercheRequest, Station


def evaluer_station(brute: dict, req: RechercheRequest) -> Station:
    """Transforme une station brute (venant de l'API carburants) en Station
    évaluée, avec le coût réel du détour pour aller la remplir.
    """
    depart = (req.depart_lat, req.depart_lon)
    station_coord = (brute["lat"], brute["lon"])
    arrivee = (req.arrivee_lat, req.arrivee_lon) if req.arrivee_lat is not None else None

    dist_km = distance_km(*depart, *station_coord)
    d_km = detour_km(depart, station_coord, arrivee)
    temps_min = (d_km / req.vitesse_moyenne_kmh) * 60

    prix = brute["prix_carburant"]

    # Volume à acheter selon ce que l'utilisateur a demandé (un montant en euros
    # ou directement un volume en litres).
    if req.type_budget.value == "euros":
        volume_l = req.montant / prix
    else:
        volume_l = req.montant

    cout_plein = volume_l * prix

    # Carburant brûlé pour faire le détour, valorisé au prix de cette station.
    carburant_detour_l = (d_km / 100) * req.consommation_l_100km
    cout_detour = carburant_detour_l * prix

    return Station(
        id=brute["id"],
        nom=brute["nom"],
        adresse=brute["adresse"],
        ville=brute["ville"],
        lat=brute["lat"],
        lon=brute["lon"],
        prix_carburant=prix,
        maj=brute.get("maj"),
        distance_km=round(dist_km, 2),
        detour_km=round(d_km, 2),
        temps_detour_min=round(temps_min, 1),
        volume_achete_l=round(volume_l, 2),
        cout_plein=round(cout_plein, 2),
        cout_detour=round(cout_detour, 2),
        cout_total_reel=round(cout_plein + cout_detour, 2),
    )


def classer_stations(stations_brutes: list[dict], req: RechercheRequest) -> list[Station]:
    """Évalue toutes les stations et les trie par coût réel total croissant
    (le meilleur choix en tenant compte du détour arrive en premier).
    """
    evaluees = [evaluer_station(s, req) for s in stations_brutes]
    evaluees.sort(key=lambda s: s.cout_total_reel)
    return evaluees
