import csv
import json
import math
import os
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

WORKBOOK = Path(__file__).resolve().parents[1] / 'source' / 'ladakh_master_final_updated_v4.xlsx'
OUTDIR = Path(__file__).resolve().parents[1]
DATADIR = OUTDIR / 'data'
SCRIPTDIR = OUTDIR / 'scripts'
DOCDIR = OUTDIR / 'docs'
SOURCEDIR = OUTDIR / 'source'

for d in [OUTDIR, DATADIR, SCRIPTDIR, DOCDIR, SOURCEDIR]:
    d.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Minimal XLSX reader (stdlib only)
# -----------------------------
NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'officeRel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}

def col_to_index(cell_ref):
    letters = ''.join(ch for ch in cell_ref if ch.isalpha())
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - 64)
    return idx - 1

def text_from_si(si):
    pieces = []
    for t in si.iterfind('.//main:t', NS):
        pieces.append(t.text or '')
    return ''.join(pieces)

def load_xlsx(path):
    with zipfile.ZipFile(path) as zf:
        shared = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            shared = [text_from_si(si) for si in root.findall('main:si', NS)]

        wb_root = ET.fromstring(zf.read('xl/workbook.xml'))
        rel_root = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
        rels = {}
        for rel in rel_root.findall('rel:Relationship', NS):
            rels[rel.attrib['Id']] = rel.attrib['Target']

        sheets = {}
        for sheet in wb_root.findall('.//main:sheet', NS):
            name = sheet.attrib['name']
            rid = sheet.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target = rels[rid]
            if target.startswith('/'):
                sheet_path = target.lstrip('/')
            else:
                sheet_path = 'xl/' + target
            sheet_path = str(Path(sheet_path).as_posix())
            root = ET.fromstring(zf.read(sheet_path))
            rows = []
            for row in root.findall('.//main:sheetData/main:row', NS):
                values = []
                for cell in row.findall('main:c', NS):
                    ref = cell.attrib.get('r', '')
                    cidx = col_to_index(ref)
                    while len(values) <= cidx:
                        values.append('')
                    ctype = cell.attrib.get('t')
                    value = ''
                    if ctype == 'inlineStr':
                        is_el = cell.find('main:is', NS)
                        value = text_from_si(is_el) if is_el is not None else ''
                    else:
                        v = cell.find('main:v', NS)
                        if v is not None and v.text is not None:
                            raw = v.text
                            if ctype == 's':
                                try:
                                    value = shared[int(raw)]
                                except Exception:
                                    value = raw
                            elif ctype == 'b':
                                value = 'TRUE' if raw == '1' else 'FALSE'
                            else:
                                value = raw
                    values[cidx] = value
                rows.append(values)
            sheets[name] = rows
        return sheets

def rowdicts(rows):
    if not rows:
        return []
    headers = [str(h).strip() for h in rows[0]]
    data = []
    for row in rows[1:]:
        if not any(str(x).strip() for x in row):
            continue
        d = {}
        for i, h in enumerate(headers):
            if h:
                d[h] = row[i] if i < len(row) else ''
        data.append(d)
    return data

sheets = load_xlsx(WORKBOOK)
entities = rowdicts(sheets['Entities'])
underpinnings = rowdicts(sheets['Underpinnings'])
explorers = rowdicts(sheets['Explorers'])
references = rowdicts(sheets['References_Used'])

# -----------------------------
# Helpers
# -----------------------------
def clean_str(x):
    if x is None:
        return ''
    s = str(x).strip()
    if s.lower() == 'nan':
        return ''
    return s

def split_multi(x):
    s = clean_str(x)
    if not s:
        return []
    return [p.strip() for p in re.split(r'\s*;\s*', s) if p.strip()]

def split_dates(x):
    return split_multi(x)

def split_outcomes(x):
    return split_multi(x)

def norm_name(s):
    s = clean_str(s).lower()
    s = re.sub(r'\s*\(.*?\)', '', s)
    s = s.replace('ā', 'a').replace('ś', 's').replace('ṣ', 's').replace('ṅ', 'n').replace('ñ', 'n').replace('ö','o').replace('ü','u').replace('é','e')
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def html_title(lines):
    return '<br>'.join(escape(x) for x in lines if x)

COLOR_MAP = {
    'Person': '#d95f02',
    'Place': '#1b9e77',
    'Asset': '#e6ab02',
    'Explorer': '#1f3b73',
    'Underpinning': '#6a3d9a',
}

