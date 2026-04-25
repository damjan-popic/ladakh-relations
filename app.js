let graphData = null;
let timelineData = null;
let geoData = null;
let placeLinksData = null;
let geocodeBacklog = [];
let network = null;
let map = null;
let markersLayer = null;
let placeLinksLayer = null;
let physicsEnabled = true;
let activePreset = 'all';
let activeView = 'network';

const nodeColorMap = { Person: '#d95f02', Place: '#1b9e77', Asset: '#e6ab02', Underpinning: '#6a3d9a', Explorer: '#1f3b73' };
const presetNames = { all: 'All', kagyu: 'Kagyu', nyingma: 'Nyingma / Dzogchen', drukpa: 'Drukpa / Brugpa' };
function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return [...document.querySelectorAll(sel)]; }
function esc(s) { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function tagsHtml(tags) { return (tags || []).map(t => `<span class="badge ${t}">${esc(presetNames[t] || t)}</span>`).join(''); }
function formatList(items, limit = 12) { if (!items || items.length === 0) return '—'; const shown = items.slice(0, limit); return shown.map(esc).join(', ') + (items.length > limit ? ` … (+${items.length - limit} more)` : ''); }
function currentSearch() { return qs('#search-input').value.trim().toLowerCase(); }
function currentNodeCategories() { return new Set(qsa('.node-filter:checked').map(el => el.value)); }
function currentEdgeTypes() { return new Set(qsa('.edge-filter:checked').map(el => el.value)); }
function passPreset(obj) { return activePreset === 'all' || (obj.presetTags || []).includes(activePreset); }
function passSearchNode(n) { const q = currentSearch(); if (!q) return true; const blob = [n.label, n.description, ...(n.aliases || []), ...(n.sourceBooks || []), ...(n.presetTags || [])].join(' ').toLowerCase(); return blob.includes(q); }
function passSearchTimeline(item) { const q = currentSearch(); if (!q) return true; const blob = [item.sourceLabel, item.targetLabel, item.dateText, item.outcome, ...(item.sourceBooks || []), ...(item.presetTags || [])].join(' ').toLowerCase(); return blob.includes(q); }

function setDetailsForNode(node) {
  qs('#details-box').innerHTML = `
    ${tagsHtml(node.presetTags)}
    <h3 style="margin:.35rem 0 .5rem 0;">${esc(node.label)}</h3>
    <div class="kv">
      <div><strong>ID</strong></div><div>${esc(node.id)}</div>
      <div><strong>Category</strong></div><div>${esc(node.category)}</div>
      <div><strong>Sheet</strong></div><div>${esc(node.sheet)}</div>
      <div><strong>Degree</strong></div><div>${node.degree ?? '—'}</div>
      <div><strong>Aliases</strong></div><div>${formatList(node.aliases || [])}</div>
      <div><strong>Description</strong></div><div>${esc(node.description || '—')}</div>
      <div><strong>Sources</strong></div><div>${formatList(node.sourceBooks || [], 8)}</div>
      <div><strong>Source refs</strong></div><div>${esc(node.sourceRefs || '—')}</div>
      <div><strong>Related persons</strong></div><div>${formatList((node.relatedSample && node.relatedSample.Person) || [])}</div>
      <div><strong>Related places</strong></div><div>${formatList((node.relatedSample && node.relatedSample.Place) || [])}</div>
      <div><strong>Related underpinnings</strong></div><div>${formatList((node.relatedSample && node.relatedSample.Underpinning) || [])}</div>
      <div><strong>Related explorers</strong></div><div>${formatList((node.relatedSample && node.relatedSample.Explorer) || [])}</div>
      <div><strong>Coordinates</strong></div><div>${node.lat ? `${node.lat}, ${node.lon}<br><span class="hint">${esc(node.coordinateNotes || '')}</span>` : '—'}</div>
      <div><strong>Notes</strong></div><div>${esc(node.notes || '—')}</div>
    </div>`;
}

function setDetailsForFeature(feature) {
  const p = feature.properties;
  qs('#details-box').innerHTML = `
    ${tagsHtml(p.presetTags)}
    <h3 style="margin:.35rem 0 .5rem 0;">${esc(p.label)}</h3>
    <div class="kv">
      <div><strong>ID</strong></div><div>${esc(p.id)}</div>
      <div><strong>Degree</strong></div><div>${p.degree ?? '—'}</div>
      <div><strong>Description</strong></div><div>${esc(p.description || '—')}</div>
      <div><strong>Sources</strong></div><div>${formatList(p.sourceBooks || [], 8)}</div>
      <div><strong>Source refs</strong></div><div>${esc(p.sourceRefs || '—')}</div>
      <div><strong>Coordinate status</strong></div><div>${esc(p.coordinateStatus || '—')}<br><span class="hint">${esc(p.coordinateNotes || '')}</span></div>
      <div><strong>Related persons</strong></div><div>${formatList((p.relatedSample && p.relatedSample.Person) || [])}</div>
      <div><strong>Related underpinnings</strong></div><div>${formatList((p.relatedSample && p.relatedSample.Underpinning) || [])}</div>
    </div>`;
}

function setDetailsForTimeline(item) {
  qs('#details-box').innerHTML = `
    ${tagsHtml(item.presetTags)}
    <h3 style="margin:.35rem 0 .5rem 0;">${esc(item.sourceLabel)} ↔ ${esc(item.targetLabel)}</h3>
    <div class="kv">
      <div><strong>Date text</strong></div><div>${esc(item.dateText || '—')}</div>
      <div><strong>Parsed range</strong></div><div>${item.startYear ? `${item.startYear}${item.endYear && item.endYear !== item.startYear ? '–' + item.endYear : ''}` : '—'} <span class="hint">${esc(item.precision || '')}</span></div>
      <div><strong>Outcome</strong></div><div>${esc(item.outcome || '—')}</div>
      <div><strong>Sources</strong></div><div>${formatList(item.sourceBooks || [], 8)}</div>
    </div>`;
}

function filteredNodesAndEdges() {
  const allowedNodes = currentNodeCategories();
  const allowedEdges = currentEdgeTypes();
  const visibleNodes = graphData.nodes.filter(n => allowedNodes.has(n.category) && passPreset(n) && passSearchNode(n));
  const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = graphData.edges.filter(e => allowedEdges.has(e.type) && passPreset(e) && visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target));
  return { visibleNodes, visibleEdges, visibleNodeIds };
}

