import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
  addDoc,
  collection,
  getFirestore,
  limit,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-firestore.js";

const config = window.LF_GUESTBOOK_CONFIG || {};
const form = document.querySelector("#guestbookForm");
const nameInput = document.querySelector("#guestName");
const messageInput = document.querySelector("#guestMessage");
const trapInput = document.querySelector("#guestWebsite");
const statusEl = document.querySelector("#guestbookStatus");
const listEl = document.querySelector("#guestbookList");

function setStatus(message, isError = false) {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function text(value) {
  return document.createTextNode(value == null ? "" : String(value));
}

function formatDate(value) {
  const date = value?.toDate ? value.toDate() : null;
  if (!date) return "now";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function clean(value, maxLength) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maxLength);
}

function renderEntries(snapshot) {
  listEl.replaceChildren();
  if (snapshot.empty) {
    const empty = document.createElement("div");
    empty.className = "guestbook-empty";
    empty.append(text("아직 남겨진 흔적이 없습니다."));
    listEl.append(empty);
    return;
  }

  snapshot.forEach((doc) => {
    const entry = doc.data();
    const row = document.createElement("article");
    row.className = "guestbook-entry";

    const head = document.createElement("div");
    head.className = "guestbook-entry-head";
    const name = document.createElement("b");
    name.append(text(entry.name || "guest"));
    const date = document.createElement("span");
    date.append(text(formatDate(entry.createdAt)));
    head.append(name, date);

    const message = document.createElement("p");
    message.append(text(entry.message || ""));

    row.append(head, message);
    listEl.append(row);
  });
}

function missingConfig() {
  const firebase = config.firebase || {};
  return !config.enabled || !firebase.apiKey || !firebase.projectId || !firebase.appId;
}

function initGuestbook() {
  if (!form || !listEl) return;

  const savedName = localStorage.getItem("lfGuestName");
  if (savedName) nameInput.value = savedName;

  if (missingConfig()) {
    setStatus("방명록 DB 설정이 필요합니다. guestbook-config.js에 Firebase 설정을 넣어주세요.", true);
    form.querySelector("button").disabled = true;
    return;
  }

  const app = initializeApp(config.firebase);
  const db = getFirestore(app);
  const entries = collection(db, config.collection || "guestbook");
  const entriesQuery = query(entries, orderBy("createdAt", "desc"), limit(50));

  onSnapshot(
    entriesQuery,
    renderEntries,
    (error) => setStatus(`방명록을 불러오지 못했습니다: ${error.message}`, true)
  );

  setStatus("방명록이 연결되었습니다.");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (trapInput.value) return;

    const name = clean(nameInput.value || "guest", 24) || "guest";
    const message = clean(messageInput.value, 500);
    if (!message) {
      setStatus("메시지를 입력해주세요.", true);
      return;
    }

    form.querySelector("button").disabled = true;
    try {
      await addDoc(entries, {
        name,
        message,
        createdAt: serverTimestamp()
      });
      localStorage.setItem("lfGuestName", name);
      messageInput.value = "";
      setStatus("흔적이 남았습니다.");
    } catch (error) {
      setStatus(`저장하지 못했습니다: ${error.message}`, true);
    } finally {
      form.querySelector("button").disabled = false;
    }
  });
}

initGuestbook();
