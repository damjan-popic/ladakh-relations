# Deployment checklist for `damjan-popic.github.io/ladakh-relations`

The live page will only work if these files and folders sit in the **repository root** of `ladakh-relations`:

```text
index.html
app.js
style.css
.nojekyll
data/
docs/
scripts/
```

Do **not** upload only `index.html`. Also do **not** leave everything inside a nested folder such as `ladakh_network_visualization_repo_v2/`, unless GitHub Pages is explicitly configured to serve from that folder.

## Quick fix

1. Download and unzip the fixed bundle.
2. Open the unzipped folder.
3. Select the contents of the folder, not the folder itself.
4. Drag the files and folders into the GitHub repo root.
5. Commit the upload.
6. Visit:

```text
https://damjan-popic.github.io/ladakh-relations/site-health.html
```

Every required row should show `OK`.

## Required runtime files

The app fetches the following at runtime:

```text
data/ladakh_graph.json
data/meetings_timeline.json
data/places.geojson
data/place_links.geojson
data/place_coordinate_backlog.csv
docs/map_enrichment_workflow.md
```

If any of those files return 404, the network, timeline, or map enrichment panels will stay empty or show an error.