PRESET_DEFINITIONS = {
    'kagyu': {
        'label': 'Kagyu family',
        'description': 'Kagyu lineages, Mahamudra, Naropa-related transmission, and major Kagyu figures.',
        'keywords': [
            'kagyu','kagyü','bka brgyud','mahamudra','mahāmudrā','six yogas','six yogas of naropa',
            'naropa','nāropa','tilopa','marpa','milarepa','gampopa','vajradhara','maitripa','rechungpa',
            'phagmodrupa','phagdru','jigten','drikung','drukpa','shangpa','gotsangpa','tummo',
            'fivefold path of mahamudra','dagpo','dakpo','phullahari','nalanda'
        ]
    },
    'nyingma': {
        'label': 'Nyingma / Dzogchen',
        'description': 'Nyingma, Dzogchen, Longchen Nyingthig, and Heart-Essence networks.',
        'keywords': [
            'nyingma','rnying','dzogchen','dzogchen','dzogs chen','atiyoga','longchen','longchenpa',
            'jigme lingpa','jigme gyalwai nyugu','patrul','padmasambhava','guru rinpoche','yeshe tsogyal',
            'vimalamitra','samantabhadra','heart essence','heart-essence','nyingthig','nature of mind',
            'dharmadhatu','samye','bumthang','kumaradza'
        ]
    },
    'drukpa': {
        'label': 'Drukpa / Brugpa',
        'description': 'Drukpa Kagyü, Bhutanese Drukpa, and related Bhutan/Ladakh branch material.',
        'keywords': [
            'drukpa','drukpa kagyu','drukpa kagyü','brug pa','brugpa','lho brug','drukpa kunle','drukpa künlé',
            'zhabdrung','ngawang namgyel','phajo','phajo drukgom','pema karpo','tsangpa gyare',
            'bhutanese drukpa','bhutan','six cycles of equal taste','equal taste','merging and transference'
        ]
    }
}

# Coordinate seed. Approximate points; scholarly validation can happen in backlog workflow.
DEFAULT_PLACE_COORDS = {
    'Ladakh': (34.15, 77.58), 'Leh': (34.1642, 77.5848), 'Tibet': (31.6846, 88.1428), 'India': (22.9734, 78.6569),
    'Zangskar': (33.46, 76.99), 'Zojila Pass': (34.285, 75.55), 'Hemis': (33.8954, 77.7904), 'Dras': (34.43, 75.76),
    'Lamayuru': (34.2828, 76.7734), 'Karakoram': (35.31, 76.73), 'Nubra Valley': (34.65, 77.70), 'Dharamsala': (32.2190, 76.3234),
    'Bhutan': (27.5142, 90.4336), 'Lhasa': (29.6520, 91.1721), 'Spituk': (34.1360, 77.4825), 'Kargil': (34.5564, 76.1262),
    'Karakoram Pass': (35.51, 78.56), 'Dzongkul': (33.381, 76.84), 'Nalanda': (25.1367, 85.4439), 'Nepal': (28.3949, 84.1240),
    'Saspola': (34.25, 76.88), 'Samye': (29.331, 91.498), 'Kashmir': (33.95, 76.80), 'Manali': (32.2432, 77.1892),
    'Padum': (33.4667, 76.8833), 'Kham': (31.5, 97.0), 'Guge': (31.48, 79.64), 'Lahoul': (32.5717, 77.0425),
    'Gotsang Gompa': (34.14, 77.56), 'Khalatse': (34.340, 76.883), 'Changchenmo Valley': (34.43, 78.44), 'Sani': (33.46, 76.93),
    'Rupshu': (33.22, 78.04), 'Phyang': (34.1556, 77.4352), 'Stagna Gompa': (34.066, 77.653), 'Oddiyana / Uddiyana': (34.77, 72.36),
    'Basgo': (34.279, 76.837), 'Bengal': (23.6850, 90.3563), 'Bodhgaya / Bodh Gaya': (24.695, 84.991), 'Karsha': (33.485, 76.998),
    'Tsari': (28.79, 93.47), 'Tanktse': (34.02, 78.25), 'Sasser-la': (35.50, 77.77), 'Hanu': (34.62, 76.86),
    'Lhotrak': (27.6, 91.2), 'Ating': (33.56, 76.92), 'Changthang': (33.9, 79.0), 'Bardan': (33.533, 76.978),
    'Stongde': (33.53, 76.99), 'Sakti': (34.04, 77.76), 'Dingri': (28.633, 86.433), 'Drepung Monastery': (29.6807, 91.0630),
    'Bumthang': (27.5497, 90.7525), 'Sangphu Neutog': (29.73, 91.34), 'Yartö Khyam': (31.20, 90.80), 'Tashi Gang': (27.3333, 91.55),
    'Chemre': (33.997, 77.89), 'Choglamsar': (34.0987, 77.6044), 'Chusul': (33.546, 78.689), 'Darcha': (32.75, 77.20),
    'Gandhara': (34.0, 72.0), 'Gartok': (31.48, 80.07), 'Gya': (33.95, 77.77), 'Hanle': (32.78, 79.05),
    'Korzok': (33.27, 78.27), 'Khardong Gompa': (34.32, 77.60), 'Mulbekh': (34.28, 76.35), 'Indus': (33.97, 77.00),
    'Shila': (33.43, 76.94), 'Phamthing / Parpheng': (27.45, 90.85), 'Tragthog Gompa': (33.59, 78.13), 'Namikala': (34.31, 76.52),
    'Fotu-la': (34.26, 76.67), 'Da': (34.67, 76.85), 'Dha': (34.66, 76.82), 'Baralacha Pass': (32.759, 77.398),
    'Bod Karbu': (34.41, 76.06), 'Farkithang': (34.17, 76.87), 'Phullahari': (25.10, 85.45),
    'Chamba / Triloknath region': (32.55, 76.02), 'Pangong Lake': (33.75, 78.80), 'Tso Moriri': (32.90, 78.31),
    'Shey': (34.07, 77.63), 'Thiksey': (34.056, 77.667), 'Alchi': (34.223, 77.176), 'Rizong': (34.271, 77.007),
    'Wanla': (34.252, 76.817), 'Takthok': (34.000, 77.775), 'Likir': (34.306, 77.011), 'Matho': (34.028, 77.643),
    'Stakna': (34.002, 77.687), 'Saspol': (34.250, 76.883), 'Kargil district': (34.56, 76.13), 'Zangla': (33.61, 76.96),
    'Stagrimo': (33.53, 76.95), 'Shingo La': (33.08, 77.38), 'Baralacha La': (32.759, 77.398), 'Rangdum': (33.99, 76.34),
}



