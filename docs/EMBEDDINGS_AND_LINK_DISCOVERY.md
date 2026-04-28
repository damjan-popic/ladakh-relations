# Embeddings and link discovery

This repo supports three levels of link discovery.

## 1. Current default: alias matching + page co-occurrence

Implemented in `scripts/rebuild_all.py`. It finds master-schema entities in corpus pages and proposes links when entities repeatedly co-occur.

## 2. Lightweight lexical similarity

Run:

```bash
python scripts/build_similarity_links.py --method lexical
```

This is dependency-light and works from public metadata.

## 3. True embedding workflow

For actual sentence embeddings, install a local embedding model and extend `scripts/build_similarity_links.py` or add a new script. Recommended pattern:

1. chunk texts in `corpus/cleaned/`
2. embed chunks locally
3. aggregate chunk vectors around each entity mention
4. write reviewed candidates to `data/candidate_links.json` or a separate `data/embedding_links.json`

Keep embeddings local unless you are comfortable with data exposure through third-party APIs.