function applyFilters() {
  if (!graphData || !network) return;
  const { visibleNodes, visibleEdges } = filteredNodesAndEdges();
  const visNodes = new vis.DataSet(visibleNodes.map(n => ({ id: n.id, label: n.label, group: n.category, color: n.color, value: n.value, title: n.title, font: { size: 16 }, shape: n.category === 'Underpinning' ? 'hexagon' : 'dot' })));
  const visEdges = new vis.DataSet(visibleEdges.map(e => ({ id: e.id, from: e.source, to: e.target, title: e.title, dashes: e.type === 'meeting_visit', color: e.type === 'underpinning' ? '#9b7fc0' : (e.type === 'meeting_visit' ? '#7f8c8d' : '#5677a6'), arrows: e.directed ? 'to' : '' })));
  network.setData({ nodes: visNodes, edges: visEdges });
  renderMapLayers();
  renderTimeline();
  updateStats();
}

function initNetwork() {
  network = new vis.Network(qs('#network'), { nodes: [], edges: [] }, { physics: { stabilization: true, barnesHut: { gravitationalConstant: -30000, springLength: 120, damping: 0.5 } }, interaction: { hover: true, navigationButtons: true, keyboard: true }, groups: { Person: { color: nodeColorMap.Person }, Place: { color: nodeColorMap.Place }, Asset: { color: nodeColorMap.Asset }, Underpinning: { color: nodeColorMap.Underpinning }, Explorer: { color: nodeColorMap.Explorer } }, edges: { smooth: { type: 'dynamic' }, width: 1.2 }, nodes: { borderWidth: 1.2 } });
  network.on('click', params => { if (params.nodes && params.nodes.length) { const node = graphData.nodes.find(n => n.id === params.nodes[0]); if (node) setDetailsForNode(node); } });
  applyFilters();
}

