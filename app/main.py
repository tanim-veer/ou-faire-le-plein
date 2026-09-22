"""Point d'entrée de l'API "Où faire le plein".

Expose l'API REST et sert le frontend statique (dossier static/).
"""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.calcul import classer_stations
from app.carburants import chercher_stations_le_long_du_trajet
from app.distance import detour_km, points_le_long_du_trajet
from app.geocode import geocoder
from app.routage import RoutageIndisponible, tracer_itineraire, trajets_depuis_depart
from app.schemas import (
    ItineraireRequest,
    ItineraireResponse,
    RechercheRequest,
    RechercheResponse,
)

logger = logging.getLogger(__name__)

# Nombre maximum de stations envoyées à OSRM en une fois. Avec une arrivée, la
# recherche porte sur plusieurs points le long du trajet (voir
# points_le_long_du_trajet) et peut donc remonter plusieurs centaines de
# stations sur un long trajet : au-delà de cette limite, on garde les plus
# prometteuses (détour approximé le plus faible) avant de demander leur vrai
# détour à OSRM. Testé jusqu'à ~190 stations en une seule requête "table" sans
# problème ; si jamais OSRM refuse une requête trop grosse, l'appli retombe
# de toute façon sur l'estimation à vol d'oiseau (voir le except plus bas).
TAILLE_POOL_ROUTAGE = 200

app = FastAPI(
    title="Où faire le plein",
    description="Trouve la station-service la moins chère en tenant compte du détour réel.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/geocoder")
async def api_geocoder(adresse: str):
    """Convertit une adresse en coordonnées GPS, pour préremplir le formulaire."""
    resultat = await geocoder(adresse)
    if resultat is None:
        raise HTTPException(status_code=404, detail="Adresse introuvable")
    lat, lon = resultat
    return {"lat": lat, "lon": lon}


@app.post("/api/recherche", response_model=RechercheResponse)
async def api_recherche(req: RechercheRequest):
    """Cherche les stations le long du trajet (autour du départ seul s'il n'y a
    pas d'arrivée) et les classe par coût réel du plein, détour compris.
    """
    depart = (req.depart_lat, req.depart_lon)
    arrivee = (req.arrivee_lat, req.arrivee_lon) if req.arrivee_lat is not None else None

    # Avec une arrivée, on cherche autour de plusieurs points répartis sur tout
    # le trajet (pas seulement près du départ), sinon on ne trouverait jamais
    # les stations proches de l'arrivée ou du milieu du parcours.
    points_recherche = points_le_long_du_trajet(depart, arrivee)
    stations_brutes = await chercher_stations_le_long_du_trajet(
        points_recherche, rayon_km=req.rayon_recherche_km, carburant=req.carburant
    )

    if not stations_brutes:
        return RechercheResponse(nb_stations_analysees=0, stations=[])

    # Pré-tri à vol d'oiseau (gratuit, aucun appel réseau) pour ne demander un
    # vrai calcul d'itinéraire qu'aux stations qui ont une vraie chance de
    # figurer dans le classement final (detour_km gère aussi bien le cas avec
    # arrivée que l'aller-retour sans arrivée).
    stations_brutes.sort(key=lambda s: detour_km(depart, (s["lat"], s["lon"]), arrivee))
    candidats = stations_brutes[:TAILLE_POOL_ROUTAGE]

    trajets_par_id: dict[str, dict] = {}
    try:
        trajets = await trajets_depuis_depart(
            depart, [(s["lat"], s["lon"]) for s in candidats], arrivee
        )
        for i, s in enumerate(candidats):
            aller = trajets["aller"][i]
            if arrivee is not None:
                retour = trajets["retour"][i]
                directe = trajets["directe"]
                d_km = max(aller["distance_km"] + retour["distance_km"] - directe["distance_km"], 0)
                d_min = max(aller["duree_min"] + retour["duree_min"] - directe["duree_min"], 0)
            else:
                d_km = 2 * aller["distance_km"]
                d_min = 2 * aller["duree_min"]

            trajets_par_id[s["id"]] = {
                "distance_km": aller["distance_km"],
                "detour_km": d_km,
                "temps_detour_min": d_min,
            }
    except RoutageIndisponible as e:
        # Le service de routage (démo publique, sans garantie) est indisponible :
        # on continue avec l'estimation à vol d'oiseau plutôt que de faire échouer
        # la recherche.
        logger.warning("Routage OSRM indisponible, repli sur le calcul à vol d'oiseau : %s", e)

    stations_classees = classer_stations(stations_brutes, req, trajets_par_id)

    return RechercheResponse(
        nb_stations_analysees=len(stations_classees),
        stations=stations_classees[:20],  # les 20 meilleurs résultats
    )


@app.post("/api/itineraire", response_model=ItineraireResponse)
async def api_itineraire(req: ItineraireRequest):
    """Renvoie le tracé détaillé d'un itinéraire passant par les points donnés
    (dans l'ordre), pour l'afficher sur la carte. Ex : [départ, arrivée] pour
    le trajet direct, ou [départ, station, arrivée] une fois une station
    choisie.
    """
    try:
        coordonnees = await tracer_itineraire(req.points)
    except RoutageIndisponible as e:
        logger.warning("Tracé d'itinéraire indisponible : %s", e)
        raise HTTPException(status_code=503, detail="Service de routage indisponible") from e

    return ItineraireResponse(coordonnees=coordonnees)


# Sert le frontend (index.html, app.js, style.css) à la racine du site.
static_dir = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
