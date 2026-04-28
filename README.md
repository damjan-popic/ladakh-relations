# Ladakh Relations Research Repository

This is the definitive static-site + local-pipeline repository for the Ladakh Buddhism master graph.

It supports:

- an interactive graph of people, places, underpinnings, explorers, assets, meetings, and candidate relations;
- a stable map view with geocoded places and coordinate-review tooling;
- a corpus index for normalized transcriptions;
- local cleaning and annotation workflows;
- candidate link discovery from entity mentions and page-level co-occurrence;
- optional future embeddings / semantic-link discovery;
- GitHub Pages deployment without a backend.

## Current generated snapshot

- Graph nodes: 447
- Graph edges: 1710
- Corpus documents indexed: 17
- Corpus pages indexed: 4309
- Similarity links generated: 200
- Candidate links generated: 350
- Entity mention rows: 1106

## Start locally

```bash
python scripts/serve_local.py
```

Open <http://localhost:8000>.

## Deploy to GitHub Pages

Upload the repository contents to your GitHub repo root. Keep `index.html`, `app.js`, `style.css`, `.nojekyll`, and `data/` at the top level.

Then either:

- use **Settings → Pages → Deploy from branch → main → root**, or
- switch Pages to **GitHub Actions** and use `.github/workflows/pages.yml`.

## Feeding new texts into the repo

1. Put transcribed/OCR text files in `corpus/raw/`.
2. Normalize them:

```bash
python scripts/normalize_texts.py corpus/raw corpus/normalized
```

3. Rebuild derived public data:

```bash
python scripts/rebuild_all.py
```

4. Serve or commit the updated `data/` files.

## Important public/private note

The public GitHub Pages site should normally contain only derived metadata. Full transcriptions may be copyrighted or otherwise sensitive. This repo therefore ignores full text files under `corpus/` by default. Use the separate private corpus import pack locally.

## Key docs

- `docs/ARCHITECTURE.md`
- `docs/CORPUS_AND_ANNOTATION_WORKFLOW.md`
- `docs/EMBEDDINGS_AND_LINK_DISCOVERY.md`
- `docs/GITHUB_PAGES_DEPLOYMENT.md`
- `docs/map_enrichment_workflow.md`