function initMap() {
  map = L.map('map').setView([34.2, 77.6], 6);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
  renderMapLayers();
}

function renderMapLayers() {
  if (!map || !geoData) return;
  if (markersLayer) map.removeLayer(markersLayer);
  if (placeLinksLayer) map.removeLayer(placeLinksLayer);
  const q = currentSearch();
  const filteredFeatures = geoData.features.filter(f => passPreset(f.properties) && (!q || [f.properties.label, f.properties.description, ...(f.properties.sourceBooks || []), ...(f.properties.presetTags || [])].join(' ').toLowerCase().includes(q)));
  markersLayer = L.geoJSON({ type: 'FeatureCollection', features: filteredFeatures }, {
    pointToLayer: function(feature, latlng) { return L.circleMarker(latlng, { radius: Math.max(5, Math.min(16, 5 + (feature.properties.degree || 0) * 0.25)), fillColor: nodeColorMap.Place, color: '#245d50', weight: 1, opacity: 1, fillOpacity: 0.75 }); },
    onEachFeature: function(feature, layer) { const p = feature.properties; layer.bindPopup(`<strong>${esc(p.label)}</strong><br>${esc(p.description || '')}<br><br><strong>Related persons:</strong> ${formatList((p.relatedSample && p.relatedSample.Person) || [], 8)}`); layer.on('click', () => setDetailsForFeature(feature)); }
  }).addTo(map);
  const showLinks = qs('#place-links-toggle') && qs('#place-links-toggle').checked;
  if (showLinks && placeLinksData) {
    const filteredLinks = placeLinksData.features.filter(f => passPreset(f.properties));
    placeLinksLayer = L.geoJSON({ type: 'FeatureCollection', features: filteredLinks }, { style: { color: '#5d718c', weight: 1.5, opacity: 0.45 }, onEachFeature: function(feature, layer) { const p = feature.properties; layer.bindPopup(`<strong>${esc(p.sourceLabel)} ↔ ${esc(p.targetLabel)}</strong><br>${esc(p.edgeType)} ${p.date ? '<br>' + esc(p.date) : ''}`); } }).addTo(map);
  }
}

function eraLabel(item) {
  if (!item.startYear) return 'Textual or undated meetings';
  const c = Math.floor((item.startYear - 1) / 100) + 1;
  const suffix = c === 1 ? 'st' : c === 2 ? 'nd' : c === 3 ? 'rd' : 'th';
  return `${c}${suffix} century`;
}

function renderTimeline() {
  if (!timelineData) return;
  const items = timelineData.items.filter(item => passPreset(item) && passSearchTimeline(item));
  qs('#timeline-count').textContent = `${items.length} meeting / visit records shown`;
  const groups = new Map();
  for (const item of items) { const k = eraLabel(item); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(item); }
  let html = '';
  for (const [era, group] of groups.entries()) {
    html += `<div class="timeline-era">${esc(era)}</div>`;
    for (const item of group) {
      const range = item.startYear ? `${item.startYear}${item.endYear && item.endYear !== item.startYear ? '–' + item.endYear : ''}` : (item.dateText || 'undated');
      html += `<article class="timeline-card" data-id="${esc(item.id)}"><div class="timeline-date">${esc(range)}</div><div><div class="timeline-title">${esc(item.sourceLabel)} ↔ ${esc(item.targetLabel)}</div><div class="timeline-outcome">${esc(item.outcome || 'No outcome recorded.')}</div><div class="timeline-tags">${tagsHtml(item.presetTags)}</div></div></article>`;
    }
  }
  qs('#timeline').innerHTML = html || '<p class="hint">No meeting / visit records match the current filters.</p>';
  qsa('.timeline-card').forEach(card => card.addEventListener('click', () => { const item = timelineData.items.find(x => x.id === card.dataset.id); if (item) setDetailsForTimeline(item); }));
}


