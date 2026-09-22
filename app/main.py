"""Point d'entrée de l'API "Où faire le plein".

Expose l'API REST et sert le frontend statique (dossier static/).
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.calcul import classer_stations
from app.carburants import chercher_stations
from app.geocode import geocoder
from app.schemas import RechercheRequest, RechercheResponse

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

    stations_classees = classer_stations(stations_brutes, req)

    return RechercheResponse(
        nb_stations_analysees=len(stations_classees),
        stations=stations_classees[:20],  # les 20 meilleurs résultats
    )


# Sert le frontend (index.html, app.js, style.css) à la racine du site.
static_dir = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