def load_place_coordinates():
    seed_path = DATADIR / 'place_coordinates_seed.csv'
    coords = {name: {'lat': lat, 'lon': lon, 'status': 'seeded_approximate', 'notes': 'Approximate seed coordinate; review before spatial analysis.'} for name, (lat, lon) in DEFAULT_PLACE_COORDS.items()}
    if seed_path.exists():
        with seed_path.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                name = clean_str(row.get('CanonicalName'))
                lat = clean_str(row.get('Latitude'))
                lon = clean_str(row.get('Longitude'))
                if not name or not lat or not lon:
                    continue
                try:
                    coords[name] = {
                        'lat': float(lat), 'lon': float(lon),
                        'status': clean_str(row.get('CoordinateStatus')) or 'manual_approved',
                        'notes': clean_str(row.get('CoordinateNotes'))
                    }
                except ValueError:
                    continue
    return coords

PLACE_COORDS = load_place_coordinates()

# -----------------------------
# Register nodes
# -----------------------------
name_to_id = {}
id_to_label = {}
id_to_category = {}
node_records = {}

def register_name(name, node_id):
    n = norm_name(name)
    if n:
        name_to_id.setdefault(n, node_id)

def gather_text(*parts):
    vals = []
    for p in parts:
        if isinstance(p, list):
            vals.extend(p)
        else:
            vals.append(clean_str(p))
    return ' '.join(v for v in vals if v).lower()

def detect_direct_presets(text):
    text = text.lower()
    tags = []
    for key, definition in PRESET_DEFINITIONS.items():
        if any(kw.lower() in text for kw in definition['keywords']):
            tags.append(key)
    return sorted(set(tags))

for r in entities:
    node_id = clean_str(r.get('EntityID'))
    if not node_id:
        continue
    category = clean_str(r.get('EntityCategory')) or 'Entity'
    label = clean_str(r.get('CanonicalName')) or node_id
    aliases = split_multi(r.get('Aliases'))
    text = gather_text(label, aliases, r.get('ShortDescription'), r.get('UnderpinningNames'), r.get('SourceBooks'), r.get('Notes'), r.get('MeetingOrVisitEntities'), r.get('MeetingOrVisitOutcomes'))
    rec = {
        'id': node_id, 'label': label, 'category': category, 'group': category, 'sheet': 'Entities', 'color': COLOR_MAP.get(category, '#666666'),
        'aliases': aliases, 'description': clean_str(r.get('ShortDescription')), 'sourceBooks': split_multi(r.get('SourceBooks')),
        'sourceRefs': clean_str(r.get('SourceRefsPDFPages')), 'notes': clean_str(r.get('Notes')),
        'explorerIDs': split_multi(r.get('ExplorerIDs')), 'explorerNames': split_multi(r.get('ExplorerNames')),
        'underpinningIDs': split_multi(r.get('UnderpinningIDs')), 'underpinningNames': split_multi(r.get('UnderpinningNames')),
        'meetingEntities': split_multi(r.get('MeetingOrVisitEntities')), 'meetingDates': split_dates(r.get('MeetingOrVisitDates')),
        'meetingOutcomes': split_outcomes(r.get('MeetingOrVisitOutcomes')), 'directPresetTags': detect_direct_presets(text)
    }
    node_records[node_id] = rec
    id_to_label[node_id] = label
    id_to_category[node_id] = category
    register_name(label, node_id)
    for a in aliases:
        register_name(a, node_id)

