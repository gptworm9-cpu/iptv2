# IPTV Flask app — Vercel-ready

This is a minimal Flask scaffold designed to deploy on Vercel as a Python Serverless Function. It provides a human-focused, non-AI-looking IPTV channel list UI you can customize.

Quick start (local):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cd api
python index.py
```

Deploy to Vercel:

1. Install and login with the Vercel CLI: `npm i -g vercel` then `vercel login`.
2. From the project root (where `vercel.json` is), run:

```powershell
vercel --prod
```

Notes:
- Replace the example stream URLs in `api/index.py` with your real IPTV HLS links.
- For an in-page player, integrate `hls.js` in the template and replace the `Open Stream` link.
