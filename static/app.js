const form = document.getElementById("form-recherche");
const message = document.getElementById("message");
const resultatsEl = document.getElementById("resultats");

// Carte centrée sur la France par défaut, en attendant une recherche.
// Fond OpenStreetMap standard (gratuit, sans clé), assombri en CSS (voir
// style.css, règle #carte .leaflet-tile-pane) pour coller au thème sombre.
const carte = L.map("carte").setView([46.6, 2.3], 6);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; contributeurs OpenStreetMap",
  maxZoom: 19,
}).addTo(carte);

let marqueurs = [];
let ligneItineraire = null;
let marqueurDepart = null;
let marqueurArrivee = null;

// Mémorisés après chaque recherche, pour pouvoir retracer l'itinéraire quand
// on clique sur une station sans tout redemander au serveur.
let dernierDepart = null;
let derniereArrivee = null;
let stationsCourantes = [];

function viderMarqueurs() {
  marqueurs.forEach((m) => carte.removeLayer(m));
  marqueurs = [];
}

async function geocoder(adresse) {
  const resp = await fetch(`/api/geocoder?adresse=${encodeURIComponent(adresse)}`);
  if (!resp.ok) {
    throw new Error(`Adresse introuvable : "${adresse}"`);
  }
  return resp.json();
}

function formatMinutes(min) {
  if (min < 1) return "moins d'1 min";
  return `${Math.round(min)} min`;
}

// Trace (ou retrace) l'itinéraire passant par les points donnés (dans
// l'ordre). Échoue silencieusement si le service de routage est indisponible :
// l'absence de tracé ne doit pas empêcher d'utiliser le reste de l'appli.
async function tracerItineraire(points) {
  if (ligneItineraire) {
    carte.removeLayer(ligneItineraire);
    ligneItineraire = null;
  }
  try {
    const resp = await fetch("/api/itineraire", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ points }),
    });
    if (!resp.ok) return;

    const data = await resp.json();
    ligneItineraire = L.polyline(data.coordonnees, {
      color: "#f5b60d",
      weight: 4,
      opacity: 0.85,
    }).addTo(carte);
    ligneItineraire.bringToBack();
  } catch {
    // Pas de tracé, tant pis : la recherche et le classement restent valables.
  }
}

// Sélectionne une station : la met en évidence dans la liste et trace
// l'itinéraire départ -> station -> arrivée (ou départ -> station -> départ
// s'il n'y a pas d'arrivée, c'est-à-dire un aller-retour).
function selectionnerStation(index) {
  document.querySelectorAll("#resultats .station").forEach((el, i) => {
    el.classList.toggle("selectionnee", i === index);
  });

  const s = stationsCourantes[index];
  const point = [s.lat, s.lon];
  const retour = derniereArrivee || dernierDepart;
  tracerItineraire([dernierDepart, point, retour]);

  carte.panTo(point);
}

