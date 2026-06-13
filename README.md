# Lost & Found

Static homepage template for a mysterious late-1990s Korean personal website.

Open `index.html` directly, or publish the folder through GitHub Pages or Cloudflare Pages.

The first screen intentionally shows only `crt-loading.gif`, `Lost & Found`, and the Today counter. Click the GIF to enter the old board-style homepage.

## Editing Content

Run `LostAndFoundWriter.command` on macOS to edit notice, diary, music, photo, and link data. The writer starts a local-only server and opens a browser editor at `http://127.0.0.1:5127/`.

Use `Save public` to update `content.js`. Use `Save & Publish` to save, commit `content.js`, and push the update to GitHub. Keep the Terminal window open while editing; closing it stops the local writer server.

The optional vault buttons store an encrypted editable copy at `private/lostfound-vault.enc`.

Music entries can use uploaded audio files or embeds. In the writer, upload mp3, m4a, wav, ogg, flac, or aac files from the music section to copy them into `assets/audio/`, or paste a SoundCloud/YouTube URL into `embedUrl`.

The `private/` folder is ignored by git. Keep the passphrase somewhere safe; it cannot be recovered from the site files.

## Publishing

The repository includes a GitHub Pages workflow at `.github/workflows/pages.yml`. After pushing to `main`, enable GitHub Pages with the source set to GitHub Actions in the repository settings if it is not already enabled.
