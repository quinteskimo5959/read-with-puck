# Read with Puck

A phonics reading app. It runs from GitHub Pages and installs on an iPhone or iPad as an app icon.

## First-time setup
1. Upload everything in this folder to a GitHub repo (keep the `stories` folder).
2. Settings → Pages → Source: "Deploy from a branch", branch `main`, folder `/ (root)`. Save.
3. Wait a minute or two, then open the Pages link in **Safari** on the iPad or iPhone.
4. Tap Share → **Add to Home Screen**. The duck icon is the app.

## Updating the app
Replace `index.html` in the repo with the new one. Next time she opens the app with internet, it loads the new version (GitHub can take up to about 10 minutes to serve it). The version number is at the bottom of Settings.

## Adding a shared story
Upload a plain text file to the `stories` folder (Add file → Upload files, or Add file → Create new file and name it something like `puck-at-the-zoo.txt`).

Format:

    Title on the first line

    First page.

    Second page.

    Third page.

- A blank line starts a new page.
- Long text (a chapter) is split into pages automatically.
- It shows up in Library → Shared stories next time the app opens. If the story is at or below her level, it also shows on the home screen under "New stories she can read".
- Tap 📊 next to any story to see the level it needs and the sounds to practice first.

The repo is public, so anyone with the link can read the stories. Only upload stories you wrote or ones Claude wrote for you. Don't upload copyrighted books (paste those into Library → Add a book on her device instead; they stay on that device).

`stories/index.json` is only a backup list used if GitHub's file listing is unavailable. You don't need to keep it up to date.