function afficherResultats(stations, typeBudget) {
  resultatsEl.innerHTML = "";
  viderMarqueurs();
  stationsCourantes = stations;

  const astuce = document.getElementById("astuce");
  astuce.hidden = stations.length === 0;

  if (stations.length === 0) {
    message.textContent = "Aucune station trouvée avec ce carburant dans le rayon choisi.";
    return;
  }

  stations.forEach((s, i) => {
    const li = document.createElement("li");
    li.className = "station" + (i === 0 ? " top" : "");
    li.title = "Cliquer pour tracer l'itinéraire jusqu'à cette station";

    // Le nombre mis en avant doit correspondre à ce qui détermine réellement
    // le classement (voir app/calcul.py) : le volume net obtenu en mode "€"
    // (le montant dépensé est fixe), le coût total en mode "litres".
    const headline = typeBudget === "euros"
      ? `${s.volume_net_l.toFixed(1)} L`
      : `${s.cout_total_reel.toFixed(2)} €`;
    const sousDetail = typeBudget === "euros"
      ? `pour ${s.cout_plein.toFixed(0)} €, détour compris`
      : `dont ${s.cout_detour.toFixed(2)} € de détour`;

    li.innerHTML = `
      <div class="infos">
        ${i === 0 ? '<span class="badge">● Meilleure affaire réelle</span><br/>' : ""}
        <div class="adresse">${s.adresse}, ${s.ville}</div>
        <div class="detail">
          <b>${s.distance_km} km</b> · détour ${s.detour_km} km (~${formatMinutes(s.temps_detour_min)})
          ${s.trajet_reel ? "" : " (estimation)"}
          · ${s.volume_achete_l} L à ${s.prix_carburant.toFixed(3)} €/L
        </div>
      </div>
      <div class="cout">
        <div class="total">${headline}</div>
        <div class="sous-detail">${sousDetail}</div>
      </div>
    `;
    li.addEventListener("click", () => selectionnerStation(i));
    resultatsEl.appendChild(li);

    const marqueur = L.marker([s.lat, s.lon])
      .addTo(carte)
      .bindPopup(`<b>${s.adresse}</b><br/>${s.prix_carburant.toFixed(3)} €/L`);
    marqueur.on("click", () => selectionnerStation(i));
    marqueurs.push(marqueur);
  });

  const groupe = L.featureGroup([...marqueurs, marqueurDepart, marqueurArrivee].filter(Boolean));
  carte.fitBounds(groupe.getBounds().pad(0.2));
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const bouton = form.querySelector("button");
  bouton.disabled = true;
  message.textContent = "Recherche en cours...";
  resultatsEl.innerHTML = "";

  try {
    const departTexte = document.getElementById("depart").value.trim();
    const arriveeTexte = document.getElementById("arrivee").value.trim();

    const depart = await geocoder(departTexte);
    const arrivee = arriveeTexte ? await geocoder(arriveeTexte) : null;

    dernierDepart = [depart.lat, depart.lon];
    derniereArrivee = arrivee ? [arrivee.lat, arrivee.lon] : null;

    if (marqueurDepart) carte.removeLayer(marqueurDepart);
    if (marqueurArrivee) carte.removeLayer(marqueurArrivee);
    marqueurDepart = L.circleMarker(dernierDepart, {
      radius: 8, color: "#f5b60d", fillColor: "#f5b60d", fillOpacity: 1,
    }).addTo(carte).bindPopup("Départ");
    marqueurArrivee = derniereArrivee
      ? L.circleMarker(derniereArrivee, {
          radius: 8, color: "#2fbd6b", fillColor: "#2fbd6b", fillOpacity: 1,
        }).addTo(carte).bindPopup("Arrivée")
      : null;

    // Trace tout de suite le trajet direct départ -> arrivée (s'il y en a
    // une) ; il sera remplacé par départ -> station -> arrivée dès qu'on en
    // choisit une.
    if (derniereArrivee) {
      tracerItineraire([dernierDepart, derniereArrivee]);
    } else if (ligneItineraire) {
      carte.removeLayer(ligneItineraire);
      ligneItineraire = null;
    }

    const requete = {
      depart_lat: depart.lat,
      depart_lon: depart.lon,
      arrivee_lat: arrivee ? arrivee.lat : null,
      arrivee_lon: arrivee ? arrivee.lon : null,
      carburant: document.getElementById("carburant").value,
      type_budget: document.getElementById("type_budget").value,
      montant: parseFloat(document.getElementById("montant").value),
      consommation_l_100km: parseFloat(document.getElementById("consommation").value),
      rayon_recherche_km: parseFloat(document.getElementById("rayon").value),
    };

    const resp = await fetch("/api/recherche", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requete),
    });

    if (!resp.ok) {
      throw new Error("La recherche a échoué. Réessaie dans un instant.");
    }

    const data = await resp.json();
    message.textContent = `${data.nb_stations_analysees} station(s) analysée(s).`;
    afficherResultats(data.stations, requete.type_budget);
  } catch (err) {
    message.textContent = err.message;
  } finally {
    bouton.disabled = false;
  }
});
