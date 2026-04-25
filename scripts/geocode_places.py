#!/usr/bin/env python3
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / 'data' / 'place_coordinate_backlog.csv'
OUT = ROOT / 'data' / 'place_geocoding_review.csv'
USER_AGENT = 'LadakhBuddhismNetworkResearch/0.1 (contact: replace-with-project-email)'

def query_nominatim(q):
    params = urllib.parse.urlencode({'format': 'jsonv2', 'limit': 3, 'q': q})
    req = urllib.request.Request('https://nominatim.openstreetmap.org/search?' + params, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    with BACKLOG.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    output = []
    for idx, row in enumerate(rows, start=1):
        if row.get('Latitude') and row.get('Longitude'):
            output.append(row)
            continue
        q = row.get('SuggestedSearchQuery') or (row.get('CanonicalName', '') + ' Ladakh')
        print(f'[{idx}/{len(rows)}] {q}')
        try:
            results = query_nominatim(q)
        except Exception as exc:
            results = []
            row['CoordinateNotes'] = f'geocoding_error: {exc}'
        if results:
            best = results[0]
            row['Latitude'] = best.get('lat', '')
            row['Longitude'] = best.get('lon', '')
            row['CoordinateStatus'] = 'nominatim_candidate_needs_review'
            row['CoordinateNotes'] = f"display_name={best.get('display_name','')}; class={best.get('class','')}; type={best.get('type','')}"
            row['Status'] = 'candidate_needs_review'
        else:
            row['CoordinateStatus'] = 'not_found'
            row['Status'] = 'needs_manual_review'
        output.append(row)
        time.sleep(1.2)
    fieldnames = list(rows[0].keys()) if rows else []
    with OUT.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(output)
    print(f'Wrote {OUT}')

if __name__ == '__main__':
    main()