const geocodeDraftKey = 'ladakhGeocodeDraftsV1';

function parseCSV(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], next = text[i + 1];
    if (c === '"' && inQuotes && next === '"') { field += '"'; i++; continue; }
    if (c === '"') { inQuotes = !inQuotes; continue; }
    if (c === ',' && !inQuotes) { row.push(field); field = ''; continue; }
    if ((c === '\n' || c === '\r') && !inQuotes) {
      if (c === '\r' && next === '\n') i++;
      row.push(field); field = '';
      if (row.some(x => x !== '')) rows.push(row);
      row = [];
      continue;
    }
    field += c;
  }
  if (field || row.length) { row.push(field); if (row.some(x => x !== '')) rows.push(row); }
  const headers = rows.shift() || [];
  return rows.map(values => Object.fromEntries(headers.map((h, i) => [h, values[i] || ''])));
}

function getGeocodeDrafts() {
  try { return JSON.parse(localStorage.getItem(geocodeDraftKey) || '{}'); }
  catch { return {}; }
}

function setGeocodeDraft(entityId, patch) {
  const drafts = getGeocodeDrafts();
  drafts[entityId] = { ...(drafts[entityId] || {}), ...patch };
  localStorage.setItem(geocodeDraftKey, JSON.stringify(drafts));
}

