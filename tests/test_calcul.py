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
    assert s.volume_net_l == s.volume_achete_l  # pas de détour -> rien n'est "perdu" en carburant


def test_station_tres_loin_perd_meme_si_moins_chere_en_mode_euros():
    """Cas extrême : un détour énorme doit faire perdre une station même très
    bon marché, en mode budget en euros (classement par volume net obtenu).
    """
    req = RechercheRequest(**REQUETE_BASE)

    proche_chere = evaluer_station(station_brute(48.86, 2.36, 2.00), req)
    loin_pas_chere = evaluer_station(station_brute(49.5, 3.5, 1.70), req)  # ~130km, gros détour

    assert loin_pas_chere.prix_carburant < proche_chere.prix_carburant
    assert loin_pas_chere.volume_net_l < proche_chere.volume_net_l


def test_euros_favorise_le_prix_bas_meme_avec_un_leger_detour():
    """Régression : en mode budget en euros, le montant dépensé est fixe quelle
    que soit la station (on ajuste le volume acheté). Classer par "coût total"
    revient alors à classer par distance et ignore le prix affiché, ce qui est
    trompeur : deux stations à la même distance mais à des prix très différents
    finissent quasiment ex-æquo, alors que la moins chère donne bien plus
    d'essence pour le même argent.

    Le bon critère en mode euros est donc le volume NET obtenu (volume acheté
    moins le carburant brûlé pour le détour), pas le coût total.
    """
    req = RechercheRequest(**REQUETE_BASE)  # 50€, montant fixe

    proche_chere = station_brute(48.8566, 2.3522, 2.50)  # aucun détour, prix élevé
    leger_detour_pas_chere = station_brute(48.87, 2.37, 2.00)  # petit détour, 20% moins cher

    classees = classer_stations([proche_chere, leger_detour_pas_chere], req)

    # La station moins chère doit gagner : elle donne nettement plus de
    # carburant pour les mêmes 50€, malgré le petit détour.
    assert classees[0].prix_carburant == 2.00

    # Un classement (bugué) par coût total réel aurait donné le résultat inverse,
    # puisque le coût total réel est ~50€ pour les deux (le montant est fixe) :
    # seul le petit coût du détour les différencierait, favorisant à tort la
    # station la plus chère mais sans aucun détour.
    par_cout_total = sorted([classees[0], classees[1]], key=lambda s: s.cout_total_reel)
    assert par_cout_total[0].prix_carburant == 2.50


def test_litres_classe_par_cout_total_et_favorise_le_prix_bas():
    """En mode budget en litres, le volume acheté est fixe : c'est bien l'argent
    dépensé (carburant + détour) qui doit déterminer le classement.
    """
    req = RechercheRequest(**{**REQUETE_BASE, "type_budget": TypeBudget.litres, "montant": 40})

    proche_chere = station_brute(48.8566, 2.3522, 2.00)
    loin_pas_chere = station_brute(49.5, 3.5, 1.70)  # ~130km de détour

    classees = classer_stations([proche_chere, loin_pas_chere], req)

    # Le gros détour doit faire perdre la station la moins chère : pour un
    # volume fixe, le carburant supplémentaire brûlé en route coûte plus cher
    # que ce que la différence de prix ne fait économiser.
    assert classees[0].prix_carburant == 2.00
    assert classees[0].cout_total_reel < classees[1].cout_total_reel


def test_evaluer_station_utilise_le_trajet_reel_si_fourni():
    """Quand un vrai trajet routier (OSRM) est fourni, il doit être utilisé
    tel quel plutôt que le calcul à vol d'oiseau.
    """
    req = RechercheRequest(**REQUETE_BASE)
    trajet = {"distance_km": 12.3, "detour_km": 24.6, "temps_detour_min": 31.5}

    s = evaluer_station(station_brute(48.86, 2.36, 2.0), req, trajet=trajet)

    assert s.distance_km == 12.3
    assert s.detour_km == 24.6
    assert s.temps_detour_min == 31.5
    assert s.trajet_reel is True


def test_evaluer_station_sans_trajet_retombe_sur_vol_oiseau():
    req = RechercheRequest(**REQUETE_BASE)
    s = evaluer_station(station_brute(48.86, 2.36, 2.0), req)
    assert s.trajet_reel is False


def test_classer_stations_applique_les_trajets_par_id():
    req = RechercheRequest(**REQUETE_BASE)
    brutes = [
        {**station_brute(48.86, 2.36, 2.0), "id": "A"},
        {**station_brute(48.90, 2.40, 2.0), "id": "B"},
    ]
    # Un trajet réel indique que "B" (pourtant plus loin à vol d'oiseau) a en
    # fait un détour routier minime (ex : autoroute directe).
    trajets = {"B": {"distance_km": 1.0, "detour_km": 2.0, "temps_detour_min": 2.0}}

    classees = classer_stations(brutes, req, trajets)
    par_id = {s.id: s for s in classees}

    assert par_id["B"].trajet_reel is True
    assert par_id["A"].trajet_reel is False
    assert par_id["B"].detour_km == 2.0
