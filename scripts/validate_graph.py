#!/usr/bin/env python3
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
graph = json.loads((ROOT / 'data' / 'ladakh_graph.json').read_text(encoding='utf-8'))
node_ids = {n['id'] for n in graph['nodes']}
bad = [e for e in graph['edges'] if e['source'] not in node_ids or e['target'] not in node_ids]
print(json.dumps({
  'nodes': len(graph['nodes']),
  'edges': len(graph['edges']),
  'bad_edges': len(bad),
  'summary': graph['summary']
}, indent=2, ensure_ascii=False))
if bad:
    raise SystemExit('Graph contains edges with missing endpoints')
