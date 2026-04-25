#!/usr/bin/env python3
"""Apply reviewed coordinate data and rebuild graph/map outputs.

This is a convenience wrapper around:
  1. scripts/merge_place_coordinates.py
  2. scripts/build_graph.py
  3. scripts/validate_graph.py

Before running, place reviewed coordinate rows in:
  data/place_coordinates_custom.csv
or mark accepted Nominatim candidates in:
  data/place_coordinate_candidates.csv
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> None:
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / script)], cwd=str(ROOT))


def main() -> None:
    run("merge_place_coordinates.py")
    run("build_graph.py")
    run("validate_graph.py")
    print("Applied reviewed geocoding data and rebuilt graph/map outputs.")


if __name__ == "__main__":
    main()
