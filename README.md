# B2 Mündlich – Trainer

German B2 oral exam practice: 6 topics in a 10-point structure. You can click any word to see its English meaning. A video-lesson mode reads each sentence aloud and highlights the words as they are spoken.

## How the natural voice works

`.github/workflows/record-audio.yml` runs `tools/make_audio.py` on GitHub. The script records every sentence with the Microsoft neural voices Katja and Conrad (via `edge-tts`) into `audio/`. It also writes `audio/timings.js`, which holds the word timings used for highlighting. If a recording is missing, the page falls back to the browser's own voice.

To change or add text, edit the JSON block at the top of the script section in `index.html` and push. Only changed sentences are recorded again.

## Publishing

Settings → Pages → Source: **Deploy from a branch** → Branch: `main`, folder `/ (root)`.
