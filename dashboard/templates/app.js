// ─────────────────────────────────────────────────────────
//  Lineage IDE — app.js
//  All client-side logic for the Data Lineage IDE dashboard
// ─────────────────────────────────────────────────────────

// ── STATE ─────────────────────────────────────────────────
let allTables   = [];
let openTabs    = [{ id: 'welcome', label: 'welcome', icon: '' }];
let activeTab   = 'welcome';
let palSelected = 0;
let statsCache  = null;

// ── LAYER COLOURS ──────────────────────────────────────────
const LC = {
  raw:   '#c0392b',
  stg:   '#8b5e3c',
  dim:   '#1a3a2a',
  fct:   '#1a3a2a',
  mrt:   '#6b7c6e',
  rpt:   '#4a3f6b',
  other: '#9a9288',
};

function layerColor(name) {
  for (const [k, v] of Object.entries(LC)) {
    if (name.startsWith(k + '_') || name === k) return v;
  }
  return LC.other;
}

function layerTag(name) {
  const l = name.split('_')[0];
  return `<span class="tag tag-${l}">${l}</span>`;
}

// ── TABS ───────────────────────────────────────────────────
function openTab(id, label, icon = '') {
  if (!openTabs.find(t => t.id === id)) {
    openTabs.push({ id, label, icon });
    renderTabs();
  }
  switchPanel(id);
  if (id === 'dead')      loadDeadPanel();
  if (id === 'overview')  loadOverview();
  if (id === 'colsearch') setTimeout(() => document.getElementById('colsearch-input').focus(), 100);
  if (id === 'lineage')   setTimeout(() => document.getElementById('lex-table').focus(), 100);
  if (id === 'broken')    loadBrokenPipeline();
  if (id === 'health')    loadHealth();
}

function openTableTab(name) {
  const id = 'table-' + name;
  if (!openTabs.find(t => t.id === id)) {
    openTabs.push({ id, label: name, icon: '⬡' });
    renderTabs();
  }
  switchPanel('table');
  loadTableInspector(name);
  document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('active'));
  const el = document.querySelector(`[data-table="${name}"]`);
  if (el) el.classList.add('active');
}

function closeTab(id, e) {
  e.stopPropagation();
  openTabs = openTabs.filter(t => t.id !== id);
  if (activeTab === id) {
    const last = openTabs[openTabs.length - 1];
    switchPanel(last ? last.id : 'welcome');
  }
  renderTabs();
}

function renderTabs() {
  const container = document.getElementById('editor-tabs');
  container.innerHTML = openTabs.map(t => `
    <div class="editor-tab ${activeTab === t.id ? 'active' : ''}" data-tab="${t.id}" onclick="switchPanel('${t.id}')">
      ${t.icon ? `<span>${t.icon}</span>` : ''}
      <span>${t.label}</span>
      ${t.id !== 'welcome' ? `<span class="close" onclick="closeTab('${t.id}', event)">×</span>` : ''}
    </div>
  `).join('');
}

function switchPanel(id) {
  activeTab = id;
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const panelMap = {
    welcome: 'welcome', overview: 'overview',
    dead: 'dead',       simulator: 'simulator',
    graph: 'graph',     colsearch: 'colsearch',
    lineage: 'lineage', broken: 'broken',
    health: 'health',
  };
  const panelId = panelMap[id] || 'table';
  const panel   = document.getElementById('panel-' + panelId);
  if (panel) panel.classList.add('active');
  renderTabs();
}

// ── SIDEBAR TREE ───────────────────────────────────────────
async function loadSidebar() {
  const tablesRes = await fetch('/api/tables').then(r => r.json()).catch(() => null);
  if (!tablesRes) return;

  allTables = tablesRes.tables;

  const layerOrder = ['raw', 'stg', 'dim', 'fct', 'mrt', 'rpt', 'other'];
  const grouped    = {};
  allTables.forEach(t => {
    const l = t.split('_')[0];
    if (!grouped[l]) grouped[l] = [];
    grouped[l].push(t);
  });

  const tree = document.getElementById('sidebar-tree');
  tree.innerHTML = layerOrder.filter(l => grouped[l]).map(l => `
    <div class="tree-group">
      <div class="tree-group-label">${l}_</div>
      ${grouped[l].map(t => `
        <div class="tree-item" data-table="${t}" onclick="openTableTab('${t}')">
          <div class="tree-dot" style="background:${LC[l] || LC.other}"></div>
          ${t}
        </div>
      `).join('')}
    </div>
  `).join('');
}

// ── STATS ──────────────────────────────────────────────────
async function fetchStats() {
  try {
    const s = await fetch('/api/stats').then(r => r.json());
    statsCache = s;
    return s;
  } catch (e) { return null; }
}