for r in underpinnings:
    node_id = clean_str(r.get('UnderpinningID'))
    if not node_id:
        continue
    label = clean_str(r.get('CanonicalName')) or node_id
    aliases = split_multi(r.get('Aliases'))
    text = gather_text(label, aliases, r.get('ShortDescription'), r.get('RelatedEntityNames'), r.get('SourceBooks'), r.get('Notes'))
    rec = {
        'id': node_id, 'label': label, 'category': 'Underpinning', 'group': 'Underpinning', 'sheet': 'Underpinnings', 'color': COLOR_MAP['Underpinning'],
        'subclass': clean_str(r.get('UnderpinningClass')), 'subtype': clean_str(r.get('UnderpinningType')),
        'aliases': aliases, 'description': clean_str(r.get('ShortDescription')), 'sourceBooks': split_multi(r.get('SourceBooks')),
        'sourceRefs': clean_str(r.get('SourceRefsPDFPages')), 'notes': clean_str(r.get('Notes')),
        'relatedEntityIDs': split_multi(r.get('RelatedEntityIDs')), 'relatedEntityNames': split_multi(r.get('RelatedEntityNames')),
        'relatedExplorerIDs': split_multi(r.get('RelatedExplorerIDs')), 'relatedExplorerNames': split_multi(r.get('RelatedExplorerNames')),
        'directPresetTags': detect_direct_presets(text)
    }
    node_records[node_id] = rec
    id_to_label[node_id] = label
    id_to_category[node_id] = 'Underpinning'
    register_name(label, node_id)
    for a in aliases:
        register_name(a, node_id)

for r in explorers:
    node_id = clean_str(r.get('ExplorerID'))
    if not node_id:
        continue
    label = clean_str(r.get('StandardName')) or node_id
    aliases = [clean_str(r.get('NameAsInBook'))] if clean_str(r.get('NameAsInBook')) else []
    text = gather_text(label, aliases, r.get('KeyObservationsOrContributions'), r.get('MainPurpose'), r.get('RelatedPlaceEntityNames'), r.get('RelatedPersonEntityNames'), r.get('RelatedUnderpinningNames'), r.get('SourceBooks'), r.get('Notes'))
    rec = {
        'id': node_id, 'label': label, 'category': 'Explorer', 'group': 'Explorer', 'sheet': 'Explorers', 'color': COLOR_MAP['Explorer'],
        'recordType': clean_str(r.get('RecordType')), 'nationality': clean_str(r.get('Nationality')), 'occupationRole': clean_str(r.get('OccupationRole')),
        'affiliationOrMission': clean_str(r.get('AffiliationOrMission')), 'aliases': aliases,
        'description': clean_str(r.get('KeyObservationsOrContributions')) or clean_str(r.get('MainPurpose')),
        'sourceBooks': split_multi(r.get('SourceBooks')), 'sourceRefs': clean_str(r.get('SourceRefsPDFPages')), 'notes': clean_str(r.get('Notes')),
        'relatedPlaceEntityIDs': split_multi(r.get('RelatedPlaceEntityIDs')), 'relatedPlaceEntityNames': split_multi(r.get('RelatedPlaceEntityNames')),
        'relatedPersonEntityIDs': split_multi(r.get('RelatedPersonEntityIDs')), 'relatedPersonEntityNames': split_multi(r.get('RelatedPersonEntityNames')),
        'relatedUnderpinningIDs': split_multi(r.get('RelatedUnderpinningIDs')), 'relatedUnderpinningNames': split_multi(r.get('RelatedUnderpinningNames')),
        'visitYearsText': clean_str(r.get('VisitYearsText')), 'mainPurpose': clean_str(r.get('MainPurpose')),
        'directPresetTags': detect_direct_presets(text)
    }
    node_records[node_id] = rec
    id_to_label[node_id] = label
    id_to_category[node_id] = 'Explorer'
    register_name(label, node_id)
    for a in aliases:
        register_name(a, node_id)

# -----------------------------
# Edges
# -----------------------------
edges = []
edge_set = set()

