const form = document.querySelector("#dig-form");
const queryInput = document.querySelector("#query");
const distanceInput = document.querySelector("#distance");
const distanceOutput = document.querySelector("#distance-output");
const moodInput = document.querySelector("#mood");
const regionInput = document.querySelector("#region");
const eraInput = document.querySelector("#era");
const challengeInput = document.querySelector("#challenge");
const results = document.querySelector("#results");
const statusEl = document.querySelector("#status");
const template = document.querySelector("#card-template");

const sessionId = getSessionId();

distanceInput.addEventListener("input", () => {
  distanceOutput.value = distanceInput.value;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  setStatus("Digging");
  results.innerHTML = `<div class="empty"><h2>Digging...</h2><p>Building candidates and asking the curator.</p></div>`;

  try {
    const payload = {
      query,
      distance_level: Number(distanceInput.value),
      region: blankToNull(regionInput.value),
      era: blankToNull(eraInput.value),
      challenge_mode: challengeInput.checked,
      mood_tags: moodInput.value
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
      session_id: sessionId,
    };

    const response = await fetch("/dig", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Dig failed");
    }

    renderRecommendations(data.recommendations || []);
    setStatus(`${data.recommendations.length} picks`);
  } catch (error) {
    results.innerHTML = `<div class="empty"><h2>Could not dig.</h2><p>${escapeHtml(error.message)}</p></div>`;
    setStatus("Error");
  }
});

function renderRecommendations(recommendations) {
  results.innerHTML = "";

  if (!recommendations.length) {
    results.innerHTML = `<div class="empty"><h2>No picks yet.</h2><p>Try another track or a wider jump.</p></div>`;
    return;
  }

  recommendations.forEach((recommendation) => {
    const card = template.content.firstElementChild.cloneNode(true);
    const validation = recommendation.validation || {};

    card.querySelector(".track-title").textContent = recommendation.title;
    card.querySelector(".track-artist").textContent = recommendation.artist;
    card.querySelector(".reason").textContent = recommendation.reason;
    card.querySelector(".confidence").textContent = `${Math.round(recommendation.confidence * 100)}%`;
    card.querySelector(".rarity").textContent = recommendation.rarity_label || "Unknown";

    const artwork = card.querySelector(".artwork");
    artwork.src = validation.artwork_url || "";
    artwork.alt = validation.album
      ? `${recommendation.title} album artwork`
      : "";

    const preview = card.querySelector(".preview");
    if (validation.preview_url) {
      preview.src = validation.preview_url;
    } else {
      preview.remove();
    }

    const external = card.querySelector(".external");
    if (validation.external_url) {
      external.href = validation.external_url;
    } else {
      external.remove();
    }

    const outboundLinks = card.querySelector(".outbound-links");
    renderOutboundLinks(outboundLinks, recommendation.outbound_links || []);

    card.querySelector(".like").addEventListener("click", () => {
      vote(card, recommendation, true);
    });
    card.querySelector(".dislike").addEventListener("click", () => {
      vote(card, recommendation, false);
    });
    card.querySelector(".share").addEventListener("click", () => {
      shareRecommendation(recommendation);
    });
    card.querySelector(".continue").addEventListener("click", () => {
      queryInput.value = `${recommendation.artist} ${recommendation.title}`;
      form.requestSubmit();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    results.append(card);
  });
}

async function shareRecommendation(recommendation) {
  const shareText = buildShareText(recommendation);
  const shareData = {
    title: `${recommendation.artist} - ${recommendation.title}`,
    text: shareText,
    url: window.location.origin,
  };

  try {
    if (navigator.share && navigator.canShare?.(shareData)) {
      await navigator.share(shareData);
      setStatus("Shared");
      return;
    }

    await navigator.clipboard.writeText(`${shareText}\n${window.location.origin}`);
    setStatus("Copied");
  } catch (error) {
    setStatus("Share failed");
  }
}

function buildShareText(recommendation) {
  const rarity = recommendation.rarity_label ? ` [${recommendation.rarity_label}]` : "";
  return [
    `Craterra pick: ${recommendation.artist} - ${recommendation.title}${rarity}`,
    recommendation.reason,
  ]
    .filter(Boolean)
    .join("\n");
}

function renderOutboundLinks(container, links) {
  container.innerHTML = "";

  if (!links.length) {
    container.remove();
    return;
  }

  links.forEach((link) => {
    const anchor = document.createElement("a");
    anchor.className = `outbound outbound-${link.service}`;
    anchor.href = link.url;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.textContent = link.label;
    container.append(anchor);
  });
}

async function vote(card, recommendation, voteValue) {
  const buttons = card.querySelectorAll(".vote");
  buttons.forEach((button) => {
    button.disabled = true;
  });

  try {
    const response = await fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        song_name: recommendation.title,
        artist_name: recommendation.artist,
        vote: voteValue,
      }),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Feedback failed");
    }
    setStatus(voteValue ? "Liked" : "Skipped");
  } catch (error) {
    buttons.forEach((button) => {
      button.disabled = false;
    });
    setStatus("Error");
  }
}

function getSessionId() {
  const key = "craterra_session_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem(key, created);
  return created;
}

function setStatus(text) {
  statusEl.textContent = text;
}

function blankToNull(value) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return entities[char];
  });
}
