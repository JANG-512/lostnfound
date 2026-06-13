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

function appendRows(targetId, rows, buildRow) {
  const target = document.querySelector(`#${targetId}`);
  if (!target) return;
  target.replaceChildren();
  rows.forEach((row) => target.append(buildRow(row)));
}

function renderContent() {
  appendRows("noticeRows", content.notice || [], (item) => {
    const tr = document.createElement("tr");
    const linked = linkCell(item.subject);
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
    tr.append(cell(item.no), linkCell(item.title).td, cell(item.weather), cell(item.date));
    return tr;
  });

  appendRows("musicRows", content.music || [], (item) => {
    const tr = document.createElement("tr");
    tr.append(cell(item.file), cell(item.memo), cell(item.time), cell(item.state));
    return tr;
  });

  appendRows("photoRows", content.photo || [], (item) => {
    const tr = document.createElement("tr");
    tr.append(cell(item.no), linkCell(item.filename).td, cell(item.memo), cell(item.date));
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

document.querySelector(".guest-form button").addEventListener("click", () => {
  const rows = document.querySelector("#guestbook");
  const notice = document.createElement("div");
  notice.className = "guest-row";
  notice.innerHTML = "<b>guest</b> 저장되지 않았습니다. 그래도 흔적은 남았습니다. <span>now</span>";
  rows.insertBefore(notice, rows.querySelector(".guest-form"));
});

renderContent();

if (window.location.hash === "#main") {
  showSite();
}