async function refreshStats() {
  const s = await fetchStats();
  if (!s) return;
  document.getElementById('hdr-nodes').textContent  = s.total_nodes + ' nodes';
  document.getElementById('hdr-edges').textContent  = s.total_edges + ' edges';
  document.getElementById('hdr-dead').textContent   = s.dead_count  + ' dead';
  document.getElementById('sb-nodes').textContent   = s.total_nodes;
  document.getElementById('sb-edges').textContent   = s.total_edges;
  document.getElementById('sb-dead').textContent    = s.dead_count;
  document.getElementById('sb-refresh').textContent = '↻ ' + new Date().toLocaleTimeString();
}

async function loadOverview() {
  const s = await fetchStats();
  if (!s) return;
  const derives = (s.edge_types.find(e => e.type === 'DERIVES_INTO') || {}).count || 0;
  document.getElementById('ov-nodes').textContent   = s.total_nodes;
  document.getElementById('ov-edges').textContent   = s.total_edges;
  document.getElementById('ov-dead').textContent    = s.dead_count;
  document.getElementById('ov-derives').textContent = derives;

  document.getElementById('ov-layers').innerHTML = s.layer_counts.map(l => `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:5px;padding:10px 16px;display:flex;align-items:center;gap:8px;">
      <div style="width:8px;height:8px;border-radius:50%;background:${LC[l.layer] || LC.other}"></div>
      <span style="color:var(--text2);font-family:var(--font-mono)">${l.layer}_</span>
      <strong style="color:var(--text);font-family:var(--font-mono)">${l.count}</strong>
    </div>
  `).join('');

  document.getElementById('ov-edges-table').innerHTML = s.edge_types.map(e =>
    `<tr><td>${e.type}</td><td style="color:var(--accent)">${e.count}</td></tr>`
  ).join('');
}

// ── TABLE INSPECTOR ────────────────────────────────────────
async function loadTableInspector(name) {
  const content = document.getElementById('table-inspector-content');
  content.innerHTML = '<div class="loading">Loading lineage for ' + name + '...</div>';
  termLog('$ lineage inspect ' + name);

  const res        = await fetch(`/api/table/lineage?table=${name}`).then(r => r.json());
  const upTables   = res.upstream   || [];
  const downTables = res.downstream || [];
  const columns    = res.columns    || [];

  content.innerHTML = `
    <div class="inspector-header">
      <h2>${name}</h2>
      ${layerTag(name)}
    </div>
    <div class="inspector-grid">
      <div class="info-block"><div class="ib-label">Upstream Tables</div><div class="ib-val">${upTables.length}</div></div>
      <div class="info-block"><div class="ib-label">Downstream Tables</div><div class="ib-val">${downTables.length}</div></div>
    </div>
    <div class="lineage-section">
      <h3>Columns</h3>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px">
        ${columns.map(c => `
          <span style="background:var(--bg2);border:1px solid var(--border2);border-radius:4px;padding:3px 10px;font-size:12px;color:var(--accent);cursor:pointer;font-family:var(--font-mono)"
            onclick="openPaletteWith('${name}.${c}')">${c}</span>
        `).join('')}
      </div>
    </div>
    <div class="lineage-section">
      <h3>Upstream Sources</h3>
      ${upTables.length ? upTables.map(t => `
        <div class="lineage-row" style="cursor:pointer" onclick="openTableTab('${t}')">
          <div class="tree-dot" style="background:${layerColor(t)}"></div>
          <div class="lr-col">${t}</div>
          <div class="arrow">→ ${name}</div>
        </div>
      `).join('') : '<div class="empty-state">No upstream tables (source table)</div>'}
    </div>
    <div class="lineage-section">
      <h3>Downstream Consumers</h3>
      ${downTables.length ? downTables.map(t => `
        <div class="lineage-row" style="cursor:pointer" onclick="openTableTab('${t}')">
          <div class="tree-dot" style="background:${layerColor(t)}"></div>
          <div class="lr-col">${name} →</div>
          <div class="arrow">${t}</div>
        </div>
      `).join('') : '<div class="empty-state">No downstream tables (terminal table)</div>'}
    </div>
  `;

  termLog(`  upstream: ${upTables.length} table(s)   downstream: ${downTables.length} table(s)   columns: ${columns.length}`, 'out');
}

