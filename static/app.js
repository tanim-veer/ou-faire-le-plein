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

function afficherResultats(stations, typeBudget) {
  resultatsEl.innerHTML = "";
  viderMarqueurs();

  if (stations.length === 0) {
    message.textContent = "Aucune station trouvée avec ce carburant dans le rayon choisi.";
    return;
  }

  stations.forEach((s, i) => {
    const li = document.createElement("li");
    li.className = "station" + (i === 0 ? " top" : "");

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
    resultatsEl.appendChild(li);

    const marqueur = L.marker([s.lat, s.lon])
      .addTo(carte)
      .bindPopup(`<b>${s.adresse}</b><br/>${s.prix_carburant.toFixed(3)} €/L`);
    marqueurs.push(marqueur);
  });

  const groupe = L.featureGroup(marqueurs);
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
