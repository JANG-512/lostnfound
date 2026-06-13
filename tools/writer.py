#!/usr/bin/env python3
"""Local browser writer for Lost & Found public content.

The public site is static. This tool runs a local-only HTTP server, opens a
browser editor, saves public data to content.js, and can optionally commit and
push that public data to GitHub Pages.
"""

from __future__ import annotations

import json
import os
import base64
import re
import socket
import subprocess
import tempfile
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "content.js"
ASSETS_AUDIO_DIR = ROOT / "assets" / "audio"
PRIVATE_DIR = ROOT / "private"
VAULT_PATH = PRIVATE_DIR / "lostfound-vault.enc"
OPENSSL = "/usr/bin/openssl"
HOST = "127.0.0.1"
PORT = 5127

DEFAULT_CONTENT = {
    "notice": [
        {
            "no": "04",
            "subject": "비밀문서는 천천히 열립니다.",
            "id": "sysop",
            "date": "99.12.07",
            "isNew": True,
            "body": "문이 열리기 전까지는 목록에 제목만 남겨둡니다.",
        },
        {
            "no": "03",
            "subject": "끊어진 신호는 그대로 보관합니다.",
            "id": "sysop",
            "date": "99.12.06",
            "body": "끊어진 신호도 이곳에서는 하나의 글이 됩니다.",
        },
    ],
    "diary": [
        {
            "no": "12",
            "title": "서랍 안쪽에서 발견한 테이프",
            "weather": "흐림",
            "date": "00.01.03",
            "body": "라벨이 지워진 테이프 안에는 아직 확인하지 못한 소리가 남아있다.",
        },
    ],
    "music": [
        {
            "file": "01_lost.wav",
            "memo": "아직 열리지 않음",
            "time": "--:--",
            "state": "hidden",
            "audioSrc": "",
            "embedType": "",
            "embedUrl": "",
            "body": "파일 설명, 가사 메모, 공개 전 코멘트를 이곳에 적습니다.",
        },
    ],
    "photo": [
        {
            "no": "07",
            "filename": "scan_1207.jpg",
            "memo": "색이 많이 바랬음",
            "date": "99.12.07",
            "body": "사진에 대한 기억이나 설명을 이곳에 적습니다.",
        },
    ],
    "links": [
        {"label": "YouTube", "url": "https://www.youtube.com/@wlsdnr123a", "memo": "video archive"},
        {"label": "SoundCloud", "url": "https://soundcloud.com/jangjinuk", "memo": "sound data"},
        {"label": "Instagram", "url": "https://www.instagram.com/j1nuk_jang", "memo": "photo log"},
    ],
}

SECTIONS = {
    "notice": {"label": "공지사항", "fields": ["no", "subject", "id", "date", "isNew", "body"], "title": ["no", "subject"]},
    "diary": {"label": "일기장", "fields": ["no", "title", "weather", "date", "body"], "title": ["no", "title"]},
    "music": {"label": "자료실", "fields": ["file", "memo", "time", "state", "audioSrc", "embedType", "embedUrl", "body"], "title": ["file", "memo"]},
    "photo": {"label": "사진첩", "fields": ["no", "filename", "memo", "date", "body"], "title": ["no", "filename"]},
    "links": {"label": "링크", "fields": ["label", "url", "memo"], "title": ["label", "url"]},
}


def extract_json_from_content_js() -> dict[str, Any]:
    if not CONTENT_PATH.exists():
        return DEFAULT_CONTENT
    text = CONTENT_PATH.read_text(encoding="utf-8").strip()
    prefix = "window.LF_CONTENT = "
    if text.startswith(prefix):
        text = text[len(prefix):].rstrip(";").strip()
    return json.loads(text)


