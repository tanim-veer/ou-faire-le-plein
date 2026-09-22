"""Point d'entrée de l'API "Où faire le plein".

Expose l'API REST et sert le frontend statique (dossier static/).
"""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.calcul import classer_stations
from app.carburants import chercher_stations
from app.distance import detour_km, distance_km
from app.geocode import geocoder
from app.routage import RoutageIndisponible, trajets_depuis_depart
from app.schemas import RechercheRequest, RechercheResponse

logger = logging.getLogger(__name__)

# Nombre maximum de stations envoyées à OSRM en une fois. On route TOUTES les
# stations trouvées plutôt qu'un sous-ensemble présélectionné : mélanger des
# détours réels (plus honnêtes, donc souvent plus grands) avec des détours
# approximés à vol d'oiseau (systématiquement optimistes) pour les stations
# non routées désavantagerait injustement ces dernières dans le classement.
# Le service "table" d'OSRM calcule tout en 1-2 requêtes quel que soit le
# nombre de stations ; cette limite n'est qu'une sécurité (chercher_stations
# renvoie au plus 100 résultats).
TAILLE_POOL_ROUTAGE = 100

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
    """Cherche les stations autour du départ (et du trajet si une arrivée est
    précisée) et les classe par coût réel du plein, détour compris.
    """
    stations_brutes = await chercher_stations(
        lat=req.depart_lat,
        lon=req.depart_lon,
        rayon_km=req.rayon_recherche_km,
        carburant=req.carburant,
    )

    if not stations_brutes:
        return RechercheResponse(nb_stations_analysees=0, stations=[])

    depart = (req.depart_lat, req.depart_lon)
    arrivee = (req.arrivee_lat, req.arrivee_lon) if req.arrivee_lat is not None else None

    # Pré-tri à vol d'oiseau (gratuit, aucun appel réseau) pour ne demander un
    # vrai calcul d'itinéraire qu'aux stations qui ont une vraie chance de
    # figurer dans le classement final. Avec une arrivée, le bon critère est le
    # détour estimé (une station peut être loin du départ mais presque sur la
    # route) ; sans arrivée, c'est simplement la distance au départ.
    if arrivee is not None:
        cle_tri = lambda s: detour_km(depart, (s["lat"], s["lon"]), arrivee)
    else:
        cle_tri = lambda s: distance_km(*depart, s["lat"], s["lon"])
    stations_brutes.sort(key=cle_tri)
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


# Sert le frontend (index.html, app.js, style.css) à la racine du site.
static_dir = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
