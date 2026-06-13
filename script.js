const splash = document.querySelector("#splash");
const site = document.querySelector("#site");
const enterSite = document.querySelector("#enterSite");
const returnSplash = document.querySelector("#returnSplash");
const tabButtons = document.querySelectorAll("[data-board]");
const panels = document.querySelectorAll(".board-panel");
const content = window.LF_CONTENT || {};

function text(value) {
  return document.createTextNode(value == null ? "" : String(value));
}

function cell(value) {
  const td = document.createElement("td");
  td.append(text(value));
  return td;
}

function linkCell(label, href = "#") {
  const td = document.createElement("td");
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.append(text(label));
  td.append(anchor);
  return { td, anchor };
}

function postTitle(section, item) {
  if (section === "notice") return item.subject;
  if (section === "diary") return item.title;
  if (section === "music") return item.file;
  if (section === "photo") return item.filename;
  return "";
}

function postMeta(section, item) {
  if (section === "notice") return `${item.id || ""} / ${item.date || ""}`;
  if (section === "diary") return `${item.weather || ""} / ${item.date || ""}`;
  if (section === "music") return `${item.time || ""} / ${item.state || ""}`;
  if (section === "photo") return `${item.memo || ""} / ${item.date || ""}`;
  return "";
}

function youtubeEmbedUrl(url) {
  try {
    const parsed = new URL(url);
    let id = "";
    if (parsed.hostname.includes("youtu.be")) {
      id = parsed.pathname.slice(1).split("/")[0];
    } else if (parsed.pathname.startsWith("/embed/")) {
      id = parsed.pathname.split("/")[2];
    } else {
      id = parsed.searchParams.get("v") || "";
    }
    return id ? `https://www.youtube-nocookie.com/embed/${id}` : "";
  } catch (_error) {
    return "";
  }
}

function soundcloudEmbedUrl(url) {
  return `https://w.soundcloud.com/player/?url=${encodeURIComponent(url)}&color=%23000080&auto_play=false&hide_related=true&show_comments=false&show_user=true&show_reposts=false&show_teaser=false`;
}

function embedType(item) {
  const explicit = String(item.embedType || "").toLowerCase();
  if (explicit) return explicit;
  const url = String(item.embedUrl || "");
  if (url.includes("soundcloud.com")) return "soundcloud";
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
  return "";
}

function musicPlayer(item) {
  const wrap = document.createElement("div");
  wrap.className = "music-player";

  if (item.audioSrc) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.src = item.audioSrc;
    wrap.append(audio);
  }

  if (item.embedUrl) {
    const type = embedType(item);
    const iframe = document.createElement("iframe");
    iframe.loading = "lazy";
    iframe.allow = "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture";
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.title = item.file || "music embed";

    if (type === "soundcloud") {
      iframe.src = soundcloudEmbedUrl(item.embedUrl);
      iframe.className = "soundcloud-embed";
      wrap.append(iframe);
    } else if (type === "youtube") {
      const src = youtubeEmbedUrl(item.embedUrl);
      if (src) {
        iframe.src = src;
        iframe.className = "youtube-embed";
        wrap.append(iframe);
      }
    }
  }

  return wrap.childNodes.length ? wrap : null;
}

function openPost(section, item) {
  const target = document.querySelector(`#${section}Post`);
  if (!target) return;
  target.replaceChildren();
  target.classList.remove("hidden");

  const title = document.createElement("h3");
  title.append(text(postTitle(section, item)));

  const meta = document.createElement("div");
  meta.className = "post-meta";
  meta.append(text(postMeta(section, item)));

  const body = document.createElement("p");
  body.append(text(item.body || "아직 본문이 없습니다."));

  target.append(title, meta);
  if (section === "music") {
    const player = musicPlayer(item);
    if (player) target.append(player);
  }
  target.append(body);
}

function readableLinkCell(section, item, label) {
  const linked = linkCell(label);
  linked.anchor.addEventListener("click", (event) => {
    event.preventDefault();
    openPost(section, item);
  });
  return linked;
}

function appendRows(targetId, rows, buildRow) {
  const target = document.querySelector(`#${targetId}`);
  if (!target) return;
  target.replaceChildren();
  rows.forEach((row) => target.append(buildRow(row)));
}

function renderContent() {
  appendRows("noticeRows", content.notice || [], (item) => {
    const tr = document.createElement("tr");
    const linked = readableLinkCell("notice", item, item.subject);
    if (item.isNew) {
      linked.td.append(" ");
      const badge = document.createElement("span");
      badge.className = "new";
      badge.append("new");
      linked.td.append(badge);
    }
    tr.append(cell(item.no), linked.td, cell(item.id), cell(item.date));
    return tr;
  });

  appendRows("diaryRows", content.diary || [], (item) => {
    const tr = document.createElement("tr");
    tr.append(cell(item.no), readableLinkCell("diary", item, item.title).td, cell(item.weather), cell(item.date));
    return tr;
  });

  appendRows("musicRows", content.music || [], (item) => {
    const tr = document.createElement("tr");
    tr.append(readableLinkCell("music", item, item.file).td, cell(item.memo), cell(item.time), cell(item.state));
    return tr;
  });

  appendRows("photoRows", content.photo || [], (item) => {
    const tr = document.createElement("tr");
    tr.append(cell(item.no), readableLinkCell("photo", item, item.filename).td, cell(item.memo), cell(item.date));
    return tr;
  });

  const linkRows = document.querySelector("#linkRows");
  if (linkRows) {
    linkRows.replaceChildren();
    (content.links || []).forEach((item) => {
      const li = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.href = item.url;
      anchor.target = "_blank";
      anchor.rel = "noopener";
      anchor.append(text(item.label));
      li.append(anchor, text(` - ${item.memo || item.url}`));
      linkRows.append(li);
    });
  }
}

function showSite() {
  splash.classList.add("hidden");
  site.classList.remove("hidden");
  window.location.hash = "main";
  window.scrollTo({ top: 0, behavior: "instant" });
}

function showSplash() {
  site.classList.add("hidden");
  splash.classList.remove("hidden");
  history.replaceState(null, "", window.location.pathname);
  window.scrollTo({ top: 0, behavior: "instant" });
}

function showBoard(id) {
  tabButtons.forEach((item) => item.classList.toggle("active", item.dataset.board === id));
  panels.forEach((panel) => panel.classList.toggle("active", panel.id === id));
}

enterSite.addEventListener("click", showSite);
returnSplash.addEventListener("click", showSplash);

tabButtons.forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    showBoard(button.dataset.board);
  });
});

renderContent();

if (window.location.hash === "#main") {
  showSite();
}
