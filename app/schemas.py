"""Modèles de données échangés entre le frontend et l'API."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Carburant(str, Enum):
    sp95 = "sp95"
    sp98 = "sp98"
    e10 = "e10"
    e85 = "e85"
    gazole = "gazole"
    gplc = "gplc"


class TypeBudget(str, Enum):
    euros = "euros"
    litres = "litres"


class RechercheRequest(BaseModel):
    depart_lat: float
    depart_lon: float
    arrivee_lat: Optional[float] = None
    arrivee_lon: Optional[float] = None

    carburant: Carburant

    type_budget: TypeBudget
    montant: float = Field(gt=0, description="Montant en euros ou en litres selon type_budget")

    consommation_l_100km: float = Field(default=6.5, gt=0, le=30)
    vitesse_moyenne_kmh: float = Field(default=60, gt=0, le=150)
    rayon_recherche_km: float = Field(default=15, gt=0, le=100)


class Station(BaseModel):
    id: str
    nom: str
    adresse: str
    ville: str
    lat: float
    lon: float
    prix_carburant: float
    maj: Optional[str] = None

    distance_km: float
    detour_km: float
    temps_detour_min: float
    trajet_reel: bool = False  # True si distance/détour viennent d'un vrai calcul d'itinéraire (OSRM)

    volume_achete_l: float
    volume_net_l: float
    cout_plein: float
    cout_detour: float
    cout_total_reel: float


class RechercheResponse(BaseModel):
    nb_stations_analysees: int
    stations: list[Station]


class ItineraireRequest(BaseModel):
    points: list[tuple[float, float]] = Field(min_length=2, description="Liste de (lat, lon), dans l'ordre du trajet")


class ItineraireResponse(BaseModel):
    coordonnees: list[tuple[float, float]]
