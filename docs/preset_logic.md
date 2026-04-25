# Lineage preset logic

Preset filters are intentionally heuristic. They help colleagues explore the network quickly but should not be treated as final taxonomic claims.

## Current presets

- `kagyu` – Kagyu family, Mahamudra, Naropa-related transmission, major Kagyu figures and places.
- `nyingma` – Nyingma, Dzogchen, Longchen Nyingthig, Heart-Essence materials.
- `drukpa` – Drukpa/Brugpa subset, including Bhutanese Drukpa material.

## How presets are assigned

The builder checks node labels, aliases, descriptions, source books, meeting outcomes, and related names against keyword lists in `scripts/build_graph.py`. Directly matched nodes are then expanded one hop along graph edges so that the preset keeps basic context.

## How to tune them

Edit `PRESET_DEFINITIONS` in `scripts/build_graph.py`, rebuild, and validate:

```bash
python scripts/build_graph.py
python scripts/validate_graph.py
```