function renderGeocodeBacklog() {
  if (!geocodeBacklog || !qs('#geocode-table')) return;
  const q = (qs('#geocode-search') && qs('#geocode-search').value || '').trim().toLowerCase();
  const statusFilter = (qs('#geocode-status-filter') && qs('#geocode-status-filter').value) || 'all';
  const drafts = getGeocodeDrafts();
  let rows = geocodeBacklog.slice();
  if (q) rows = rows.filter(r => Object.values(r).join(' ').toLowerCase().includes(q));
  if (statusFilter !== 'all') rows = rows.filter(r => (drafts[r.EntityID]?.Status || r.Status || 'needs_review') === statusFilter);
  qs('#geocode-count').textContent = `${rows.length} backlog rows shown / ${geocodeBacklog.length} total`;
  const tbody = qs('#geocode-table tbody');
  tbody.innerHTML = '';
  for (const r of rows) {
    const d = drafts[r.EntityID] || {};
    const status = d.Status || r.Status || 'needs_review';
    const confidence = d.CoordinateConfidence || '';
    const osmUrl = `https://www.openstreetmap.org/search?query=${encodeURIComponent(r.SuggestedSearchQuery || r.CanonicalName)}`;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${esc(r.CanonicalName)}</strong><br><span class="hint">${esc(r.EntityID)}</span><br><span class="hint">${esc(r.Description || '')}</span></td>
      <td><a class="inline-link" href="${osmUrl}" target="_blank" rel="noopener">${esc(r.SuggestedSearchQuery || r.CanonicalName)}</a><br><span class="hint">${esc(r.SourceBooks || '')}</span></td>
      <td><select data-field="Status">
        ${['needs_review','manual_approved','ambiguous','not_found'].map(x => `<option value="${x}" ${status === x ? 'selected' : ''}>${x}</option>`).join('')}
      </select></td>
      <td><input data-field="Latitude" type="number" step="any" value="${esc(d.Latitude || r.Latitude || '')}" placeholder="34.1642"></td>
      <td><input data-field="Longitude" type="number" step="any" value="${esc(d.Longitude || r.Longitude || '')}" placeholder="77.5848"></td>
      <td><select data-field="CoordinateConfidence">
        ${['','exact_manual','approximate_manual','regional_anchor','uncertain_manual'].map(x => `<option value="${x}" ${confidence === x ? 'selected' : ''}>${x || 'select'}</option>`).join('')}
      </select></td>
      <td><textarea data-field="Notes" placeholder="Reviewer notes, source, ambiguity…">${esc(d.Notes || '')}</textarea></td>`;
    tr.addEventListener('click', () => {
      qs('#details-box').innerHTML = `<h3>${esc(r.CanonicalName)}</h3><div class="kv"><div><strong>ID</strong></div><div>${esc(r.EntityID)}</div><div><strong>Status</strong></div><div>${esc(status)}</div><div><strong>Description</strong></div><div>${esc(r.Description || '—')}</div><div><strong>Source books</strong></div><div>${esc(r.SourceBooks || '—')}</div><div><strong>Search</strong></div><div>${esc(r.SuggestedSearchQuery || '')}</div></div>`;
    });
    tr.querySelectorAll('[data-field]').forEach(el => {
      const save = () => setGeocodeDraft(r.EntityID, { EntityID: r.EntityID, CanonicalName: r.CanonicalName, Source: r.SuggestedSearchQuery || '', [el.dataset.field]: el.value });
      el.addEventListener('input', save);
      el.addEventListener('change', save);
    });
    tbody.appendChild(tr);
  }
}

function csvCell(value) {
  const s = String(value ?? '');
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

function exportGeocodeDrafts() {
  const drafts = Object.values(getGeocodeDrafts()).filter(d => d.Latitude && d.Longitude && (d.Status || 'manual_approved') !== 'not_found');
  const headers = ['EntityID','CanonicalName','Latitude','Longitude','CoordinateConfidence','Source','Notes'];
  const lines = [headers.join(',')];
  for (const d of drafts) lines.push(headers.map(h => csvCell(d[h])).join(','));
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'place_coordinates_custom.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

function updateStats() {
  if (!graphData) return;
  const s = graphData.summary;
  const filtered = filteredNodesAndEdges();
  const presetText = activePreset === 'all' ? '' : `<div><strong>Preset:</strong> ${esc(presetNames[activePreset])}</div>`;
  qs('#stats-box').innerHTML = `${presetText}
    <div><strong>Visible nodes:</strong> ${filtered.visibleNodes.length} / ${s.nodeCount}</div>
    <div><strong>Visible edges:</strong> ${filtered.visibleEdges.length} / ${s.edgeCount}</div>
    <hr><div><strong>Persons:</strong> ${s.countsByCategory.Person || 0}</div>
    <div><strong>Places:</strong> ${s.countsByCategory.Place || 0}</div>
    <div><strong>Underpinnings:</strong> ${s.countsByCategory.Underpinning || 0}</div>
    <div><strong>Explorers:</strong> ${s.countsByCategory.Explorer || 0}</div>
    <div><strong>Meetings/visits:</strong> ${s.meetingVisitEdgeCount}</div>`;
  qs('#enrichment-box').innerHTML = `<div><strong>Geocoded places:</strong> ${s.placeCountWithCoordinates} / ${s.placeCountTotal}</div><div><strong>Backlog:</strong> ${s.placeCoordinateBacklogCount} places need review</div><div><strong>Place links:</strong> ${(placeLinksData && placeLinksData.features.length) || 0}</div>`;
}

function searchAndFocus() {
  const q = currentSearch();
  if (!q) return;
  const node = graphData.nodes.find(n => passPreset(n) && (n.label.toLowerCase().includes(q) || (n.aliases || []).some(a => a.toLowerCase().includes(q))));
  applyFilters();
  if (node) {
    setDetailsForNode(node);
    switchView('network');
    setTimeout(() => { network.selectNodes([node.id]); network.focus(node.id, { scale: 1.2, animation: true }); }, 50);
    if (node.category === 'Place' && node.lat && node.lon && map) map.setView([node.lat, node.lon], 8);
  }
}

function switchView(view) {
  activeView = view;
  ['network', 'map', 'timeline', 'geocode'].forEach(v => { qs(`#${v}-view`).classList.toggle('active', v === view); qs(`#show-${v}-btn`).classList.toggle('active', v === view); });
  setTimeout(() => { if (view === 'network' && network) network.redraw(); if (view === 'map' && map) map.invalidateSize(); if (view === 'geocode') renderGeocodeBacklog(); }, 80);
}

function setPreset(preset) {
  activePreset = preset;
  qsa('.preset-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.preset === preset));
  const defs = graphData.presetDefinitions || {};
  qs('#preset-description').textContent = preset === 'all' ? 'Showing the full network.' : (defs[preset] && defs[preset].description) || '';
  applyFilters();
}

function initUI() {
  qsa('.node-filter, .edge-filter').forEach(el => el.addEventListener('change', applyFilters));
  qsa('.preset-btn').forEach(btn => btn.addEventListener('click', () => setPreset(btn.dataset.preset)));
  qs('#search-btn').addEventListener('click', searchAndFocus);
  qs('#search-input').addEventListener('keydown', e => { if (e.key === 'Enter') searchAndFocus(); });
  qs('#search-input').addEventListener('input', () => { renderTimeline(); renderMapLayers(); });
  qs('#reset-btn').addEventListener('click', () => { qs('#search-input').value = ''; qsa('.node-filter, .edge-filter').forEach(el => el.checked = true); setPreset('all'); applyFilters(); if (network) network.fit({ animation: true }); });
  qs('#fit-btn').addEventListener('click', () => network.fit({ animation: true }));
  qs('#physics-btn').addEventListener('click', () => { physicsEnabled = !physicsEnabled; network.setOptions({ physics: { enabled: physicsEnabled } }); });
  qs('#show-network-btn').addEventListener('click', () => switchView('network'));
  qs('#show-map-btn').addEventListener('click', () => switchView('map'));
  qs('#show-timeline-btn').addEventListener('click', () => switchView('timeline'));
  qs('#show-geocode-btn').addEventListener('click', () => switchView('geocode'));
  qs('#geocode-search').addEventListener('input', renderGeocodeBacklog);
  qs('#geocode-status-filter').addEventListener('change', renderGeocodeBacklog);
  qs('#export-geocode-btn').addEventListener('click', exportGeocodeDrafts);
  qs('#clear-geocode-drafts-btn').addEventListener('click', () => { if (confirm('Clear saved coordinate drafts from this browser?')) { localStorage.removeItem(geocodeDraftKey); renderGeocodeBacklog(); } });
  qs('#place-links-toggle').addEventListener('change', renderMapLayers);
}

async function loadJson(path) {
  const res = await fetch(path, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${path} returned HTTP ${res.status}`);
  return await res.json();
}
async function loadText(path) {
  const res = await fetch(path, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${path} returned HTTP ${res.status}`);
  return await res.text();
}
function showBootError(err) {
  console.error(err);
  const msg = `Failed to load database files: ${esc(err.message || err)}. Check that app.js, style.css, data/, and docs/ are uploaded to the repository root. Also open site-health.html for a file-by-file check.`;
  const stats = qs('#stats-box');
  const enrich = qs('#enrichment-box');
  const details = qs('#details-box');
  if (stats) stats.innerHTML = `<span class="error-text">${msg}</span>`;
  if (enrich) enrich.innerHTML = `<span class="error-text">Map enrichment cannot load until the data files are reachable.</span>`;
  if (details) details.innerHTML = `<a href="site-health.html">Run the site health check</a>`;
}
async function boot() {
  graphData = await loadJson('data/ladakh_graph.json');
  timelineData = await loadJson('data/meetings_timeline.json');
  geoData = await loadJson('data/places.geojson');
  placeLinksData = await loadJson('data/place_links.geojson');
  geocodeBacklog = parseCSV(await loadText('data/place_coordinate_backlog.csv'));
  initNetwork();
  initMap();
  initUI();
  updateStats();
  renderTimeline();
  renderGeocodeBacklog();
  network.fit({ animation: true });
}
boot().catch(showBootError);