def edge_presets(source, target, *texts):
    tags = set(node_records.get(source, {}).get('directPresetTags', [])) | set(node_records.get(target, {}).get('directPresetTags', []))
    tags |= set(detect_direct_presets(' '.join(clean_str(t) for t in texts)))
    return sorted(tags)

def add_edge(source, target, edge_type, label='', title='', weight=1, directed=False, extra=None):
    source = clean_str(source)
    target = clean_str(target)
    if not source or not target or source not in node_records or target not in node_records:
        return
    key = (source, target, edge_type, label, clean_str(extra.get('date') if extra else ''))
    if key in edge_set:
        return
    edge_set.add(key)
    presets = edge_presets(source, target, label, title, extra.get('outcome', '') if extra else '')
    e = {'id': f'e{len(edges)+1}', 'source': source, 'target': target, 'type': edge_type, 'label': label, 'title': title or label or edge_type, 'weight': weight, 'directed': directed, 'presetTags': presets}
    if extra:
        e.update(extra)
    edges.append(e)

for r in entities:
    src = clean_str(r.get('EntityID'))
    for uid in split_multi(r.get('UnderpinningIDs')):
        add_edge(src, uid, 'underpinning', label='associated with', title='Entity ↔ Underpinning association')
    for eid in split_multi(r.get('ExplorerIDs')):
        add_edge(eid, src, 'explorer_link', label='documented / linked', title='Explorer ↔ Entity association')
    meet_names = split_multi(r.get('MeetingOrVisitEntities'))
    meet_dates = split_dates(r.get('MeetingOrVisitDates'))
    meet_outcomes = split_outcomes(r.get('MeetingOrVisitOutcomes'))
    full_outcome = clean_str(r.get('MeetingOrVisitOutcomes'))
    for i, name in enumerate(meet_names):
        tgt = name_to_id.get(norm_name(name))
        if not tgt:
            continue
        date = meet_dates[i] if i < len(meet_dates) else (meet_dates[0] if len(meet_dates) == 1 else '')
        outcome = meet_outcomes[i] if i < len(meet_outcomes) else (full_outcome if full_outcome else '')
        title = f"Meeting/visit: {id_to_label.get(src, src)} ↔ {id_to_label.get(tgt, tgt)}"
        if date:
            title += f"<br>Date(s): {escape(date)}"
        if outcome:
            title += f"<br>Outcome: {escape(outcome)}"
        add_edge(src, tgt, 'meeting_visit', label='meeting / visit', title=title, extra={'date': date, 'outcome': outcome})

for r in explorers:
    src = clean_str(r.get('ExplorerID'))
    for col in ['RelatedPlaceEntityIDs', 'RelatedPersonEntityIDs']:
        for tgt in split_multi(r.get(col)):
            add_edge(src, tgt, 'explorer_link', label='related in explorer record', title='Explorer ↔ Entity link')
    for tgt in split_multi(r.get('RelatedUnderpinningIDs')):
        add_edge(src, tgt, 'explorer_link', label='related in explorer record', title='Explorer ↔ Underpinning link')
    cand = clean_str(r.get('ExplorerCandidateEntityID'))
    if cand:
        add_edge(src, cand, 'explorer_link', label='possible identity match', title='Explorer ↔ possible entity match')

for r in underpinnings:
    src = clean_str(r.get('UnderpinningID'))
    for tgt in split_multi(r.get('RelatedEntityIDs')):
        add_edge(src, tgt, 'underpinning', label='relates to', title='Underpinning ↔ Entity link')
    for tgt in split_multi(r.get('RelatedExplorerIDs')):
        add_edge(src, tgt, 'explorer_link', label='mentioned by explorer', title='Underpinning ↔ Explorer link')

# Presets are direct heuristic tags. This keeps lineage filters precise and avoids
# flooding through highly connected generic nodes such as Ladakh or Tibet.
direct_tag_by_node = {nid: set(rec.get('directPresetTags', [])) for nid, rec in node_records.items()}
node_preset_tags = {nid: set(tags) for nid, tags in direct_tag_by_node.items()}
for e in edges:
    tags = set(e.get('presetTags', [])) | direct_tag_by_node[e['source']] | direct_tag_by_node[e['target']]
    e['presetTags'] = sorted(tags)

# -----------------------------
# Build nodes + coordinate / related summaries
# -----------------------------
degree = Counter()
related = defaultdict(lambda: defaultdict(set))
for e in edges:
    degree[e['source']] += 1
    degree[e['target']] += 1
    for a, b in [(e['source'], e['target']), (e['target'], e['source'])]:
        related[a][id_to_category.get(b, '')].add(b)
        related[a][f"edge:{e['type']}"].add(b)
        related[a]['all'].add(b)

