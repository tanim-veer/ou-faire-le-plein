from app.distance import detour_km, distance_km, points_le_long_du_trajet


def test_distance_paris_lyon():
    # Distance à vol d'oiseau Paris-Lyon : environ 392 km (valeur de référence connue).
    d = distance_km(48.8566, 2.3522, 45.7640, 4.8357)
    assert 385 <= d <= 400


def test_distance_point_identique_est_nulle():
    assert distance_km(48.8566, 2.3522, 48.8566, 2.3522) == 0


def test_detour_sans_arrivee_est_un_aller_retour():
    depart = (48.8566, 2.3522)
    station = (48.9, 2.4)
    d = detour_km(depart, station, None)
    assert d == 2 * distance_km(*depart, *station)


def test_detour_station_sur_le_trajet_est_proche_de_zero():
    # Une station exactement entre départ et arrivée ne doit ajouter quasiment
    # aucune distance supplémentaire.
    depart = (48.0, 2.0)
    arrivee = (49.0, 2.0)
    station_sur_le_trajet = (48.5, 2.0)
    d = detour_km(depart, station_sur_le_trajet, arrivee)
    assert d < 0.5  # tolérance pour l'approximation à vol d'oiseau


def test_detour_station_hors_trajet_est_positif():
    depart = (48.0, 2.0)
    arrivee = (49.0, 2.0)
    station_loin = (48.5, 4.0)  # nettement à l'écart de la ligne directe
    d = detour_km(depart, station_loin, arrivee)
    assert d > 50


def test_points_sans_arrivee_renvoie_juste_le_depart():
    depart = (48.8566, 2.3522)
    assert points_le_long_du_trajet(depart, None) == [depart]


def test_points_le_long_du_trajet_couvre_tout_le_parcours():
    # Paris -> Lyon (~392 km) : il doit y avoir plusieurs points intermédiaires,
    # en commençant par le départ et en terminant par l'arrivée.
    depart = (48.8566, 2.3522)
    arrivee = (45.7640, 4.8357)
    points = points_le_long_du_trajet(depart, arrivee, espacement_km=25, max_points=8)

    assert points[0] == depart
    assert points[-1] == arrivee
    assert len(points) > 2  # au moins un point intermédiaire sur un si long trajet
    assert len(points) <= 8  # jamais plus que max_points


def test_points_le_long_du_trajet_respecte_max_points():
    depart = (48.8566, 2.3522)
    arrivee = (45.7640, 4.8357)
    points = points_le_long_du_trajet(depart, arrivee, espacement_km=1, max_points=5)
    assert len(points) == 5  # sans la limite, un espacement de 1km en donnerait des centaines


def test_points_trajet_court_ne_duplique_pas_le_depart():
    # Sur un trajet plus court que l'espacement demandé, il ne doit y avoir que
    # le départ et l'arrivée, pas de points intermédiaires redondants.
    depart = (48.8566, 2.3522)
    arrivee = (48.87, 2.36)  # quelques centaines de mètres
    points = points_le_long_du_trajet(depart, arrivee, espacement_km=25, max_points=8)
    assert points == [depart, arrivee]
