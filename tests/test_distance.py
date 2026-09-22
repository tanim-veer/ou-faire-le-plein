from app.distance import detour_km, distance_km


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
