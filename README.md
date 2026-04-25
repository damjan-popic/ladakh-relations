# Ladakh Buddhism Network Explorer

Interactive static website and data exports for exploring the Ladakh Buddhism master schema.

This version adds three research-facing upgrades:

1. **Lineage preset filters** for Kagyu, Nyingma/Dzogchen, and Drukpa/Brugpa.
2. **Timeline view** for entity meetings, visits, and transmission moments.
3. **Map enrichment workflow** for gradually validating and adding coordinates, including a browser-based Coordinate backlog tab.

The app is static and can be deployed directly to GitHub Pages. No backend and no build system are required.

## Quick start locally

```bash
cd ladakh_network_visualization_repo_v2
python -m http.server 8000
```

Open `http://localhost:8000`.

## Deploy to GitHub Pages

1. Create a GitHub repository.
2. Upload the contents of this folder to the repository root.
3. Go to **Settings → Pages**.
4. Choose **Deploy from branch**.
5. Select `main` and `/ (root)`.
6. Save.

## Dataset snapshot

Generated from `ladakh_master_final_updated_v4.xlsx`.

- Nodes: 447
- Edges: 1710
- Persons: 122
- Places: 143
- Assets: 3
- Underpinnings: 98
- Explorers: 81
- Meetings / visits: 53
- Geocoded places: 87 / 143
- Coordinate backlog: 56

## Main files

- `index.html` – app shell
- `app.js` – interactive network, map, timeline, filters, coordinate backlog editor
- `style.css` – interface styling
- `data/ladakh_graph.json` – full graph data
- `data/meetings_timeline.json` – parsed meeting/visit records
- `data/places.geojson` – geocoded place markers
- `data/place_links.geojson` – geocoded place-to-place links where available
- `data/place_coordinate_backlog.csv` – ungeocoded places needing review
- `data/place_coordinates_custom.csv` – reviewer-entered coordinate updates, used by the merge script
- `data/place_coordinates_seed.csv` – current seed coordinate table
- `data/ladakh_network.graphml` – importable into Gephi / Cytoscape

## Rebuild after workbook updates

Replace the workbook in `source/`, then run:

```bash
python scripts/build_graph.py
python scripts/validate_graph.py
```

Commit the changed `data/` files and push.

## Preset filters

The preset logic is heuristic and lives in `scripts/build_graph.py` under `PRESET_DEFINITIONS`.
Adjust the keyword lists as the master schema gets richer.

## Map enrichment

Use the **Coordinate backlog** tab in the app, then see `docs/map_enrichment_workflow.md` for the merge steps. The short version is:

```bash
python scripts/apply_geocoding_review.py
```