// ── DEAD COLUMNS ───────────────────────────────────────────
async function loadDeadPanel() {
  const exclude = document.getElementById('dead-exclude').value;
  const content = document.getElementById('dead-content');
  content.innerHTML = '<div class="loading">Loading...</div>';
  termLog('$ lineage dead --exclude ' + (exclude || 'none'));

  const data = await fetch(`/api/dead?exclude=${encodeURIComponent(exclude)}`).then(r => r.json());
  if (!data.columns.length) {
    content.innerHTML = '<div class="empty-state">No dead columns found.</div>';
    return;
  }

  termLog(`  found ${data.total} dead column(s)`, 'out');

  const summaryHtml = Object.entries(data.summary).map(([layer, count]) => `
    <div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:var(--bg2);border:1px solid var(--border);border-radius:5px;">
      <div style="width:7px;height:7px;border-radius:50%;background:${LC[layer] || LC.other}"></div>
      <span style="color:var(--text2);font-family:var(--font-mono)">${layer}_</span>
      <strong style="color:var(--red);font-family:var(--font-mono)">${count}</strong>
    </div>
  `).join('');

  const rows = data.columns.map(r => {
    const last = r.source_files.length ? r.source_files[r.source_files.length - 1] : 'unknown';
    const rl   = r.reason === 'never_forwarded' ? 'var(--red)' : r.reason === 'renamed' ? 'var(--warm)' : 'var(--text2)';
    return `<tr>
      <td>${layerTag(r.table)} ${r.table}</td>
      <td style="color:var(--accent)">${r.column}</td>
      <td style="color:var(--text2)">depth ${r.depth}</td>
      <td style="color:${rl}">${r.reason}</td>
      <td style="font-size:11px"><span class="script-link" onclick="openScriptViewer('${last}')">${last}</span></td>
    </tr>`;
  }).join('');

  content.innerHTML = `
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px">${summaryHtml}</div>
    <table class="rt">
      <thead><tr><th>Table</th><th>Column</th><th>Depth</th><th>Reason</th><th>Last Script</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// ── SIMULATOR ──────────────────────────────────────────────
function toggleSimType() {
  const t = document.getElementById('sim-type').value;
  document.getElementById('sim-newname').style.display = t === 'rename' ? '' : 'none';
  document.getElementById('sim-oldtype').style.display = t === 'type'   ? '' : 'none';
  document.getElementById('sim-newtype').style.display = t === 'type'   ? '' : 'none';
  document.getElementById('sim-arrow').style.display   = t === 'type'   ? '' : 'none';
}

async function runSim() {
  const type   = document.getElementById('sim-type').value;
  const table  = document.getElementById('sim-table').value.trim();
  const col    = document.getElementById('sim-col').value.trim();
  const content = document.getElementById('sim-content');

  if (!table || !col) { content.innerHTML = '<div class="error-msg">Enter table and column.</div>'; return; }
  content.innerHTML = '<div class="loading">Running simulation...</div>';

  let url, body, cmdStr;
  if (type === 'rename') {
    const nn = document.getElementById('sim-newname').value.trim();
    url = '/api/simulate/rename'; body = { table, column: col, new_name: nn };
    cmdStr = `$ lineage simulate-rename ${table}.${col} ${nn}`;
  } else {
    const ot = document.getElementById('sim-oldtype').value.trim();
    const nt = document.getElementById('sim-newtype').value.trim();
    url = '/api/simulate/type'; body = { table, column: col, old_type: ot, new_type: nt };
    cmdStr = `$ lineage simulate-type ${table}.${col} ${ot} ${nt}`;
  }

  termLog(cmdStr);
  const data = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(r => r.json());

  if (!data.steps.length) {
    content.innerHTML = '<div class="empty-state">No downstream impact found.</div>';
    termLog('  no impact found', 'out');
    return;
  }

  termLog(`  ${data.total} column(s) affected across ${data.exec_order.length} script(s)`, 'out');

  const execHtml = data.exec_order.map((s, i) => `
    <div class="exec-step">
      <span class="step-num script-link" onclick="openScriptViewer('${s}')">${i + 1}. ${s}</span>
      ${i < data.exec_order.length - 1 ? '<span class="step-arr">→</span>' : ''}
    </div>
  `).join('');

  const riskHtml = data.risk_level
    ? `<div class="sb-item">Risk: <strong class="sev-${data.risk_level}">${data.risk_level}</strong> — ${data.risk_note}</div>`
    : '';

  const stepsHtml = data.steps.map(s => `
    <tr>
      <td style="color:var(--text2)">depth ${s.depth}</td>
      <td>${layerTag(s.affected_table)} <span style="color:var(--accent)">${s.affected_table}.${s.affected_column}</span>
        ${s.indirect_break ? '<span style="color:var(--warm);font-size:11px;margin-left:6px">⚠ indirect</span>' : ''}
      </td>
      <td class="sev-${s.severity}">${s.severity}</td>
      <td style="font-size:11px"><span class="script-link" onclick="openScriptViewer('${s.script}')">${s.script}</span></td>
      <td style="font-size:11px;color:var(--text2)">${s.rollback_action}</td>
    </tr>
  `).join('');

  content.innerHTML = `
    <div class="sim-header">
      <div class="sim-stat"><div class="ss-val">${data.total}</div><div class="ss-label">Affected Columns</div></div>
      <div class="sim-stat"><div class="ss-val">${data.exec_order.length}</div><div class="ss-label">Scripts to Update</div></div>
      ${riskHtml}
    </div>
    <div class="exec-order">
      <h3>Safe Execution Order</h3>
      <div class="exec-steps">${execHtml}</div>
    </div>
    <div class="section-title" style="margin-top:16px">Migration Steps</div>
    <table class="rt">
      <thead><tr><th>Depth</th><th>Column</th><th>Severity</th><th>Script</th><th>Rollback</th></tr></thead>
      <tbody>${stepsHtml}</tbody>
    </table>
  `;
}

// ── GRAPH ──────────────────────────────────────────────────
function loadGraph() {
  const mode  = document.getElementById('graph-mode').value;
  const focus = document.getElementById('graph-focus').value.trim();
  let url = `/api/visualizer?mode=${mode}`;
  if (focus) url += `&focus=${encodeURIComponent(focus)}`;
  termLog(`$ lineage visualize --mode ${mode}${focus ? ' --focus ' + focus : ''}`);
  document.getElementById('graph-frame').src = url;
}

// ── TERMINAL ───────────────────────────────────────────────
function termLog(msg, type = 'cmd') {
  const body = document.getElementById('terminal-body');
  const div  = document.createElement('div');
  div.className = 't-line';
  if (type === 'cmd') {
    const prompt = msg.startsWith('$') ? '<span class="t-prompt">$</span>' : '';
    div.innerHTML = prompt + `<span class="t-cmd">${msg.replace(/^\$ /, '')}</span>`;
  } else {
    div.innerHTML = `<span class="t-${type}">${msg}</span>`;
  }
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

// ── COMMAND PALETTE ────────────────────────────────────────
const COMMANDS = [
  { icon: '💀', main: 'Dead Columns',    sub: 'Find unused columns',               action: () => openTab('dead',      'Dead Columns',  '💀') },
  { icon: '⚡', main: 'Schema Simulator', sub: 'Simulate renames and type changes', action: () => openTab('simulator', 'Simulator',     '⚡') },
  { icon: '🕸', main: 'Graph View',       sub: 'Open interactive lineage graph',    action: () => openTab('graph',     'Graph View',    '🕸') },
  { icon: '📊', main: 'Overview',         sub: 'Graph statistics and layer breakdown', action: () => openTab('overview', 'Overview',    '📊') },
];

function openPalette() {
  document.getElementById('palette').classList.add('open');
  document.getElementById('pal-input').value = '';
  setTimeout(() => document.getElementById('pal-input').focus(), 50);
  updatePalette();
}

function closePalette(e) {
  if (e.target === document.getElementById('palette')) {
    document.getElementById('palette').classList.remove('open');
  }
}

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openPalette(); }
  if (e.key === 'Escape') document.getElementById('palette').classList.remove('open');
});

function updatePalette() {
  const q   = document.getElementById('pal-input').value.toLowerCase().trim();
  const sug = document.getElementById('pal-suggestions');
  palSelected = 0;

  const matchedTables = allTables.filter(t => !q || t.includes(q)).slice(0, 8);
  const matchedCmds   = COMMANDS.filter(c =>
    !q || c.main.toLowerCase().includes(q) || c.sub.toLowerCase().includes(q)
  );

  let html = '';
  if (matchedCmds.length) {
    html += `<div class="pal-group-label">Commands</div>`;
    html += matchedCmds.map((c, i) => `
      <div class="pal-item ${i === 0 ? 'selected' : ''}"
        onclick="${c.action.toString().replace(/\n/g, '').replace(/^.*?{(.*)}.*$/, '$1')}; document.getElementById('palette').classList.remove('open')">
        <span class="pi-icon">${c.icon}</span>
        <span class="pi-main">${c.main}</span>
        <span class="pi-sub">${c.sub}</span>
      </div>
    `).join('');
  }
  if (matchedTables.length) {
    html += `<div class="pal-group-label">Tables</div>`;
    html += matchedTables.map(t => {
      const l = t.split('_')[0];
      return `<div class="pal-item" onclick="openTableTab('${t}'); document.getElementById('palette').classList.remove('open')">
        <span class="pi-icon"><div style="width:8px;height:8px;border-radius:50%;background:${LC[l] || LC.other};display:inline-block"></div></span>
        <span class="pi-main">${t}</span>
        <span class="pi-tag">${l}_</span>
      </div>`;
    }).join('');
  }
  sug.innerHTML = html || `<div class="empty-state" style="padding:20px">No results</div>`;
}

function palKey(e) {
  const items = document.querySelectorAll('.pal-item');
  if (e.key === 'ArrowDown') palSelected = Math.min(palSelected + 1, items.length - 1);
  if (e.key === 'ArrowUp')   palSelected = Math.max(palSelected - 1, 0);
  if (e.key === 'Enter' && items[palSelected]) items[palSelected].click();
  items.forEach((el, i) => el.classList.toggle('selected', i === palSelected));
}

// ── COLUMN SEARCH ──────────────────────────────────────────
let colSearchTimer = null;

function debounceColSearch() {
  clearTimeout(colSearchTimer);
  colSearchTimer = setTimeout(runColSearch, 300);
}

async function runColSearch() {
  const q       = document.getElementById('colsearch-input').value.trim();
  const results = document.getElementById('colsearch-results');
  const summary = document.getElementById('colsearch-summary');

  if (!q) {
    results.innerHTML = '<div class="empty-state">Type a column name to search across all tables.</div>';
    summary.textContent = '';
    return;
  }

  results.innerHTML = '<div class="loading">Searching...</div>';
  termLog(`$ lineage search-column "${q}"`);

  const data = await fetch(`/api/search/column?q=${encodeURIComponent(q)}`).then(r => r.json());

  if (!data.results.length) {
    results.innerHTML = `<div class="empty-state">No columns found matching "${q}"</div>`;
    summary.textContent = '';
    termLog('  no results found', 'out');
    return;
  }

  const uniqueTables = new Set(data.results.map(r => r.table_name)).size;
  termLog(`  found ${data.total} match(es) across ${uniqueTables} table(s)`, 'out');
  summary.textContent = `${data.total} column(s) found across ${uniqueTables} table(s)`;

  const grouped = {};
  data.results.forEach(r => {
    if (!grouped[r.column_name]) grouped[r.column_name] = [];
    grouped[r.column_name].push(r);
  });

  results.innerHTML = Object.entries(grouped).map(([colName, rows]) => `
    <div style="margin-bottom:20px">
      <div style="font-size:13px;color:var(--accent);font-weight:600;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border);font-family:var(--font-mono)">
        ${colName} <span style="color:var(--text2);font-weight:400;font-size:11px">(${rows.length} table${rows.length > 1 ? 's' : ''})</span>
      </div>
      <table class="rt">
        <thead>
          <tr><th>Table</th><th>Layer</th><th>Upstream</th><th>Downstream</th><th>Actions</th></tr>
        </thead>
        <tbody>
          ${rows.map(r => {
            const upCount   = r.upstream_count   || 0;
            const downCount = r.downstream_count || 0;
            return `<tr>
              <td style="cursor:pointer;color:var(--accent)" onclick="openTableTab('${r.table_name}')">${r.table_name}</td>
              <td>${layerTag(r.table_name)}</td>
              <td style="color:${upCount   > 0 ? 'var(--green)' : 'var(--text3)'}">↑ ${upCount}</td>
              <td style="color:${downCount > 0 ? 'var(--accent)' : 'var(--text3)'}">↓ ${downCount}</td>
              <td style="display:flex;gap:6px">
                <button class="btn-ghost" style="padding:3px 8px;font-size:11px"
                  onclick="runImpactFromSearch('${r.table_name}','${r.column_name}')">impact</button>
                <button class="btn-ghost" style="padding:3px 8px;font-size:11px"
                  onclick="openTableTab('${r.table_name}')">inspect</button>
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  `).join('');
}

function runImpactFromSearch(table, column) {
  openTab('simulator', 'Simulator', '⚡');
  document.getElementById('sim-table').value = table;
  document.getElementById('sim-col').value   = column;
  document.getElementById('sim-type').value  = 'rename';
  toggleSimType();
  termLog(`$ opening simulator for ${table}.${column}`);
}

// ── LINEAGE EXPLORER ───────────────────────────────────────
async function runLex() {
  const table  = document.getElementById('lex-table').value.trim();
  const column = document.getElementById('lex-column').value.trim();
  const mode   = document.getElementById('lex-mode').value;
  const box    = document.getElementById('lex-results');

  if (!table || !column) {
    box.innerHTML = '<div class="error-msg">Enter both table and column.</div>';
    return;
  }

  box.innerHTML = '<div class="loading">Running...</div>';
  termLog(`$ lineage ${mode} ${table}.${column}`);

  const data = await fetch(`/api/lineage/${mode}?table=${table}&column=${column}`).then(r => r.json());
  const rows = data.rows || [];

  if (!rows.length) {
    box.innerHTML = `<div class="empty-state">No ${mode} found for ${table}.${column}</div>`;
    termLog('  no results', 'out');
    return;
  }

  termLog(`  ${rows.length} result(s) found`, 'out');

  const tableKey = mode === 'upstream'   ? 'source_table'   : mode === 'downstream' ? 'target_table'  : 'affected_table';
  const colKey   = mode === 'upstream'   ? 'source_column'  : mode === 'downstream' ? 'target_column' : 'affected_column';
  const filesKey = mode === 'impact'     ? 'via_scripts'    : 'sql_files';

  const seen    = {};
  const deduped = [];
  rows.forEach(r => {
    const key = `${r[tableKey]}.${r[colKey]}`;
    if (!seen[key]) { seen[key] = true; deduped.push(r); }
  });

  const source   = `${table}.${column}`;
  const pathHtml = buildPathViz(source, deduped, tableKey, colKey, mode);

  const tableHtml = `
    <table class="rt">
      <thead>
        <tr>
          <th>Depth</th>
          <th>${mode === 'upstream' ? 'Source' : 'Target'} Column</th>
          <th>Layer</th>
          <th>Via Scripts</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${deduped.map(r => {
          const tname = r[tableKey];
          const cname = r[colKey];
          const files = (r[filesKey] || []).join(' → ');
          return `<tr>
            <td style="color:var(--text2)">depth ${r.depth}</td>
            <td>
              <span style="color:var(--accent);cursor:pointer" onclick="openTableTab('${tname}')">${tname}</span>
              <span style="color:var(--text3)">.</span>
              <span style="color:var(--text)">${cname}</span>
            </td>
            <td>${layerTag(tname)}</td>
            <td style="font-size:11px">${(r[filesKey] || []).map(f =>
  `<span class="script-link" onclick="openScriptViewer('${f}')">${f}</span>`
).join(' &#8594; ')}</td>
            <td>
              <button class="btn-ghost" style="padding:3px 8px;font-size:11px"
                onclick="document.getElementById('lex-table').value='${tname}';
                         document.getElementById('lex-column').value='${cname}';
                         runLex()">explore →</button>
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  `;

  box.innerHTML = `
    <div style="margin-bottom:6px;color:var(--text2);font-size:12px;font-family:var(--font-mono)">
      ${deduped.length} unique column(s) ${mode === 'upstream' ? 'feed into' : 'are fed by'}
      <span style="color:var(--accent)">${source}</span>
    </div>
    ${pathHtml}
    <div style="margin-top:20px">${tableHtml}</div>
  `;
}

function buildPathViz(source, rows, tableKey, colKey, mode) {
  if (!rows.length) return '';

  const byDepth = {};
  rows.forEach(r => {
    const d = r.depth;
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(r);
  });

  const depths = mode === 'upstream'
    ? Object.keys(byDepth).map(Number).sort((a, b) => b - a)
    : Object.keys(byDepth).map(Number).sort((a, b) => a - b);

  const sourceLayer = source.split('.')[0].split('_')[0];

  let html = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:7px;padding:16px 20px;overflow-x:auto">
      <div style="font-size:10px;color:var(--text3);margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;font-family:var(--font-head)">
        ${mode === 'upstream' ? 'Sources →' : '→ Consumers'} Path
      </div>
      <div style="display:flex;align-items:flex-start;gap:0;min-width:max-content">
  `;

  if (mode !== 'upstream') {
    html += `
      <div style="display:flex;flex-direction:column;align-items:center;gap:4px;margin-right:8px">
        <div style="background:var(--bg2);border:2px solid ${LC[sourceLayer] || LC.other};border-radius:5px;padding:6px 12px;font-size:12px;color:var(--accent);white-space:nowrap;font-family:var(--font-mono)">${source}</div>
        <div style="font-size:10px;color:var(--text3);font-family:var(--font-head)">source</div>
      </div>
      <div style="display:flex;align-items:center;padding-top:10px;margin-right:8px;color:var(--text3)">→</div>
    `;
  }

  depths.forEach((depth, di) => {
    const nodes = byDepth[depth];
    html += `<div style="display:flex;flex-direction:column;gap:6px;margin-right:8px">`;
    nodes.forEach(r => {
      const tname = r[tableKey];
      const cname = r[colKey];
      const l     = tname.split('_')[0];
      html += `
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px">
          <div style="background:var(--bg2);border:1px solid ${LC[l] || LC.other};border-radius:5px;padding:5px 10px;font-size:11px;white-space:nowrap;cursor:pointer;font-family:var(--font-mono)"
            onclick="document.getElementById('lex-table').value='${tname}';document.getElementById('lex-column').value='${cname}';runLex()">
            <span style="color:${LC[l] || LC.other}">${tname}</span><span style="color:var(--text3)">.</span><span style="color:var(--text)">${cname}</span>
          </div>
          <div style="font-size:10px;color:var(--text3);font-family:var(--font-head)">depth ${depth}</div>
        </div>
      `;
    });
    html += `</div>`;
    if (di < depths.length - 1) {
      html += `<div style="display:flex;align-items:center;padding-top:10px;margin-right:8px;color:var(--text3)">→</div>`;
    }
  });

  if (mode === 'upstream') {
    html += `
      <div style="display:flex;align-items:center;padding-top:10px;margin-right:8px;color:var(--text3)">→</div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
        <div style="background:var(--bg2);border:2px solid ${LC[sourceLayer] || LC.other};border-radius:5px;padding:6px 12px;font-size:12px;color:var(--accent);white-space:nowrap;font-family:var(--font-mono)">${source}</div>
        <div style="font-size:10px;color:var(--text3);font-family:var(--font-head)">target</div>
      </div>
    `;
  }

  html += `</div></div>`;
  return html;
}

// ── BROKEN PIPELINE ────────────────────────────────────────
async function loadBrokenPipeline() {
  const content = document.getElementById('broken-content');
  content.innerHTML = '<div class="loading">Scanning pipeline...</div>';
  termLog('$ lineage broken-pipeline');

  const data = await fetch('/api/broken-pipeline').then(r => r.json());
  termLog(`  ${data.total_phantoms} phantom source(s), ${data.total_isolated} isolated table(s)`, 'out');

  const summaryHtml = `
    <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap">
      <div class="info-block" style="flex:1;min-width:160px">
        <div class="ib-label">Phantom Sources</div>
        <div class="ib-val" style="color:${data.total_phantoms > 0 ? 'var(--red)' : 'var(--green)'}">${data.total_phantoms}</div>
      </div>
      <div class="info-block" style="flex:1;min-width:160px">
        <div class="ib-label">Isolated Tables</div>
        <div class="ib-val" style="color:${data.total_isolated > 0 ? 'var(--warm)' : 'var(--green)'}">${data.total_isolated}</div>
      </div>
      <div class="info-block" style="flex:1;min-width:160px">
        <div class="ib-label">Pipeline Status</div>
        <div class="ib-val" style="font-size:18px;color:${data.total_phantoms > 0 ? 'var(--red)' : 'var(--green)'}">
          ${data.total_phantoms > 0 ? '⚠ Issues Found' : '✓ Healthy'}
        </div>
      </div>
    </div>
  `;

  let phantomHtml = '';
  if (data.phantom_sources.length) {
    const rows = data.phantom_sources.map(r => {
      const scripts = r.in_scripts.join(', ');
      const refs    = r.referenced_by.map(t =>
        `<span style="color:var(--accent);cursor:pointer" onclick="openTableTab('${t}')">${t}</span>`
      ).join(', ');
      return `<tr>
        <td style="color:var(--red)">${r.missing_table}</td>
        <td>${refs}</td>
        <td style="color:var(--text2);font-size:11px">${scripts}</td>
        <td><button class="btn-ghost" style="padding:3px 8px;font-size:11px" onclick="openTableTab('${r.missing_table}')">inspect</button></td>
      </tr>`;
    }).join('');
    phantomHtml = `
      <div style="margin-bottom:20px">
        <div class="section-title" style="color:var(--red);margin-bottom:10px">⚠ Phantom Sources — referenced but never created</div>
        <p style="color:var(--text2);font-size:12px;margin-bottom:12px;font-family:var(--font-mono)">
          These tables appear as inputs in SQL scripts but have no corresponding output script in the system.
        </p>
        <table class="rt">
          <thead><tr><th>Missing Table</th><th>Referenced By</th><th>In Scripts</th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } else {
    phantomHtml = `
      <div style="margin-bottom:20px">
        <div class="section-title" style="color:var(--green);margin-bottom:10px">✓ No phantom sources found</div>
        <p style="color:var(--text2);font-size:12px;font-family:var(--font-mono)">Every input table has a corresponding output script.</p>
      </div>
    `;
  }

  let isolatedHtml = '';
  if (data.isolated_tables.length) {
    isolatedHtml = `
      <div>
        <div class="section-title" style="color:var(--warm);margin-bottom:10px">⚡ Isolated Tables — no upstream or downstream connections</div>
        <p style="color:var(--text2);font-size:12px;margin-bottom:12px;font-family:var(--font-mono)">
          These tables exist in the graph but are not connected to any other table via FEEDS edges.
        </p>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${data.isolated_tables.map(t => `
            <div style="background:var(--bg2);border:1px solid var(--warm);border-radius:5px;padding:6px 12px;font-size:12px;cursor:pointer;color:var(--warm);font-family:var(--font-mono)"
              onclick="openTableTab('${t}')">${t}</div>
          `).join('')}
        </div>
      </div>
    `;
  } else {
    isolatedHtml = `
      <div>
        <div class="section-title" style="color:var(--green);margin-bottom:10px">✓ No isolated tables found</div>
        <p style="color:var(--text2);font-size:12px;font-family:var(--font-mono)">Every table is connected to the pipeline.</p>
      </div>
    `;
  }

  content.innerHTML = summaryHtml + phantomHtml + isolatedHtml;
}

// ── HEALTH SCORE ───────────────────────────────────────────
async function loadHealth() {
  const content = document.getElementById('health-content');
  content.innerHTML = '<div class="loading">Calculating health scores...</div>';
  termLog('$ lineage health-score');

  const data = await fetch('/api/health').then(r => r.json());
  termLog(`  average score: ${data.average_score}/100 across ${data.total_tables} tables`, 'out');

  const avgColor = data.average_score >= 90 ? 'var(--green)'
                 : data.average_score >= 75 ? 'var(--accent)'
                 : data.average_score >= 60 ? 'var(--warm)'
                 : 'var(--red)';

  const gradeColors = { A: 'var(--green)', B: 'var(--accent)', C: 'var(--warm)', D: 'var(--orange)', F: 'var(--red)' };

  const summaryHtml = `
    <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;align-items:stretch">
      <div class="info-block" style="text-align:center;min-width:140px">
        <div class="ib-label">Average Score</div>
        <div style="font-size:48px;font-weight:700;color:${avgColor};line-height:1.2;font-family:var(--font-mono)">${data.average_score}</div>
        <div style="color:var(--text2);font-size:12px;font-family:var(--font-head)">out of 100</div>
      </div>
      <div style="flex:1;display:grid;grid-template-columns:repeat(5,1fr);gap:8px;min-width:300px">
        ${Object.entries(data.grade_counts).map(([grade, count]) => `
          <div class="info-block" style="text-align:center">
            <div style="font-size:22px;font-weight:700;color:${gradeColors[grade]};font-family:var(--font-mono)">${grade}</div>
            <div style="font-size:18px;color:var(--text);font-family:var(--font-mono)">${count}</div>
            <div style="font-size:10px;color:var(--text2);font-family:var(--font-head)">table(s)</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  const rows = data.scores.map(s => {
    const scoreColor = s.score >= 90 ? 'var(--green)'
                     : s.score >= 75 ? 'var(--accent)'
                     : s.score >= 60 ? 'var(--warm)'
                     : s.score >= 40 ? 'var(--orange)'
                     : 'var(--red)';
    return `<tr>
      <td style="cursor:pointer;color:var(--accent)" onclick="openTableTab('${s.table}')">${s.table}</td>
      <td>${layerTag(s.table)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div style="width:80px;height:5px;background:var(--border2);border-radius:3px;overflow:hidden">
            <div style="width:${s.score}%;height:100%;background:${scoreColor};border-radius:3px"></div>
          </div>
          <span style="color:${scoreColor};font-weight:700">${s.score}</span>
          <span style="color:${gradeColors[s.grade]};font-size:11px;font-weight:700">${s.grade}</span>
        </div>
      </td>
      <td style="color:${s.dead_cols > 0 ? 'var(--red)' : 'var(--green)'}">
        ${s.dead_cols} / ${s.total_cols}
        <span style="color:var(--text3);font-size:11px">(${s.dead_ratio}%)</span>
      </td>
      <td style="color:var(--text2)">↑ ${s.upstream} ↓ ${s.downstream}</td>
      <td>
        <button class="btn-ghost" style="padding:3px 8px;font-size:11px"
          onclick="openTab('dead','Dead Columns','💀'); document.getElementById('dead-exclude').value='rpt_,mrt_'; loadDeadPanel()">
          dead cols
        </button>
      </td>
    </tr>`;
  }).join('');

  content.innerHTML = `
    ${summaryHtml}
    <div class="section-title" style="margin-bottom:10px">Table Scores (sorted by score ascending)</div>
    <table class="rt">
      <thead><tr><th>Table</th><th>Layer</th><th>Score</th><th>Dead Columns</th><th>Connections</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// ── BOOT ───────────────────────────────────────────────────
function openPaletteWith(val) {
  openPalette();
  document.getElementById('pal-input').value = val;
  updatePalette();
}

async function boot() {
  await refreshStats();
  await loadSidebar();
  setInterval(refreshStats, 5000);
  termLog(`  graph loaded — ${statsCache?.total_nodes || '?'} nodes, ${statsCache?.total_edges || '?'} edges`, 'out');
}
// ── SCRIPT VIEWER ─────────────────────────────────────────────────────────────
async function openScriptViewer(filename) {
  document.getElementById('scriptOverlay').classList.add('open');
  document.getElementById('scriptFilename').textContent = filename;
  document.getElementById('scriptContent').innerHTML = 'Loading...';

  termLog(`$ cat data/sql_scripts/${filename}`);

  try {
    const data = await fetch(`/api/script?filename=${encodeURIComponent(filename)}`).then(r => r.json());
    if (data.error) {
      document.getElementById('scriptContent').innerHTML =
        `<span style="color:var(--red)">${data.error}</span>`;
      termLog(`  ${data.error}`, 'err');
      return;
    }
    document.getElementById('scriptContent').innerHTML = highlightSql(data.content);
    termLog(`  loaded ${data.content.split('\\n').length} line(s)`, 'out');
  } catch (e) {
    document.getElementById('scriptContent').innerHTML =
      `<span style="color:var(--red)">Failed to load script</span>`;
  }
}

function closeScriptViewer(e) {
  if (e.target === document.getElementById('scriptOverlay')) {
    document.getElementById('scriptOverlay').classList.remove('open');
  }
}

function highlightSql(code) {
  const KEYWORDS = [
    'SELECT','FROM','WHERE','JOIN','LEFT','RIGHT','INNER','OUTER','ON','AS',
    'GROUP BY','ORDER BY','WITH','CREATE','TABLE','INSERT','INTO','VALUES',
    'AND','OR','NOT','NULL','IS','IN','CASE','WHEN','THEN','ELSE','END',
    'UNION','ALL','DISTINCT','HAVING','LIMIT','CROSS','COALESCE'
  ];
  const FUNCTIONS = ['COUNT','SUM','AVG','MAX','MIN','DATE','EXTRACT','LOWER','UPPER','TRIM','CAST'];

  let escaped = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // comments
  escaped = escaped.replace(/(--.*$)/gm, '<span class="sql-com">$1</span>');

  // strings
  escaped = escaped.replace(/('[^']*')/g, '<span class="sql-str">$1</span>');

  // keywords (word boundary, case-insensitive)
  KEYWORDS.forEach(kw => {
    const re = new RegExp(`\\b(${kw.replace(' ', '\\s+')})\\b`, 'gi');
    escaped = escaped.replace(re, '<span class="sql-kw">$1</span>');
  });

  // functions
  FUNCTIONS.forEach(fn => {
    const re = new RegExp(`\\b(${fn})\\b(?=\\s*\\()`, 'gi');
    escaped = escaped.replace(re, '<span class="sql-fn">$1</span>');
  });

  return escaped;
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.getElementById('scriptOverlay').classList.remove('open');
});

boot();