def normalize_content(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for section in SECTIONS:
        rows = data.get(section, [])
        normalized[section] = rows if isinstance(rows, list) else []
    return normalized


def write_content_js(data: dict[str, Any]) -> None:
    pretty = json.dumps(normalize_content(data), ensure_ascii=False, indent=2)
    CONTENT_PATH.write_text(f"window.LF_CONTENT = {pretty};\n", encoding="utf-8")


def encrypt_vault(data: dict[str, Any], passphrase: str) -> None:
    PRIVATE_DIR.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        json.dump(normalize_content(data), tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            [
                OPENSSL,
                "enc",
                "-aes-256-cbc",
                "-pbkdf2",
                "-salt",
                "-in",
                str(tmp_path),
                "-out",
                str(VAULT_PATH),
                "-pass",
                f"pass:{passphrase}",
            ],
            check=True,
            capture_output=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def decrypt_vault(passphrase: str) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("r", encoding="utf-8", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            [
                OPENSSL,
                "enc",
                "-d",
                "-aes-256-cbc",
                "-pbkdf2",
                "-in",
                str(VAULT_PATH),
                "-out",
                str(tmp_path),
                "-pass",
                f"pass:{passphrase}",
            ],
            check=True,
            capture_output=True,
        )
        return json.loads(tmp_path.read_text(encoding="utf-8"))
    finally:
        tmp_path.unlink(missing_ok=True)


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def has_public_changes() -> bool:
    paths = [str(CONTENT_PATH.relative_to(ROOT))]
    if ASSETS_AUDIO_DIR.exists():
        paths.append(str(ASSETS_AUDIO_DIR.relative_to(ROOT)))
    result = subprocess.run(
        ["git", "status", "--short", "--", *paths],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return bool(result.stdout.strip())


def safe_audio_filename(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}:
        raise ValueError("Upload an audio file: mp3, m4a, wav, ogg, flac, or aac.")
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-") or "audio"
    return f"{stem}-{datetime.now().strftime('%Y%m%d%H%M%S')}{suffix}"


def save_uploaded_audio(filename: str, data_url: str) -> str:
    if "," not in data_url:
        raise ValueError("Invalid upload data.")
    _header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)
    if len(data) > 100 * 1024 * 1024:
        raise ValueError("Audio file is too large. Keep uploads under 100 MB.")
    ASSETS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = safe_audio_filename(filename)
    path = ASSETS_AUDIO_DIR / safe_name
    path.write_bytes(data)
    return f"assets/audio/{safe_name}"


def publish_content(data: dict[str, Any], passphrase: str = "") -> str:
    write_content_js(data)
    if passphrase:
        encrypt_vault(data, passphrase)
    if not has_public_changes():
        return "content.js and audio assets did not change. Nothing to publish."
    add_paths = ["content.js"]
    if ASSETS_AUDIO_DIR.exists():
        add_paths.append(str(ASSETS_AUDIO_DIR.relative_to(ROOT)))
    run_git(["add", *add_paths])
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    run_git(["commit", "-m", f"Update site content {stamp}"])
    run_git(["push"])
    return "Committed content.js and pushed to GitHub."


ADMIN_HTML = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lost & Found Writer</title>
  <style>
    :root { color-scheme: light; --ink: #1d1d1f; --muted: #6b7280; --line: #c9cdd3; --panel: #f6f7f9; --accent: #0033cc; }
    * { box-sizing: border-box; }
    body { margin: 0; color: var(--ink); background: #e8eaee; font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }
    header { display: flex; gap: 12px; align-items: center; justify-content: space-between; padding: 12px 14px; background: #111; color: #fff; }
    h1 { margin: 0; font-size: 17px; letter-spacing: 0; }
    main { display: grid; grid-template-columns: 220px minmax(280px, 1fr) 360px; gap: 10px; padding: 10px; min-height: calc(100vh - 54px); }
    section, aside { border: 1px solid var(--line); background: #fff; }
    button, input, textarea { font: inherit; }
    button { min-height: 32px; border: 1px solid #9da3ad; background: #fff; color: #111; cursor: pointer; }
    button:hover { background: #f0f3f8; }
    button.primary { border-color: #001f88; background: var(--accent); color: #fff; }
    button.danger { border-color: #9b1c1c; color: #9b1c1c; }
    input, textarea { width: 100%; min-height: 32px; padding: 5px 7px; border: 1px solid #aeb4bf; background: #fff; }
    textarea { min-height: 220px; resize: vertical; line-height: 1.5; }
    .upload-row { display: grid; grid-template-columns: 1fr auto; gap: 6px; }
    .upload-row input[type="file"] { padding: 4px; }
    .hint { color: var(--muted); font-size: 12px; }
    label { display: grid; gap: 4px; color: var(--muted); font-size: 12px; }
    .tabs { padding: 8px; }
    .tabs button { width: 100%; margin-bottom: 6px; text-align: left; padding: 6px 9px; }
    .tabs button.active { background: #dfe7ff; border-color: #6f8dff; color: #001f88; font-weight: 700; }
    .list { min-height: 0; display: grid; grid-template-rows: auto 1fr; }
    .list-title, .form-title { padding: 8px 10px; border-bottom: 1px solid var(--line); background: var(--panel); font-weight: 700; }
    .items { overflow: auto; }
    .item { display: block; width: 100%; min-height: 38px; padding: 7px 10px; border: 0; border-bottom: 1px solid #eceff3; background: #fff; text-align: left; }
    .item.active { background: #fff7c2; }
    .form { display: grid; grid-template-rows: auto 1fr auto; min-height: 0; }
    .fields { display: grid; align-content: start; gap: 9px; padding: 10px; overflow: auto; }
    .check-row { display: flex; align-items: center; gap: 8px; color: var(--ink); font-size: 14px; }
    .check-row input { width: auto; min-height: auto; }
    .actions { display: flex; flex-wrap: wrap; gap: 7px; padding: 10px; border-top: 1px solid var(--line); background: var(--panel); }
    .toolbar { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
    .toolbar input { width: 210px; background: #fff; color: #111; }
    .status { min-height: 22px; padding: 4px 10px; color: #103b14; background: #e6f5e7; border-top: 1px solid #bddfc0; }
    .error { color: #7f1d1d; background: #fee2e2; border-color: #fecaca; }
    @media (max-width: 860px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>Lost & Found Writer</h1>
    <div class="toolbar">
      <input id="passphrase" type="password" placeholder="vault passphrase">
      <button id="loadPublic">Load content.js</button>
      <button id="openVault">Open vault</button>
      <button id="saveVault">Save vault + public</button>
      <button id="savePublic" class="primary">Save public</button>
      <button id="publish">Save & Publish</button>
    </div>
  </header>
  <main>
    <aside class="tabs" id="tabs"></aside>
    <section class="list">
      <div class="list-title" id="listTitle"></div>
      <div class="items" id="items"></div>
      <div class="status" id="status">Loading...</div>
    </section>
    <section class="form">
      <div class="form-title" id="formTitle"></div>
      <div class="fields" id="fields"></div>
      <div class="actions">
        <button id="newItem">New</button>
        <button id="addItem">Add</button>
        <button id="updateItem">Update</button>
        <button id="deleteItem" class="danger">Delete</button>
      </div>
    </section>
  </main>
  <script>
    const sections = __SECTIONS__;
    let data = {};
    let current = "notice";
    let selected = null;

    const tabs = document.querySelector("#tabs");
    const items = document.querySelector("#items");
    const fields = document.querySelector("#fields");
    const statusEl = document.querySelector("#status");
    const listTitle = document.querySelector("#listTitle");
    const formTitle = document.querySelector("#formTitle");

    function setStatus(message, isError = false) {
      statusEl.textContent = message;
      statusEl.classList.toggle("error", isError);
    }

    async function api(path, body) {
      const response = await fetch(path, {
        method: body ? "POST" : "GET",
        headers: body ? {"Content-Type": "application/json"} : {},
        body: body ? JSON.stringify(body) : undefined
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Request failed");
      return payload;
    }

    function readAsDataURL(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
    }

    async function uploadAudio(file) {
      const dataUrl = await readAsDataURL(file);
      return api("/api/upload-audio", {filename: file.name, dataUrl});
    }

    function titleFor(section, item) {
      const keys = sections[section].title;
      return keys.map((key) => item[key] || "").filter(Boolean).join("  ") || "(empty)";
    }

    function renderTabs() {
      tabs.replaceChildren();
      Object.entries(sections).forEach(([key, meta]) => {
        const button = document.createElement("button");
        button.textContent = meta.label;
        button.className = key === current ? "active" : "";
        button.onclick = () => { current = key; selected = null; render(); };
        tabs.append(button);
      });
    }

    function renderItems() {
      items.replaceChildren();
      (data[current] || []).forEach((item, index) => {
        const button = document.createElement("button");
        button.className = "item" + (index === selected ? " active" : "");
        button.textContent = titleFor(current, item);
        button.onclick = () => { selected = index; renderFields(item); renderItems(); };
        items.append(button);
      });
    }

    function renderFields(item = {}) {
      fields.replaceChildren();
      sections[current].fields.forEach((name) => {
        if (name === "isNew") {
          const label = document.createElement("label");
          label.className = "check-row";
          const input = document.createElement("input");
          input.type = "checkbox";
          input.id = "field-" + name;
          input.checked = Boolean(item[name]);
          label.append(input, "new 표시");
          fields.append(label);
          return;
        }
        const label = document.createElement("label");
        label.textContent = name === "body" ? "본문" : name;
        const input = document.createElement(name === "body" ? "textarea" : "input");
        input.id = "field-" + name;
        input.value = item[name] || "";
        if (current === "music" && name === "audioSrc") {
          const row = document.createElement("div");
          row.className = "upload-row";
          const picker = document.createElement("input");
          picker.type = "file";
          picker.accept = "audio/*,.mp3,.m4a,.wav,.ogg,.flac,.aac";
          picker.onchange = async () => {
            if (!picker.files.length) return;
            try {
              setStatus("uploading audio...");
              const payload = await uploadAudio(picker.files[0]);
              input.value = payload.path;
              const fileField = document.querySelector("#field-file");
              if (fileField && !fileField.value) fileField.value = picker.files[0].name;
              setStatus("audio uploaded to " + payload.path);
            } catch (error) {
              setStatus(error.message, true);
            }
          };
          row.append(input, picker);
          label.append(row);
          const hint = document.createElement("div");
          hint.className = "hint";
          hint.textContent = "로컬 음원은 assets/audio/에 저장됩니다. mp3, m4a, wav, ogg, flac, aac 지원.";
          label.append(hint);
        } else {
          label.append(input);
        }
        if (current === "music" && name === "embedType") {
          const hint = document.createElement("div");
          hint.className = "hint";
          hint.textContent = "soundcloud, youtube, 또는 비워두면 URL로 자동 판별";
          label.append(hint);
        }
        if (current === "music" && name === "embedUrl") {
          const hint = document.createElement("div");
          hint.className = "hint";
          hint.textContent = "SoundCloud 트랙 URL이나 YouTube URL을 넣으면 본문에 임베드됩니다.";
          label.append(hint);
        }
        fields.append(label);
      });
    }

    function formItem() {
      const item = {};
      sections[current].fields.forEach((name) => {
        const input = document.querySelector("#field-" + name);
        if (name === "isNew") {
          if (input.checked) item[name] = true;
        } else {
          item[name] = input.value;
        }
      });
      return item;
    }

    function render() {
      renderTabs();
      listTitle.textContent = sections[current].label + " 목록";
      formTitle.textContent = sections[current].label + " 작성";
      renderItems();
      renderFields(selected == null ? {} : data[current][selected]);
    }

    async function loadPublic() {
      const payload = await api("/api/content");
      data = payload.data;
      selected = null;
      render();
      setStatus("content.js loaded");
    }

    document.querySelector("#loadPublic").onclick = () => loadPublic().catch((error) => setStatus(error.message, true));
    document.querySelector("#openVault").onclick = async () => {
      try {
        const passphrase = document.querySelector("#passphrase").value;
        const payload = await api("/api/vault/open", {passphrase});
        data = payload.data;
        selected = null;
        render();
        setStatus("vault loaded");
      } catch (error) { setStatus(error.message, true); }
    };
    document.querySelector("#savePublic").onclick = async () => {
      try {
        await api("/api/save", {data});
        setStatus("content.js saved");
      } catch (error) { setStatus(error.message, true); }
    };
    document.querySelector("#saveVault").onclick = async () => {
      try {
        const passphrase = document.querySelector("#passphrase").value;
        await api("/api/vault/save", {passphrase, data});
        setStatus("vault and content.js saved");
      } catch (error) { setStatus(error.message, true); }
    };
    document.querySelector("#publish").onclick = async () => {
      if (!confirm("content.js를 저장하고 GitHub에 commit/push할까요?")) return;
      try {
        const passphrase = document.querySelector("#passphrase").value;
        const payload = await api("/api/publish", {passphrase, data});
        setStatus(payload.message);
      } catch (error) { setStatus(error.message, true); }
    };
    document.querySelector("#newItem").onclick = () => { selected = null; renderFields({}); renderItems(); };
    document.querySelector("#addItem").onclick = () => {
      data[current] ||= [];
      data[current].unshift(formItem());
      selected = 0;
      render();
      setStatus("added");
    };
    document.querySelector("#updateItem").onclick = () => {
      if (selected == null) return setStatus("수정할 항목을 먼저 선택하세요.", true);
      data[current][selected] = formItem();
      render();
      setStatus("updated");
    };
    document.querySelector("#deleteItem").onclick = () => {
      if (selected == null) return setStatus("삭제할 항목을 먼저 선택하세요.", true);
      data[current].splice(selected, 1);
      selected = null;
      render();
      setStatus("deleted");
    };

    loadPublic().catch((error) => setStatus(error.message, true));
  </script>
</body>
</html>"""


class WriterHandler(BaseHTTPRequestHandler):
    server_version = "LostFoundWriter/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/writer"}:
            html = ADMIN_HTML.replace("__SECTIONS__", json.dumps(SECTIONS, ensure_ascii=False))
            self.send_text(html, "text/html; charset=utf-8")
            return
        if path == "/api/content":
            self.send_json({"data": normalize_content(extract_json_from_content_js())})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/save":
                write_content_js(payload.get("data", {}))
                self.send_json({"ok": True})
            elif path == "/api/vault/open":
                passphrase = self.require_passphrase(payload)
                if not VAULT_PATH.exists():
                    raise ValueError("No encrypted vault exists yet. Save once to create it.")
                self.send_json({"data": normalize_content(decrypt_vault(passphrase))})
            elif path == "/api/vault/save":
                passphrase = self.require_passphrase(payload)
                data = payload.get("data", {})
                write_content_js(data)
                encrypt_vault(data, passphrase)
                self.send_json({"ok": True})
            elif path == "/api/publish":
                message = publish_content(payload.get("data", {}), payload.get("passphrase", ""))
                self.send_json({"ok": True, "message": message})
            elif path == "/api/upload-audio":
                filename = str(payload.get("filename", ""))
                data_url = str(payload.get("dataUrl", ""))
                if not filename or not data_url:
                    raise ValueError("Choose an audio file first.")
                self.send_json({"ok": True, "path": save_uploaded_audio(filename, data_url)})
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            self.send_json({"error": detail}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def require_passphrase(self, payload: dict[str, Any]) -> str:
        passphrase = str(payload.get("passphrase", ""))
        if not passphrase:
            raise ValueError("Enter the vault passphrase first.")
        return passphrase

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_text(json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8", status)

    def send_text(self, text: str, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[writer] {self.address_string()} - {fmt % args}")


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex((HOST, PORT)) != 0:
            return PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def main() -> None:
    port = pick_port()
    server = ThreadingHTTPServer((HOST, port), WriterHandler)
    url = f"http://{HOST}:{port}/"
    print(f"Lost & Found Writer is running at {url}", flush=True)
    print("Keep this Terminal window open while editing. Press Ctrl-C to stop.", flush=True)
    if not os.environ.get("LF_WRITER_NO_BROWSER"):
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping writer.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
