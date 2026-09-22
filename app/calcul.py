"""Calcule, pour chaque station candidate, le coût réel du plein en tenant
compte du détour (carburant brûlé + temps perdu pour s'y rendre), et pas
uniquement du prix affiché à la pompe.

Le bon classement dépend de ce que l'utilisateur a fixé :

- Budget en LITRES (le volume à acheter est fixe) : ce qui varie d'une station
  à l'autre, c'est l'argent dépensé (prix du plein + carburant brûlé pour le
  détour). On classe donc par coût total réel croissant.
- Budget en EUROS (l'argent dépensé est fixe) : quelle que soit la station,
  l'utilisateur dépense toujours le même montant en carburant. Ce qui varie,
  c'est la quantité d'essence obtenue pour cet argent, moins celle brûlée pour
  le détour. On classe donc par volume net obtenu décroissant.

  (Classer par "coût total" en mode euros serait trompeur : ce coût est
  quasiment fixe puisque le montant dépensé est fixé par l'utilisateur, et le
  classement finirait par ignorer le prix du carburant pour ne refléter que la
  distance du détour.)
"""
from app.distance import detour_km, distance_km
from app.schemas import RechercheRequest, Station, TypeBudget


def evaluer_station(brute: dict, req: RechercheRequest, trajet: dict | None = None) -> Station:
    """Transforme une station brute (venant de l'API carburants) en Station
    évaluée, avec le coût réel du détour pour aller la remplir.

    Si `trajet` est fourni (dict avec distance_km/detour_km/temps_detour_min,
    voir app/main.py), on utilise ce vrai calcul d'itinéraire routier (OSRM).
    Sinon, on retombe sur une estimation à vol d'oiseau (voir app/distance.py).
    """
    depart = (req.depart_lat, req.depart_lon)
    station_coord = (brute["lat"], brute["lon"])
    arrivee = (req.arrivee_lat, req.arrivee_lon) if req.arrivee_lat is not None else None

    if trajet is not None:
        dist_km = trajet["distance_km"]
        d_km = trajet["detour_km"]
        temps_min = trajet["temps_detour_min"]
    else:
        dist_km = distance_km(*depart, *station_coord)
        d_km = detour_km(depart, station_coord, arrivee)
        temps_min = (d_km / req.vitesse_moyenne_kmh) * 60

    prix = brute["prix_carburant"]

    # Volume à acheter selon ce que l'utilisateur a demandé (un montant en euros
    # ou directement un volume en litres).
    if req.type_budget == TypeBudget.euros:
        volume_l = req.montant / prix
    else:
        volume_l = req.montant

    cout_plein = volume_l * prix

    # Carburant brûlé pour faire le détour, valorisé au prix de cette station.
    carburant_detour_l = (d_km / 100) * req.consommation_l_100km
    cout_detour = carburant_detour_l * prix

    # Volume réellement gagné une fois le détour payé en carburant.
    volume_net_l = volume_l - carburant_detour_l

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
        trajet_reel=trajet is not None,
        volume_achete_l=round(volume_l, 2),
        volume_net_l=round(volume_net_l, 2),
        cout_plein=round(cout_plein, 2),
        cout_detour=round(cout_detour, 2),
        cout_total_reel=round(cout_plein + cout_detour, 2),
    )


def classer_stations(
    stations_brutes: list[dict],
    req: RechercheRequest,
    trajets_par_id: dict[str, dict] | None = None,
) -> list[Station]:
    """Évalue toutes les stations et les classe selon ce que l'utilisateur a
    fixé (voir le module docstring pour le raisonnement).

    `trajets_par_id` associe l'id d'une station à un vrai trajet routier
    (calculé via OSRM, voir app/main.py) pour les stations où on en a un ;
    les autres retombent sur l'estimation à vol d'oiseau.
    """
    trajets_par_id = trajets_par_id or {}
    evaluees = [
        evaluer_station(s, req, trajets_par_id.get(s["id"])) for s in stations_brutes
    ]

    if req.type_budget == TypeBudget.euros:
        evaluees.sort(key=lambda s: s.volume_net_l, reverse=True)
    else:
        evaluees.sort(key=lambda s: s.cout_total_reel)

    return evaluees
