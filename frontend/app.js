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
const chainEl = document.querySelector("#dig-chain");
const chainList = document.querySelector("#chain-list");
const chainClear = document.querySelector("#chain-clear");

const sessionId = getSessionId();
const chainStorageKey = "craterra_dig_chain";
let digChain = loadDigChain();
let pendingChain = null;

renderDigChain();

distanceInput.addEventListener("input", () => {
  distanceOutput.value = distanceInput.value;
});

chainClear.addEventListener("click", () => {
  digChain = [];
  pendingChain = null;
  saveDigChain();
  renderDigChain();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  const proposedChain = pendingChain || [makeChainItem({ query })];
  pendingChain = null;
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
    digChain = proposedChain;
    saveDigChain();
    renderDigChain();
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
    renderRelationshipSummary(
      card.querySelector(".relationship-summary"),
      validation.relationship_summary || [],
    );

    const artwork = card.querySelector(".artwork");
    artwork.addEventListener("error", () => showArtworkPlaceholder(artwork));
    if (validation.artwork_url) {
      artwork.src = validation.artwork_url;
      artwork.alt = validation.album ? `${recommendation.title} album artwork` : "";
    } else {
      showArtworkPlaceholder(artwork);
    }

    const player = card.querySelector(".player");
    const preview = card.querySelector(".preview");
    if (validation.preview_url) {
      preview.src = validation.preview_url;
      setupPlayer(player, preview);
    } else {
      player.remove();
    }

    const external = card.querySelector(".external");
    if (validation.external_url) {
      external.href = validation.external_url;
    } else {
      external.remove();
    }

    const outboundLinks = card.querySelector(".outbound-links");
    renderOutboundLinks(outboundLinks, recommendation.outbound_links || [], recommendation);

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
      pendingChain = appendChainItem(digChain, makeChainItem(recommendation));
      form.requestSubmit();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    results.append(card);
  });
}

function setupPlayer(player, audio) {
  player.hidden = false;
  const toggle = player.querySelector(".player-toggle");
  const track = player.querySelector(".player-track");
  const progress = player.querySelector(".player-progress");
  const time = player.querySelector(".player-time");

  toggle.addEventListener("click", () => {
    if (audio.paused) {
      document.querySelectorAll("audio.preview").forEach((other) => {
        if (other !== audio) other.pause();
      });
      audio.play().catch(() => setStatus("Preview unavailable"));
    } else {
      audio.pause();
    }
  });

  audio.addEventListener("play", () => player.classList.add("is-playing"));
  audio.addEventListener("pause", () => player.classList.remove("is-playing"));
  audio.addEventListener("ended", () => {
    player.classList.remove("is-playing");
    progress.style.width = "0%";
  });
  audio.addEventListener("loadedmetadata", () => {
    time.textContent = formatTime(audio.duration);
  });
  audio.addEventListener("timeupdate", () => {
    const ratio = audio.duration ? audio.currentTime / audio.duration : 0;
    progress.style.width = `${ratio * 100}%`;
    time.textContent = formatTime(audio.duration - audio.currentTime);
  });

  track.addEventListener("click", (event) => {
    if (!audio.duration) return;
    const rect = track.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    audio.currentTime = ratio * audio.duration;
  });
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function showArtworkPlaceholder(artwork) {
  artwork.removeAttribute("src");
  artwork.alt = "";
  artwork.classList.add("artwork-empty");
}

function renderDigChain() {
  chainList.innerHTML = "";
  chainEl.hidden = !digChain.length;

  digChain.forEach((item, index) => {
    const node = document.createElement("li");
    node.className = index === digChain.length - 1 ? "chain-item chain-current" : "chain-item";

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.label;
    button.addEventListener("click", () => {
      queryInput.value = item.query;
      pendingChain = digChain.slice(0, index + 1);
      form.requestSubmit();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    node.append(button);
    chainList.append(node);
  });
}

function makeChainItem(source) {
  const query =
    source.query ||
    [source.artist, source.title]
      .filter(Boolean)
      .join(" ")
      .trim();
  const label =
    source.artist && source.title ? `${source.artist} - ${source.title}` : query;

  return {
    query,
    label,
  };
}

function appendChainItem(chain, item) {
  const nextChain = chain.length ? [...chain] : [makeChainItem({ query: queryInput.value.trim() })];
  const last = nextChain[nextChain.length - 1];
  if (!last || normalizeChainKey(last.query) !== normalizeChainKey(item.query)) {
    nextChain.push(item);
  }
  return nextChain.slice(-8);
}

function loadDigChain() {
  try {
    const parsed = JSON.parse(localStorage.getItem(chainStorageKey) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) => item && typeof item.query === "string" && typeof item.label === "string")
      .slice(-8);
  } catch (error) {
    return [];
  }
}

function saveDigChain() {
  localStorage.setItem(chainStorageKey, JSON.stringify(digChain));
}

function normalizeChainKey(value) {
  return value.toLowerCase().trim().replace(/\s+/g, " ");
}

function renderRelationshipSummary(container, relationships) {
  container.innerHTML = "";

  if (!relationships.length) {
    container.remove();
    return;
  }

  relationships.slice(0, 4).forEach((relationship) => {
    const item = document.createElement("li");
    item.textContent = relationship;
    container.append(item);
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

function renderOutboundLinks(container, links, recommendation) {
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
    anchor.addEventListener("click", () => {
      trackOutboundClick(link, recommendation);
    });
    container.append(anchor);
  });
}

function trackOutboundClick(link, recommendation) {
  const payload = JSON.stringify({
    session_id: sessionId,
    service: link.service,
    song_name: recommendation.title,
    artist_name: recommendation.artist,
    url: link.url,
  });

  if (navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "application/json" });
    if (navigator.sendBeacon("/outbound-click", blob)) {
      return;
    }
  }

  fetch("/outbound-click", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
    keepalive: true,
  }).catch(() => {});
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
