from app.calcul import classer_stations, evaluer_station
from app.schemas import Carburant, RechercheRequest, TypeBudget

REQUETE_BASE = dict(
    depart_lat=48.8566,
    depart_lon=2.3522,
    arrivee_lat=None,
    arrivee_lon=None,
    carburant=Carburant.gazole,
    type_budget=TypeBudget.euros,
    montant=50,
    consommation_l_100km=6.0,
    vitesse_moyenne_kmh=60,
    rayon_recherche_km=15,
)


def station_brute(lat, lon, prix):
    return {
        "id": "test",
        "nom": "Station test",
        "adresse": "1 rue Test",
        "ville": "Testville",
        "lat": lat,
        "lon": lon,
        "prix_carburant": prix,
        "maj": None,
    }


def test_volume_achete_correspond_au_budget_en_euros():
    req = RechercheRequest(**REQUETE_BASE)
    s = evaluer_station(station_brute(48.86, 2.35, 2.0), req)
    # 50€ à 2€/L -> 25L
    assert s.volume_achete_l == 25.0
    assert s.cout_plein == 50.0


def test_volume_achete_correspond_au_budget_en_litres():
    req = RechercheRequest(**{**REQUETE_BASE, "type_budget": TypeBudget.litres, "montant": 30})
    s = evaluer_station(station_brute(48.86, 2.35, 1.8), req)
    assert s.volume_achete_l == 30.0
    assert s.cout_plein == 54.0  # 30L * 1.8€


def test_station_plus_pres_du_depart_a_un_cout_detour_nul():
    req = RechercheRequest(**REQUETE_BASE)
    s = evaluer_station(station_brute(48.8566, 2.3522, 2.0), req)  # même position que le départ
    assert s.detour_km == 0
    assert s.cout_detour == 0
    assert s.cout_total_reel == s.cout_plein


def test_station_loin_moins_chere_peut_couter_plus_cher_au_final():
    req = RechercheRequest(**REQUETE_BASE)

    proche_chere = evaluer_station(station_brute(48.86, 2.36, 2.00), req)
    loin_pas_chere = evaluer_station(station_brute(49.5, 3.5, 1.70), req)  # ~130km, gros détour

    # La station loin affiche un prix au litre plus bas...
    assert loin_pas_chere.prix_carburant < proche_chere.prix_carburant
    # ...mais son coût réel total (plein + détour) doit être plus élevé,
    # c'est tout l'intérêt du calcul.
    assert loin_pas_chere.cout_total_reel > proche_chere.cout_total_reel


def test_classement_trie_par_cout_reel_et_pas_par_prix_affiche():
    req = RechercheRequest(**REQUETE_BASE)
    brutes = [
        station_brute(49.5, 3.5, 1.70),  # loin, prix bas -> détour cher
        station_brute(48.86, 2.36, 2.00),  # proche, prix plus haut
    ]
    classees = classer_stations(brutes, req)
    # La station proche doit arriver en premier malgré son prix affiché plus élevé.
    assert classees[0].prix_carburant == 2.00
    assert classees[0].cout_total_reel < classees[1].cout_total_reel
