let currentTab = "humanities";
let currentVideos = [];

function showToast(msg) {
  const t = document.getElementById("toast");
  t.innerText = msg;
  t.style.display = "block";
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => t.style.display = "none", 2200);
}

function formatDur(sec) {
  if (!sec || sec === 0) return "";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function copyMpv(url) {
  navigator.clipboard.writeText(`mpv "${url}"`).then(() => showToast(`Copied: mpv "${url}"`));
}

function openModal(vid) {
  const v = currentVideos.find(x => x.vid === vid);
  if (!v) return;
  document.getElementById("modal-title").innerText = v.title;
  document.getElementById("modal-channel").innerText = (v.channel || "") + (v.duration_sec ? " · " + formatDur(v.duration_sec) : "");
  document.getElementById("modal-summary").innerText = v.summary || "No summary available.";
  document.getElementById("modal-iframe").src = `https://www.youtube-nocookie.com/embed/${v.vid}?rel=0&modestbranding=1`;
  document.getElementById("modal-yt-link").href = v.url;
  document.getElementById("modal-mpv-btn").onclick = () => copyMpv(v.url);
  document.getElementById("modal-star-btn").innerText = v.starred ? "★ Starred" : "☆ Star";
  document.getElementById("modal-star-btn").onclick = () => toggleStarModal(v.vid);
  document.getElementById("video-modal").style.display = "flex";
}

function closeModal() {
  document.getElementById("modal-iframe").src = "";
  document.getElementById("video-modal").style.display = "none";
}

async function toggleStar(vid, btn) {
  const res = await fetch(`/api/video/${vid}/star`, { method: "POST" });
  const d = await res.json();
  if (d.starred) {
    btn.classList.add("starred");
    btn.innerText = "★";
    showToast("Starred");
  } else {
    btn.classList.remove("starred");
    btn.innerText = "☆";
    showToast("Unstarred");
  }
  const v = currentVideos.find(x => x.vid === vid);
  if (v) v.starred = d.starred;
}

async function toggleStarModal(vid) {
  const res = await fetch(`/api/video/${vid}/star`, { method: "POST" });
  const d = await res.json();
  document.getElementById("modal-star-btn").innerText = d.starred ? "★ Starred" : "☆ Star";
  const v = currentVideos.find(x => x.vid === vid);
  if (v) v.starred = d.starred;
  showToast(d.starred ? "Starred" : "Unstarred");
}

function renderCards(videos) {
  currentVideos = videos;
  const grid = document.getElementById("video-grid");
  const count = document.getElementById("result-count");
  grid.innerHTML = "";
  count.innerText = `${videos.length} talks`;

  if (videos.length === 0) {
    grid.innerHTML = `<p style="grid-column:1/-1; text-align:center; color:#555; padding:30px 0;">No results found.</p>`;
    return;
  }

  videos.forEach(v => {
    const scholars = JSON.parse(v.scholar_matches || "[]").filter((s, i, a) => a.indexOf(s) === i);
    const disciplines = JSON.parse(v.disciplines || "[]").filter((d, i, a) => a.indexOf(d) === i);

    // Thumbnail: use automatic mid-video frame (hq2.jpg) which requires no API key
    const thumbUrl = `https://i.ytimg.com/vi/${v.vid}/hq2.jpg`;

    let badgesHtml = scholars.slice(0, 2).map(s => `<span class="badge badge-scholar">${s}</span>`).join("");
    disciplines.slice(0, 1).forEach(d => { badgesHtml += `<span class="badge">${d.replace(/-/g, ' ')}</span>`; });

    const dur = formatDur(v.duration_sec);
    const starClass = v.starred ? "starred" : "";
    const starIcon = v.starred ? "★" : "☆";

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <img class="thumb" src="${thumbUrl}" alt="" loading="lazy" onerror="this.style.display='none'" onclick="openModal('${v.vid}')">
      <div class="card-body" onclick="openModal('${v.vid}')">
        <div class="card-title">${v.title}</div>
        <div class="card-channel">${v.channel || ""}</div>
        <div class="card-meta">
          <span>${dur}</span>
          <span>${v.score ? v.score.toFixed(1) : ""}</span>
        </div>
        <div class="card-badges">${badgesHtml}</div>
      </div>
      <div class="card-actions">
        <button onclick="event.stopPropagation(); copyMpv('${v.url}')">mpv</button>
        <button class="${starClass}" onclick="event.stopPropagation(); toggleStar('${v.vid}', this)">${starIcon}</button>
      </div>
    `;
    grid.appendChild(card);
  });
}

async function loadVideos(randomise) {
  const q = document.getElementById("search-input").value;
  const disc = document.getElementById("disc-select").value;
  const rand = randomise !== undefined ? randomise : false;
  const params = new URLSearchParams({ tab: currentTab, q, discipline: disc, random: rand ? "1" : "0" });
  try {
    const res = await fetch(`/api/videos?${params}`);
    const data = await res.json();
    renderCards(data.videos || []);
  } catch (e) { console.error(e); }
}

function setTab(tab, btn) {
  currentTab = tab;
  document.querySelectorAll("nav button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  loadVideos();
}

document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") {
    if (e.key === "Escape") e.target.blur();
    return;
  }
  if (e.key === "Escape") closeModal();
  if (e.key === "/") { e.preventDefault(); document.getElementById("search-input").focus(); }
  if (e.key === "r") loadVideos(true);
});

window.onload = () => loadVideos(true); // randomise on first open
