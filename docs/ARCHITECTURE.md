# Architecture

The repository is split into two layers:

1. **Static public site**: `index.html`, `app.js`, `style.css`, and generated `data/*.json` files. This layer runs on GitHub Pages with no backend.
2. **Local research pipeline**: `corpus/`, `scripts/`, `schema/`, and `source/`. This layer lets you ingest transcriptions, clean them, annotate them, and regenerate data for the site.

The core principle is that the web app never writes to the server. Reviews are saved in the browser and exported as CSV/JSON. Once a review is accepted, copy it into `corpus/annotated/` and rerun the pipeline.

## Data flow

```text
source workbook + graph data
        │
        ▼
data/ladakh_graph.json ──────┐
                              ├── static site
corpus/normalized/*.txt ──────┤
        │                     │
        ▼                     │
scripts/rebuild_all.py ───────┘
        │
        ├── data/corpus_index.json
        ├── data/entity_mentions.json
        ├── data/candidate_links.json
        ├── data/annotation_queue.json
        └── data/site_health.json
```

## Why derived public data?

The normalized transcriptions are research material and may include copyrighted text. The public site therefore uses metadata, entity counts, page references, and candidate links. Keep full texts in a private repo, local folder, or private corpus import pack unless redistribution rights are clear.