nodes = []
for node_id, rec in node_records.items():
    subtitle = ''
    if rec['category'] == 'Underpinning':
        subtitle = ' / '.join(x for x in [rec.get('subclass',''), rec.get('subtype','')] if x)
    elif rec['category'] == 'Explorer':
        subtitle = ' / '.join(x for x in [rec.get('occupationRole',''), rec.get('nationality','')] if x)
    lines = [f"<b>{rec['label']}</b>", f"Category: {rec['category']}"]
    if subtitle:
        lines.append(subtitle)
    if rec.get('description'):
        lines.append(rec['description'])
    if rec.get('sourceBooks'):
        sources = '; '.join(rec['sourceBooks'][:6]) + (' …' if len(rec['sourceBooks']) > 6 else '')
        lines.append('Sources: ' + sources)
    node = {
        'id': node_id, 'label': rec['label'], 'category': rec['category'], 'group': rec['group'], 'sheet': rec['sheet'], 'color': rec['color'],
        'title': html_title(lines), 'description': rec.get('description',''), 'aliases': rec.get('aliases',[]), 'sourceBooks': rec.get('sourceBooks',[]),
        'sourceRefs': rec.get('sourceRefs',''), 'notes': rec.get('notes',''), 'metadata': rec,
        'directPresetTags': sorted(set(rec.get('directPresetTags', []))), 'presetTags': sorted(node_preset_tags[node_id]),
        'degree': int(degree[node_id]), 'value': max(8, min(42, 8 + int(degree[node_id]) * 1.25)),
        'relatedCounts': {k: len(v) for k, v in related[node_id].items() if k != 'all'},
        'relatedSample': {cat: [id_to_label.get(x, x) for x in sorted(list(v))[:12]] for cat, v in related[node_id].items() if cat in {'Person','Place','Asset','Underpinning','Explorer'}}
    }
    if rec['category'] == 'Place' and rec['label'] in PLACE_COORDS:
        c = PLACE_COORDS[rec['label']]
        node['lat'] = c['lat']
        node['lon'] = c['lon']
        node['coordinateStatus'] = c.get('status', 'seeded_approximate')
        node['coordinateNotes'] = c.get('notes', 'Approximate seed coordinate. Review through the map enrichment workflow before using for spatial analysis.')
    nodes.append(node)

node_by_id = {n['id']: n for n in nodes}

# Keep edge preset tags tied to direct matches and literal edge text.
# Node preset tags may include one-hop contextual expansion, but edges do not cascade further.
for e in edges:
    e['presetTags'] = sorted(set(e.get('presetTags', [])))

# -----------------------------
# Timeline data
# -----------------------------
def parse_years(date_text):
    s = clean_str(date_text).lower().replace('–', '-').replace('—', '-').replace('c.', '').replace('ca.', '').replace('circa', '')
    if not s:
        return None, None, 'unknown'
    # 1625/26 style
    slash = re.search(r'(\d{3,4})\s*/\s*(\d{2})(?!\d)', s)
    if slash:
        first = int(slash.group(1))
        suffix = slash.group(2)
        prefix = str(first)[:len(str(first))-len(suffix)]
        second = int(prefix + suffix)
        return first, second, 'approximate'
    # 18th-19th century / 11th century
    century_range = re.search(r'(\d{1,2})(?:st|nd|rd|th)\s*-\s*(\d{1,2})(?:st|nd|rd|th)\s+centur', s)
    if century_range:
        a, b = int(century_range.group(1)), int(century_range.group(2))
        return (a - 1) * 100, b * 100, 'century'
    century = re.search(r'(\d{1,2})(?:st|nd|rd|th)\s+centur', s)
    if century:
        c = int(century.group(1))
        return (c - 1) * 100, c * 100, 'century'
    years = [int(y) for y in re.findall(r'(?<!\d)(\d{3,4})(?!\d)', s)]
    if years:
        start, end = min(years), max(years)
        if 'before' in s:
            start = max(1, end - 75)
        elif 'after' in s or 'onward' in s:
            end = start + 75
        return start, end, 'approximate' if any(x in s for x in ['before', 'after', 'onward', 'approx']) else 'year'
    return None, None, 'textual'

def year_to_date(y):
    if y is None:
        return None
    # JavaScript and ISO date parsing behave better with 4-digit years.
    return f"{int(y):04d}-01-01"

