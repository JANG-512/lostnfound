# Lost & Found

Static homepage template for a mysterious late-1990s Korean personal website.

Open `index.html` directly, or publish the folder through GitHub Pages or Cloudflare Pages.

The first screen intentionally shows only `crt-loading.gif`, `Lost & Found`, and the Today counter. Click the GIF to enter the old board-style homepage.

## Editing Content

Run `LostAndFoundWriter.command` on macOS to edit notice, diary, music, photo, and link data. The writer exports public data to `content.js` and stores the editable source vault at `private/lostfound-vault.enc`.

Use `Save encrypted vault + public content.js` to save locally. Use `Save & Publish to GitHub` to save, commit `content.js`, and push the update to GitHub.

The `private/` folder is ignored by git. Keep the passphrase somewhere safe; it cannot be recovered from the site files.

## Publishing

The repository includes a GitHub Pages workflow at `.github/workflows/pages.yml`. After pushing to `main`, enable GitHub Pages with the source set to GitHub Actions in the repository settings if it is not already enabled.
