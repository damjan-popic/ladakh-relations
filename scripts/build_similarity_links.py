#!/usr/bin/env python3
"""Optional semantic-link builder.

Default mode uses lightweight lexical vectors with no external dependencies.
If sentence-transformers is installed and a local model is available, extend this script with a private model path.
"""
from __future__ import annotations
import argparse, json, math, re
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def tokenize(s): return [w.lower() for w in re.findall(r'[A-Za-z][A-Za-z\-]{2,}', s)]
def cosine(a,b):
    dot = sum(a.get(k,0)*b.get(k,0) for k in a.keys() & b.keys())
    na = math.sqrt(sum(v*v for v in a.values())); nb = math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--method', choices=['lexical','sentence-transformers'], default='lexical')
    ap.add_argument('--top', type=int, default=200)
    args = ap.parse_args()
    corpus = json.loads((ROOT/'data/corpus_index.json').read_text(encoding='utf-8'))
    mentions = json.loads((ROOT/'data/entity_mentions.json').read_text(encoding='utf-8'))['items']
    vecs = defaultdict(Counter)
    for m in mentions:
        for w in tokenize(m['documentTitle']):
            vecs[m['entityId']][w] += m['count']
    ids = sorted(vecs)
    items = []
    for i, a in enumerate(ids):
        for b in ids[i+1:]:
            s = cosine(vecs[a], vecs[b])
            if s > 0:
                items.append({'source': a, 'target': b, 'method': 'public_metadata_lexical_similarity', 'score': round(s,4)})
    items.sort(key=lambda x: -x['score'])
    (ROOT/'data/similarity_links.json').write_text(json.dumps({'summary': {'method': args.method, 'count': min(args.top, len(items))}, 'items': items[:args.top]}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'wrote data/similarity_links.json with {min(args.top, len(items))} links')
if __name__ == '__main__': main()