timeline_items = []
for e in edges:
    if e['type'] != 'meeting_visit':
        continue
    sy, ey, precision = parse_years(e.get('date',''))
    item = {
        'id': e['id'], 'sourceId': e['source'], 'targetId': e['target'], 'sourceLabel': id_to_label.get(e['source'], e['source']),
        'targetLabel': id_to_label.get(e['target'], e['target']), 'dateText': e.get('date',''), 'outcome': e.get('outcome',''),
        'startYear': sy, 'endYear': ey, 'startDate': year_to_date(sy), 'endDate': year_to_date(ey), 'precision': precision,
        'sortKey': sy if sy is not None else 999999, 'presetTags': e.get('presetTags', []),
        'sourceBooks': sorted(set(node_by_id[e['source']].get('sourceBooks', []) + node_by_id[e['target']].get('sourceBooks', [])))
    }
    timeline_items.append(item)
timeline_items.sort(key=lambda x: (x['sortKey'], x['sourceLabel'], x['targetLabel']))

# -----------------------------
# GeoJSON + backlog + place links
# -----------------------------
features = []
backlog = []
for n in nodes:
    if n['category'] != 'Place':
        continue
    if 'lat' in n and 'lon' in n:
        features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [n['lon'], n['lat']]}, 'properties': {
            'id': n['id'], 'label': n['label'], 'description': n.get('description',''), 'degree': n.get('degree',0),
            'sourceBooks': n.get('sourceBooks',[]), 'sourceRefs': n.get('sourceRefs',''), 'relatedCounts': n.get('relatedCounts',{}),
            'relatedSample': n.get('relatedSample',{}), 'presetTags': n.get('presetTags',[]), 'coordinateStatus': n.get('coordinateStatus','seeded_approximate'),
            'coordinateNotes': n.get('coordinateNotes','')
        }})
    else:
        backlog.append({
            'EntityID': n['id'], 'CanonicalName': n['label'], 'Description': n.get('description',''),
            'SourceBooks': '; '.join(n.get('sourceBooks', [])), 'SuggestedSearchQuery': f"{n['label']} Ladakh Tibet Buddhist site coordinates",
            'Status': 'needs_review', 'Latitude': '', 'Longitude': '', 'CoordinateStatus': '', 'CoordinateNotes': '', 'Reviewer': '', 'ReviewedDate': ''
        })

place_links = []
for e in edges:
    s, t = node_by_id.get(e['source']), node_by_id.get(e['target'])
    if not s or not t:
        continue
    if s.get('category') == 'Place' and t.get('category') == 'Place' and 'lat' in s and 'lat' in t:
        place_links.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[s['lon'], s['lat']], [t['lon'], t['lat']]]}, 'properties': {
            'id': e['id'], 'sourceId': s['id'], 'targetId': t['id'], 'sourceLabel': s['label'], 'targetLabel': t['label'],
            'edgeType': e['type'], 'label': e.get('label',''), 'date': e.get('date',''), 'outcome': e.get('outcome',''), 'presetTags': e.get('presetTags',[])
        }})

geojson = {'type': 'FeatureCollection', 'features': features}
place_links_geojson = {'type': 'FeatureCollection', 'features': place_links}

# -----------------------------
# Data files
# -----------------------------
summary = {
    'workbook': WORKBOOK.name,
    'nodeCount': len(nodes), 'edgeCount': len(edges), 'countsByCategory': dict(Counter(n['category'] for n in nodes)),
    'placeCountWithCoordinates': len(features), 'placeCountTotal': sum(1 for n in nodes if n['category'] == 'Place'),
    'placeCoordinateBacklogCount': len(backlog), 'meetingVisitEdgeCount': len(timeline_items),
    'presetDefinitions': PRESET_DEFINITIONS,
    'presetCounts': {key: sum(1 for n in nodes if key in n.get('presetTags', [])) for key in PRESET_DEFINITIONS}
}

