# Map enrichment workflow

The current map has **87 / 143** places geocoded. The remaining **56** are listed in:

`data/place_coordinate_backlog.csv`

The app now includes a **Coordinate backlog** tab, so a reviewer can work through the missing places inside the browser, export a reviewed coordinate CSV, and merge those coordinates back into the graph.

## Browser workflow

1. Open the app locally or on GitHub Pages.
2. Go to **Coordinate backlog**.
3. Open the suggested OpenStreetMap search link for a place.
4. Enter latitude and longitude.
5. Set status:
   - `manual_approved`
   - `ambiguous`
   - `not_found`
   - `needs_review`
6. Set coordinate confidence:
   - `exact_manual`
   - `approximate_manual`
   - `regional_anchor`
   - `uncertain_manual`
7. Add notes.
8. Click **Export custom coordinate CSV**.
9. Copy the exported file to:

`data/place_coordinates_custom.csv`

## Merge workflow

Run either the one-step wrapper:

```bash
python scripts/apply_geocoding_review.py
```

or run the steps manually:

```bash
python scripts/merge_place_coordinates.py
python scripts/build_graph.py
python scripts/validate_graph.py
```

Then commit the updated `data/` files.

## Optional Nominatim candidate workflow

For a reviewable candidate list, run:

```bash
python scripts/geocode_places.py
```

This creates:

`data/place_coordinate_candidates.csv`

Review the candidates manually. Set `Use=1` only for accepted rows, then run:

```bash
python scripts/apply_geocoding_review.py
```

## Coordinate status values

Suggested values:

- `seeded_approximate` – already available but approximate
- `custom_reviewed` – checked manually through the backlog workflow
- `nominatim_reviewed` – Nominatim candidate accepted by a human reviewer
- `not_found` – no confident result
- `ambiguous` – multiple possible places; needs a human decision

## Practical notes

The place list includes modern settlements, historical regions, passes, monasteries, caves, and broad cultural regions. These should not all be treated as equivalent point locations. For broad regions such as Tibet, Kham, Ladakh, Bengal, or Bhutan, use a representative map anchor and mark it as `regional_anchor`.
