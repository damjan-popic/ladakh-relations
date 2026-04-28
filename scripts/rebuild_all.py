#!/usr/bin/env python3
"""Rebuild derived public data from the master graph and local corpus.

This script refreshes:
- data/corpus_index.json
- data/entity_mentions.json
- data/candidate_links.json
- data/annotation_queue.json
- data/site_health.json

Full text stays in corpus/* and is not copied to data/ unless --include-context is used.
"""
from __future__ import annotations
import argparse, itertools, json, math, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
CORPUS = ROOT / 'corpus'

def ascii_fold(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(ch for ch in s if not unicodedata.combining(ch)).replace('’', "'").replace('‘', "'")

def parse_pages(text: str):
    pat = re.compile(r'^===\s*(?:PDF\s+)?Page\s+(\d+)\s*===\s*$|^===\s*PAGE\s+(\d+)\s*===\s*$', re.M | re.I)
    matches = list(pat.finditer(text))
    if not matches:
        return [{'page': None, 'text': text}]
    pages = []
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        pages.append({'page': int(m.group(1) or m.group(2)), 'text': text[m.end():end].strip()})
    return pages

def read_corpus_files():
    docs = []
    for folder in [CORPUS/'cleaned', CORPUS/'normalized']:
        for path in sorted(folder.glob('*.txt')):
            if path.name.startswith('.'):
                continue
            text = path.read_text(encoding='utf-8', errors='ignore').replace('\x00','')
            title = path.stem
            m = re.search(r'^TITLE:\s*(.+)$', text, re.M)
            if m: title = m.group(1).strip()
            source = ''
            m = re.search(r'^SOURCE FILE:\s*(.+)$', text, re.M)
            if m: source = m.group(1).strip()
            bundle = ''
            m = re.search(r'^BUNDLE:\s*(.+)$', text, re.M)
            if m: bundle = m.group(1).strip()
            docs.append({'path': str(path.relative_to(ROOT)), 'title': title, 'sourceFile': source, 'bundle': bundle, 'pages': parse_pages(text), 'rawText': text})
    return docs

def build_aliases(nodes):
    stop = {'the','and','bon','da','gya','sani','india','tibet','nepal','kham','leh','lama','guru','buddha','dharma','sangha','refuge','mind','ethics','wisdom','compassion'}
    aliases = []
    for n in nodes:
        vals = {n.get('label',''), *[a for a in (n.get('aliases') or []) if a]}
        expanded = set()
        for v in vals:
            expanded.add(v); expanded.add(ascii_fold(v))
        usable = []
        for a in sorted(expanded, key=lambda x:(-len(x), x.lower())):
            norm = ascii_fold(a).lower().strip()
            if len(norm) < 4 or norm in stop: continue
            pat = re.escape(norm).replace('\\ ', r'\s+')
            try: rx = re.compile(r'(?<![a-z0-9])' + pat + r'(?![a-z0-9])', re.I)
            except re.error: continue
            usable.append((a, norm, rx))
        if usable:
            aliases.append({'node': n, 'aliases': usable[:8]})
    return aliases

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--include-context', action='store_true', help='Include short snippets in annotation queue. Avoid for public copyrighted data.')
    args = ap.parse_args()
    graph = json.loads((DATA/'ladakh_graph.json').read_text(encoding='utf-8'))
    nodes, edges = graph['nodes'], graph['edges']
    node_by_id = {n['id']: n for n in nodes}
    alias_rows = build_aliases(nodes)
    docs = read_corpus_files()
    mention_by_doc_entity = defaultdict(lambda: {'count': 0, 'pages': Counter(), 'aliases': Counter()})
    pair_counter, pair_docs, pair_evidence = Counter(), defaultdict(Counter), defaultdict(list)
    doc_summaries, annotations = [], []
    for i, d in enumerate(docs, 1):
        doc_id = f'DOC_{i:03d}'
        counts = Counter(); pages_with_mentions = 0
        for page in d['pages']:
            txt = page['text'] or ''
            norm_text = ascii_fold(txt).lower()
            page_entities = {}
            for row in alias_rows:
                ent = row['node']
                for alias, alias_norm, rx in row['aliases']:
                    if alias_norm not in norm_text:
                        continue
                    c = 0
                    first = None
                    for m in rx.finditer(norm_text):
                        if first is None: first = m
                        c += 1
                        if c >= 5: break
                    if not c: continue
                    eid = ent['id']
                    page_entities[eid] = page_entities.get(eid, 0) + c
                    key = (doc_id, eid)
                    mention_by_doc_entity[key]['count'] += c
                    mention_by_doc_entity[key]['pages'][page['page']] += c
                    mention_by_doc_entity[key]['aliases'][alias] += c
                    counts[eid] += c
                    if len(annotations) < 500:
                        ann = {'id': f'ANN_{len(annotations)+1:04d}', 'kind': 'entity_mention', 'docId': doc_id, 'documentTitle': d['title'], 'page': page['page'], 'entityId': eid, 'entityLabel': ent.get('label', eid), 'matchedAlias': alias, 'reviewStatus': 'unreviewed', 'notes': ''}
                        if args.include_context and first:
                            start = max(first.start()-140, 0); end = min(first.end()+140, len(txt))
                            ann['context'] = txt[start:end].replace('\n',' ')
                        annotations.append(ann)
                    break
            if page_entities: pages_with_mentions += 1
            ids = sorted(page_entities)
            if 2 <= len(ids) <= 35:
                for a, b in itertools.combinations(ids, 2):
                    pair = tuple(sorted((a,b)))
                    pair_counter[pair] += 1; pair_docs[pair][doc_id] += 1
                    if len(pair_evidence[pair]) < 8:
                        pair_evidence[pair].append({'docId': doc_id, 'documentTitle': d['title'], 'page': page['page']})
        top = [{'entityId': eid, 'label': node_by_id.get(eid,{}).get('label', eid), 'category': node_by_id.get(eid,{}).get('category',''), 'count': c} for eid, c in counts.most_common(15)]
        doc_summaries.append({'docId': doc_id, 'title': d['title'], 'sourceFile': d['sourceFile'], 'bundle': d['bundle'], 'corpusPath': d['path'], 'pageCount': len(d['pages']), 'characterCount': sum(len(p['text']) for p in d['pages']), 'wordEstimate': sum(len(re.findall(r'\w+', p['text'])) for p in d['pages']), 'pagesWithEntityMentions': pages_with_mentions, 'topEntities': top})
    (DATA/'corpus_index.json').write_text(json.dumps({'summary': {'documentCount': len(doc_summaries), 'pageCount': sum(x['pageCount'] for x in doc_summaries), 'wordEstimate': sum(x['wordEstimate'] for x in doc_summaries), 'publicDataPolicy': 'Derived metadata only; full texts remain in corpus/.'}, 'documents': doc_summaries}, ensure_ascii=False, indent=2), encoding='utf-8')
    mention_items = []
    for (doc_id, eid), val in mention_by_doc_entity.items():
        doc = doc_summaries[int(doc_id.split('_')[1])-1]
        n = node_by_id.get(eid, {})
        mention_items.append({'docId': doc_id, 'documentTitle': doc['title'], 'entityId': eid, 'entityLabel': n.get('label', eid), 'entityCategory': n.get('category',''), 'count': val['count'], 'pages': [p for p,c in val['pages'].most_common(50)], 'topAliases': [{'alias': a, 'count': c} for a,c in val['aliases'].most_common(5)], 'presetTags': n.get('presetTags',[])})
    mention_items.sort(key=lambda x:(-x['count'], x['documentTitle']))
    (DATA/'entity_mentions.json').write_text(json.dumps({'summary': {'mentionRows': len(mention_items), 'entityCount': len(set(x['entityId'] for x in mention_items))}, 'items': mention_items[:5000]}, ensure_ascii=False, indent=2), encoding='utf-8')
    existing = {tuple(sorted((e['source'], e['target']))) for e in edges if e.get('source') and e.get('target')}
    def relation(a,b, ex):
        if ex: return 'already_in_master_graph'
        cats = {a,b}
        if cats == {'Person'}: return 'possible_teacher_disciple_or_textual_association'
        if cats == {'Person','Place'}: return 'possible_visit_location_or_site_association'
        if cats == {'Person','Underpinning'}: return 'possible_doctrine_practice_association'
        if cats == {'Place','Underpinning'}: return 'possible_place_lineage_or_practice_association'
        return 'possible_textual_association'
    candidates = []
    for (a,b), cnt in pair_counter.most_common(500):
        if cnt < 2: break
        na, nb = node_by_id.get(a), node_by_id.get(b)
        if not na or not nb: continue
        ex = tuple(sorted((a,b))) in existing
        candidates.append({'id': f'CL_{len(candidates)+1:04d}', 'source': a, 'target': b, 'sourceLabel': na.get('label',a), 'targetLabel': nb.get('label',b), 'sourceCategory': na.get('category',''), 'targetCategory': nb.get('category',''), 'method': 'page_cooccurrence_alias_match', 'score': round(min(1.0, math.log1p(cnt)/math.log(60)),4), 'evidenceCount': cnt, 'documents': [{'docId': did, 'documentTitle': doc_summaries[int(did.split("_")[1])-1]['title'], 'pageCooccurrences': c} for did,c in pair_docs[(a,b)].most_common(8)], 'evidencePages': pair_evidence[(a,b)], 'alreadyInGraph': ex, 'suggestedRelationType': relation(na.get('category',''), nb.get('category',''), ex), 'reviewStatus': 'already_represented' if ex else 'unreviewed', 'presetTags': sorted(set(na.get('presetTags',[]) + nb.get('presetTags',[])))})
    (DATA/'candidate_links.json').write_text(json.dumps({'summary': {'candidateCount': len(candidates), 'method': 'alias matching + page-level co-occurrence'}, 'items': candidates}, ensure_ascii=False, indent=2), encoding='utf-8')
    aq = {'summary': {'itemCount': min(200, len(candidates)+len(annotations)), 'includeContext': args.include_context}, 'items': []}
    aq['items'].extend([{'id':'AQ_'+c['id'], 'kind':'candidate_relation', **{k:c[k] for k in ['source','target','sourceLabel','targetLabel','suggestedRelationType','evidenceCount','evidencePages','reviewStatus']}, 'notes':''} for c in candidates[:120]])
    aq['items'].extend(annotations[:80])
    (DATA/'annotation_queue.json').write_text(json.dumps(aq, ensure_ascii=False, indent=2), encoding='utf-8')
    health = {'documents': len(doc_summaries), 'mentions': len(mention_items), 'candidateLinks': len(candidates), 'graphNodes': len(nodes), 'graphEdges': len(edges)}
    (DATA/'site_health.json').write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(health, indent=2))
if __name__ == '__main__': main()