graph_json = {'summary': summary, 'nodes': nodes, 'edges': edges, 'references': references, 'presetDefinitions': PRESET_DEFINITIONS}
(DATADIR / 'ladakh_graph.json').write_text(json.dumps(graph_json, ensure_ascii=False, indent=2), encoding='utf-8')
(DATADIR / 'places.geojson').write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding='utf-8')
(DATADIR / 'place_links.geojson').write_text(json.dumps(place_links_geojson, ensure_ascii=False, indent=2), encoding='utf-8')
(DATADIR / 'meetings_timeline.json').write_text(json.dumps({'summary': summary, 'items': timeline_items}, ensure_ascii=False, indent=2), encoding='utf-8')
(DATADIR / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

# CSV writers
with (DATADIR / 'nodes.csv').open('w', newline='', encoding='utf-8') as f:
    fieldnames = ['id','label','category','sheet','degree','directPresetTags','presetTags','description','aliases','sourceBooks','sourceRefs','lat','lon','coordinateStatus','coordinateNotes']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for n in nodes:
        w.writerow({k: json.dumps(n.get(k, ''), ensure_ascii=False) if isinstance(n.get(k, ''), (list, dict)) else n.get(k, '') for k in fieldnames})

with (DATADIR / 'edges.csv').open('w', newline='', encoding='utf-8') as f:
    fieldnames = ['id','source','target','type','label','date','outcome','presetTags','title']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for e in edges:
        w.writerow({k: json.dumps(e.get(k, ''), ensure_ascii=False) if isinstance(e.get(k, ''), (list, dict)) else e.get(k, '') for k in fieldnames})

with (DATADIR / 'meetings_timeline.csv').open('w', newline='', encoding='utf-8') as f:
    fieldnames = ['id','sourceLabel','targetLabel','dateText','startYear','endYear','precision','outcome','presetTags','sourceBooks']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for item in timeline_items:
        w.writerow({k: json.dumps(item.get(k, ''), ensure_ascii=False) if isinstance(item.get(k, ''), (list, dict)) else item.get(k, '') for k in fieldnames})

with (DATADIR / 'references_used.csv').open('w', newline='', encoding='utf-8') as f:
    fieldnames = list(references[0].keys()) if references else []
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in references:
        w.writerow(r)

with (DATADIR / 'place_coordinates_seed.csv').open('w', newline='', encoding='utf-8') as f:
    fieldnames = ['CanonicalName','Latitude','Longitude','CoordinateStatus','CoordinateNotes']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for name, c in sorted(PLACE_COORDS.items()):
        w.writerow({'CanonicalName': name, 'Latitude': c['lat'], 'Longitude': c['lon'], 'CoordinateStatus': c.get('status', 'seeded_approximate'), 'CoordinateNotes': c.get('notes', 'Approximate seed coordinate; review before spatial analysis.')})

with (DATADIR / 'place_coordinate_backlog.csv').open('w', newline='', encoding='utf-8') as f:
    fieldnames = ['EntityID','CanonicalName','Description','SourceBooks','SuggestedSearchQuery','Status','Latitude','Longitude','CoordinateStatus','CoordinateNotes','Reviewer','ReviewedDate']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for row in sorted(backlog, key=lambda r: r['CanonicalName']):
        w.writerow(row)

# GraphML export, stdlib
GRAPHML_NS = 'http://graphml.graphdrawing.org/xmlns'
ET.register_namespace('', GRAPHML_NS)
gml = ET.Element(f'{{{GRAPHML_NS}}}graphml')
keys = [
    ('node_label','node','label'),('node_category','node','category'),('node_degree','node','degree'),('node_presetTags','node','presetTags'),
    ('node_description','node','description'),('node_lat','node','lat'),('node_lon','node','lon'),
    ('edge_type','edge','type'),('edge_label','edge','label'),('edge_date','edge','date'),('edge_outcome','edge','outcome'),('edge_presetTags','edge','presetTags')
]
for kid, domain, attr in keys:
    ET.SubElement(gml, f'{{{GRAPHML_NS}}}key', id=kid, **{'for': domain, 'attr.name': attr, 'attr.type': 'string'})
graph = ET.SubElement(gml, f'{{{GRAPHML_NS}}}graph', edgedefault='undirected')
for n in nodes:
    ne = ET.SubElement(graph, f'{{{GRAPHML_NS}}}node', id=n['id'])
    vals = {'node_label': n['label'], 'node_category': n['category'], 'node_degree': str(n['degree']), 'node_presetTags': '; '.join(n.get('presetTags', [])), 'node_description': n.get('description',''), 'node_lat': str(n.get('lat','')), 'node_lon': str(n.get('lon',''))}
    for k, v in vals.items():
        de = ET.SubElement(ne, f'{{{GRAPHML_NS}}}data', key=k)
        de.text = v
for e in edges:
    ee = ET.SubElement(graph, f'{{{GRAPHML_NS}}}edge', id=e['id'], source=e['source'], target=e['target'])
    vals = {'edge_type': e['type'], 'edge_label': e.get('label',''), 'edge_date': e.get('date',''), 'edge_outcome': e.get('outcome',''), 'edge_presetTags': '; '.join(e.get('presetTags', []))}
    for k, v in vals.items():
        de = ET.SubElement(ee, f'{{{GRAPHML_NS}}}data', key=k)
        de.text = v
ET.ElementTree(gml).write(DATADIR / 'ladakh_network.graphml', encoding='utf-8', xml_declaration=True)


print(json.dumps(summary, indent=2, ensure_ascii=False))
print(f'Graph data rebuilt in {DATADIR}')
