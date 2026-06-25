# CiteMD PubMed Copilot Extension

This is an unpacked Chrome or Edge extension that injects a CiteMD panel into PubMed and Google Scholar pages.

## Start the local API

From the project root:

```bash
.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

The API runs at `http://localhost:8001`.

## Install in Chrome

1. Open `chrome://extensions`.
2. Turn on Developer mode.
3. Click Load unpacked.
4. Select this `extension` directory.
5. Open `https://pubmed.ncbi.nlm.nih.gov` or `https://scholar.google.com`.
6. Click the CiteMD button in the lower-right corner.

## Install in Edge

1. Open `edge://extensions`.
2. Turn on Developer mode.
3. Click Load unpacked.
4. Select this `extension` directory.
5. Open PubMed and click CiteMD.

## Notes

The extension is local-first. It sends questions to your local CiteMD API, which then searches PubMed, ranks papers, and calls OpenAI if `OPENAI_API_KEY` is set. On Google Scholar pages, it also sends the visible result titles, snippets, metadata, and links as page context; it does not scrape Google Scholar from the backend.
