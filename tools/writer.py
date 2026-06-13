#!/usr/bin/env python3
"""Local macOS writer for Lost & Found public content.

The writer stores editable source data in an encrypted local vault and exports
public website data to content.js. The private vault is ignored by git.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Entry, Frame, Label, Tk, messagebox
from tkinter.scrolledtext import ScrolledText

ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "content.js"
PRIVATE_DIR = ROOT / "private"
VAULT_PATH = PRIVATE_DIR / "lostfound-vault.enc"
OPENSSL = "/usr/bin/openssl"

DEFAULT_CONTENT = {
    "notice": [
        {"no": "04", "subject": "비밀문서는 천천히 열립니다.", "id": "sysop", "date": "99.12.07", "isNew": True},
        {"no": "03", "subject": "끊어진 신호는 그대로 보관합니다.", "id": "sysop", "date": "99.12.06"},
    ],
    "diary": [
        {"no": "12", "title": "서랍 안쪽에서 발견한 테이프", "weather": "흐림", "date": "00.01.03"},
    ],
    "music": [
        {"file": "01_lost.wav", "memo": "아직 열리지 않음", "time": "--:--", "state": "hidden"},
    ],
    "photo": [
        {"no": "07", "filename": "scan_1207.jpg", "memo": "색이 많이 바랬음", "date": "99.12.07"},
    ],
    "links": [
        {"label": "YouTube", "url": "https://www.youtube.com/@wlsdnr123a", "memo": "video archive"},
        {"label": "SoundCloud", "url": "https://soundcloud.com/jangjinuk", "memo": "sound data"},
        {"label": "Instagram", "url": "https://www.instagram.com/j1nuk_jang", "memo": "photo log"},
    ],
}


def extract_json_from_content_js() -> dict:
    if not CONTENT_PATH.exists():
        return DEFAULT_CONTENT
    text = CONTENT_PATH.read_text(encoding="utf-8").strip()
    prefix = "window.LF_CONTENT = "
    if text.startswith(prefix):
        text = text[len(prefix):].rstrip(";").strip()
    return json.loads(text)


def encrypt_vault(data: dict, passphrase: str) -> None:
    PRIVATE_DIR.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
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


def decrypt_vault(passphrase: str) -> dict:
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


def write_content_js(data: dict) -> None:
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    CONTENT_PATH.write_text(f"window.LF_CONTENT = {pretty};\n", encoding="utf-8")


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def has_public_content_changes() -> bool:
    result = subprocess.run(
        ["git", "status", "--short", "--", str(CONTENT_PATH.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return bool(result.stdout.strip())


class WriterApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Lost & Found Writer")
        self.root.geometry("820x640")

        top = Frame(self.root)
        top.pack(fill=X, padx=10, pady=8)
        Label(top, text="Vault passphrase").pack(side=LEFT)
        self.passphrase = Entry(top, show="*", width=32)
        self.passphrase.pack(side=LEFT, padx=8)
        Button(top, text="Open encrypted vault", command=self.open_vault).pack(side=LEFT)
        Button(top, text="Load public content.js", command=self.load_public).pack(side=LEFT, padx=5)

        self.editor = ScrolledText(self.root, wrap="none", font=("Menlo", 12))
        self.editor.pack(fill=BOTH, expand=True, padx=10, pady=6)

        bottom = Frame(self.root)
        bottom.pack(fill=X, padx=10, pady=8)
        Button(bottom, text="Save & Publish to GitHub", command=self.save_and_publish).pack(side=RIGHT)
        Button(bottom, text="Save encrypted vault + public content.js", command=self.save_all).pack(side=RIGHT)
        Button(bottom, text="Validate JSON", command=self.validate).pack(side=RIGHT, padx=6)

        self.load_public()

    def current_data(self) -> dict:
        return json.loads(self.editor.get("1.0", END))

    def put_data(self, data: dict) -> None:
        self.editor.delete("1.0", END)
        self.editor.insert("1.0", json.dumps(data, ensure_ascii=False, indent=2))

    def load_public(self) -> None:
        try:
            self.put_data(extract_json_from_content_js())
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))

    def open_vault(self) -> None:
        phrase = self.passphrase.get()
        if not phrase:
            messagebox.showwarning("Missing passphrase", "Enter the vault passphrase first.")
            return
        if not VAULT_PATH.exists():
            messagebox.showinfo("No vault yet", "No encrypted vault exists yet. Save once to create it.")
            return
        try:
            self.put_data(decrypt_vault(phrase))
            messagebox.showinfo("Vault opened", f"Loaded {VAULT_PATH}")
        except Exception as exc:
            messagebox.showerror("Vault open failed", str(exc))

    def validate(self) -> None:
        try:
            self.current_data()
            messagebox.showinfo("Valid JSON", "The editor content is valid JSON.")
        except Exception as exc:
            messagebox.showerror("Invalid JSON", str(exc))

    def save_all(self) -> None:
        self.save_files(show_success=True)

    def save_files(self, show_success: bool = False) -> bool:
        phrase = self.passphrase.get()
        if not phrase:
            messagebox.showwarning("Missing passphrase", "Enter a passphrase to encrypt the private vault.")
            return False
        try:
            data = self.current_data()
            write_content_js(data)
            encrypt_vault(data, phrase)
            if show_success:
                messagebox.showinfo("Saved", "Updated content.js and encrypted private/lostfound-vault.enc.")
            return True
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return False

    def save_and_publish(self) -> None:
        proceed = messagebox.askyesno(
            "Publish to GitHub",
            "This will save content.js, commit the public content change, and push to GitHub. Continue?",
        )
        if not proceed:
            return
        if not self.save_files(show_success=False):
            return
        try:
            if not has_public_content_changes():
                messagebox.showinfo("No public changes", "content.js did not change, so there is nothing to publish.")
                return
            run_git(["add", "content.js"])
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            run_git(["commit", "-m", f"Update site content {stamp}"])
            run_git(["push"])
            messagebox.showinfo("Published", "Committed content.js and pushed to GitHub.")
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            messagebox.showerror("Publish failed", detail)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    WriterApp().run()
