/* global window, document, fetch */
const state = {
  power: [],
  bracket: [],
  sort: {
    bracket: { key: 'round_order', dir: 'asc', type: 'number' },
    power: { key: 'elo', dir: 'desc', type: 'number' },
  },
};

function buildTeamIndex(powerRows) {
  const map = new Map();
  powerRows.forEach((r) => {
    if (!r || r.team == null) return;
    map.set(String(r.team), r);
  });
  return map;
}

function $(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const el = $(id);
  if (!el) return;
  el.textContent = value;
}

function setHref(id, value) {
  const el = $(id);
  if (!el) return;
  el.href = value;
}

function formatRunMeta(meta) {
  const parts = [];
  if (meta.run_id) parts.push(meta.run_id);
  if (meta.method) parts.push(meta.method);
  if (meta.built_at) parts.push(`built ${meta.built_at}`);
  if (meta.source_dir) parts.push(`source ${meta.source_dir}`);
  return parts.length ? parts.join(' • ') : '—';
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toFixed(digits);
}

function formatProb(value) {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return `${(num * 100).toFixed(1)}%`;
}

function parseRegionCode(slot) {
  const s = String(slot ?? '');
  if (s.startsWith('E_')) return 'E';
  if (s.startsWith('W_')) return 'W';
  if (s.startsWith('S_')) return 'S';
  if (s.startsWith('M_')) return 'M';
  return null;
}

function parseRoundNumber(slot) {
  const m = String(slot ?? '').match(/_R(\d+)_/);
  if (!m) return null;
  return Number(m[1]);
}

function parseGameNumber(slot) {
  const m = String(slot ?? '').match(/_G(\d+)$/);
  if (!m) return null;
  return Number(m[1]);
}

function gridRowFor(roundNumber, gameNumber) {
  // 16-row grid (plus a header row in CSS), placing cards to resemble a bracket.
  if (roundNumber === 1) return (gameNumber - 1) * 2 + 1; // 1..15 odd
  if (roundNumber === 2) return (gameNumber - 1) * 4 + 2; // 2,6,10,14
  if (roundNumber === 3) return (gameNumber - 1) * 8 + 4; // 4,12
  if (roundNumber === 4) return 8;
  return 1;
}

function teamDisplay(teamIndex, teamName) {
  const name = String(teamName ?? '—');
  const info = teamIndex.get(name);
  const seed = info && info.seed != null ? Number(info.seed) : null;
  return { name, seed };
}

function renderGameCard(teamIndex, game, labelOverride) {
  const team1 = teamDisplay(teamIndex, game.team1);
  const team2 = teamDisplay(teamIndex, game.team2);
  const winner = String(game.winner ?? '');
  const winnerProb = formatProb(game.winner_prob);
  const label = labelOverride ?? String(game.slot ?? '—');

  const div = document.createElement('div');
  div.className = 'brGame';
  const t1Winner = team1.name === winner;
  const t2Winner = team2.name === winner;
  div.innerHTML = `
    <div class="brGame__meta">
      <span class="tag">${label}</span>
      <span class="brTeam__badge">${winnerProb}</span>
    </div>
    <div class="brTeam ${t1Winner ? 'brTeam--winner' : ''}">
      <div class="brTeam__name">
        <span class="seed">${team1.seed != null ? `(${team1.seed})` : ''}</span>
        <span class="teamName" title="${team1.name}">${team1.name}</span>
      </div>
      <span class="brTeam__badge">${formatProb(game.team1_win_prob)}</span>
    </div>
    <div class="brTeam ${t2Winner ? 'brTeam--winner' : ''}">
      <div class="brTeam__name">
        <span class="seed">${team2.seed != null ? `(${team2.seed})` : ''}</span>
        <span class="teamName" title="${team2.name}">${team2.name}</span>
      </div>
      <span class="brTeam__badge">${formatProb(1 - Number(game.team1_win_prob))}</span>
    </div>
  `;
  return div;
}

function sortRows(rows, sortCfg) {
  const { key, dir, type } = sortCfg;
  const m = dir === 'asc' ? 1 : -1;
  const copy = rows.slice();
  copy.sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (type === 'number') {
      const an = Number(av);
      const bn = Number(bv);
      if (Number.isNaN(an) && Number.isNaN(bn)) return 0;
      if (Number.isNaN(an)) return 1;
      if (Number.isNaN(bn)) return -1;
      if (an === bn) return 0;
      return (an < bn ? -1 : 1) * m;
    }
    const as = String(av ?? '').toLowerCase();
    const bs = String(bv ?? '').toLowerCase();
    if (as === bs) return 0;
    return (as < bs ? -1 : 1) * m;
  });
  return copy;
}

function setSort(tableName, th) {
  const key = th.getAttribute('data-key');
  const type = th.getAttribute('data-type') || 'string';
  const sortCfg = state.sort[tableName];
  if (sortCfg.key === key) {
    sortCfg.dir = sortCfg.dir === 'asc' ? 'desc' : 'asc';
  } else {
    sortCfg.key = key;
    sortCfg.type = type;
    sortCfg.dir = type === 'number' ? 'desc' : 'asc';
  }
}

function setHeaderIndicators(tableEl, sortCfg) {
  const ths = tableEl.querySelectorAll('thead th');
  ths.forEach((th) => {
    const key = th.getAttribute('data-key');
    const arrow = key === sortCfg.key ? (sortCfg.dir === 'asc' ? ' ▲' : ' ▼') : '';
    th.textContent = th.textContent.replace(/ [▲▼]$/, '') + arrow;
  });
}

function buildRoundFilter(rounds) {
  const sel = $('roundFilter');
  sel.innerHTML = '';
  const all = document.createElement('option');
  all.value = '';
  all.textContent = 'All rounds';
  sel.appendChild(all);
  rounds.forEach((r) => {
    const opt = document.createElement('option');
    opt.value = r;
    opt.textContent = r;
    sel.appendChild(opt);
  });
}

function renderBracket() {
  const table = $('bracketTable');
  const tbody = table.querySelector('tbody');
  const q = $('bracketSearch').value.trim().toLowerCase();
  const round = $('roundFilter').value;

  let rows = state.bracket;
  if (round) rows = rows.filter((r) => String(r.round_name) === round);
  if (q) {
    rows = rows.filter((r) =>
      [r.slot, r.round_name, r.team1, r.team2, r.winner].some((x) =>
        String(x ?? '').toLowerCase().includes(q),
      ),
    );
  }
  rows = sortRows(rows, state.sort.bracket);
  setHeaderIndicators(table, state.sort.bracket);

  const frag = document.createDocumentFragment();
  rows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="prob">${formatNumber(r.round_order, 0)}</td>
      <td>${r.round_name ?? '—'}</td>
      <td><span class="tag">${r.slot ?? '—'}</span></td>
      <td>${r.team1 ?? '—'}</td>
      <td>${r.team2 ?? '—'}</td>
      <td class="prob">${formatProb(r.team1_win_prob)}</td>
      <td><span class="winner"><span class="dot"></span>${r.winner ?? '—'}</span></td>
      <td class="prob">${formatProb(r.winner_prob)}</td>
    `;
    frag.appendChild(tr);
  });
  tbody.innerHTML = '';
  tbody.appendChild(frag);
}

function renderPower() {
  const table = $('powerTable');
  const tbody = table.querySelector('tbody');
  const q = $('powerSearch').value.trim().toLowerCase();

  let rows = state.power;
  if (q) rows = rows.filter((r) => String(r.team ?? '').toLowerCase().includes(q));
  rows = sortRows(rows, state.sort.power);
  setHeaderIndicators(table, state.sort.power);

  const frag = document.createDocumentFragment();
  rows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.team ?? '—'}</td>
      <td>${r.region ?? '—'}</td>
      <td class="prob">${formatNumber(r.seed, 0)}</td>
      <td class="prob">${formatNumber(r.wins, 0)}</td>
      <td class="prob">${formatNumber(r.losses, 0)}</td>
      <td class="prob">${formatNumber(r.net_rank, 0)}</td>
      <td class="prob">${formatNumber(r.power_score, 2)}</td>
      <td class="prob">${formatNumber(r.elo, 1)}</td>
    `;
    frag.appendChild(tr);
  });
  tbody.innerHTML = '';
  tbody.appendChild(frag);
}

function computeChampionHint(championName) {
  if (!championName) return '—';
  const top = state.power.find((r) => r.team === championName);
  if (!top) return 'Not found in power table';
  const seed = top.seed != null ? `Seed ${top.seed}` : 'Seed —';
  const region = top.region ?? 'Region —';
  const elo = top.elo != null ? `Elo ${formatNumber(top.elo, 1)}` : 'Elo —';
  return `${region} • ${seed} • ${elo}`;
}

function renderBracketViz(meta) {
  const teamIndex = buildTeamIndex(state.power);

  // First Four
  const firstFourHost = $('firstFour');
  const firstFour = state.bracket.filter((g) => Number(g.round_order) === 0);
  firstFourHost.innerHTML = '';
  const ffTitle = document.createElement('div');
  ffTitle.className = 'bracketSection__title';
  ffTitle.textContent = 'First Four';
  firstFourHost.appendChild(ffTitle);
  const ffGrid = document.createElement('div');
  ffGrid.className = 'firstFourGrid';
  firstFour
    .slice()
    .sort((a, b) => String(a.slot).localeCompare(String(b.slot)))
    .forEach((g) => ffGrid.appendChild(renderGameCard(teamIndex, g)));
  firstFourHost.appendChild(ffGrid);

  // Regional brackets
  const regionHost = $('regionGrid');
  regionHost.innerHTML = '';
  const regions = [
    { code: 'E', name: 'East' },
    { code: 'W', name: 'West' },
    { code: 'S', name: 'South' },
    { code: 'M', name: 'Midwest' },
  ];

  const roundLabels = [
    { n: 1, label: 'Round of 64' },
    { n: 2, label: 'Round of 32' },
    { n: 3, label: 'Sweet 16' },
    { n: 4, label: 'Elite 8' },
  ];

  regions.forEach((reg) => {
    const card = document.createElement('div');
    card.className = 'regionCard';
    const head = document.createElement('div');
    head.className = 'regionCard__head';
    head.innerHTML = `<h3 class="regionCard__title">${reg.name}</h3><div class="regionCard__hint">Predicted winners highlighted</div>`;
    card.appendChild(head);

    const scroll = document.createElement('div');
    scroll.className = 'regionScroll';

    const grid = document.createElement('div');
    grid.className = 'bracketGrid';
    roundLabels.forEach((r, idx) => {
      const h = document.createElement('div');
      h.className = 'brColHeader';
      h.style.gridColumn = String(idx + 1);
      h.textContent = r.label;
      grid.appendChild(h);
    });

    const games = state.bracket.filter((g) => parseRegionCode(g.slot) === reg.code);
    const byRound = new Map();
    games.forEach((g) => {
      const rn = parseRoundNumber(g.slot);
      if (!rn) return;
      if (!byRound.has(rn)) byRound.set(rn, []);
      byRound.get(rn).push(g);
    });

    [1, 2, 3, 4].forEach((rn) => {
      const list = (byRound.get(rn) || []).slice();
      list.sort((a, b) => {
        const ga = parseGameNumber(a.slot) ?? 0;
        const gb = parseGameNumber(b.slot) ?? 0;
        return ga - gb;
      });
      list.forEach((g, idx) => {
        const gn = parseGameNumber(g.slot) ?? (idx + 1);
        const row = gridRowFor(rn, gn) + 1; // +1 for header row
        const col = rn;
        const cardEl = renderGameCard(teamIndex, g, `R${rn} G${gn}`);
        cardEl.style.gridColumn = String(col);
        cardEl.style.gridRow = String(row);
        grid.appendChild(cardEl);
      });
    });

    scroll.appendChild(grid);
    card.appendChild(scroll);
    regionHost.appendChild(card);
  });

  // Final Four + Champion
  const finalHost = $('finalFour');
  finalHost.innerHTML = '';
  const fTitle = document.createElement('div');
  fTitle.className = 'bracketSection__title';
  fTitle.textContent = 'Final Four & Champion';
  finalHost.appendChild(fTitle);

  const fGrid = document.createElement('div');
  fGrid.className = 'finalFourGrid';
  const g1 = state.bracket.find((g) => String(g.slot) === 'FF_G1');
  const g2 = state.bracket.find((g) => String(g.slot) === 'FF_G2');
  const champSlot = state.bracket.find((g) => String(g.slot) === 'CHAMPION');

  if (g1) fGrid.appendChild(renderGameCard(teamIndex, g1, 'Final Four 1'));
  if (g2) fGrid.appendChild(renderGameCard(teamIndex, g2, 'Final Four 2'));

  const champCard = document.createElement('div');
  champCard.className = 'brGame championCard';
  champCard.innerHTML = `
    <div class="brGame__meta">
      <span class="tag">Champion</span>
      <span class="brTeam__badge champProb">—</span>
    </div>
    <div class="brTeam brTeam--winner">
      <div class="brTeam__name">
        <span class="seed"></span>
        <span class="teamName" title="${meta.champion || '—'}">${meta.champion || '—'}</span>
      </div>
      <span class="brTeam__badge">Winner</span>
    </div>
  `;
  // If we have the CHAMPION slot, show its probability.
  if (champSlot && champSlot.winner_prob != null) {
    champCard.querySelector('.champProb').textContent = formatProb(champSlot.winner_prob);
  }
  fGrid.appendChild(champCard);
  finalHost.appendChild(fGrid);
}

async function loadJson(path) {
  const res = await fetch(path, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}

async function loadRunsManifest() {
  const candidates = ['./runs.json', '../runs.json'];
  for (const path of candidates) {
    try {
      return await loadJson(path);
    } catch (e) {
      // ignore
    }
  }
  return null;
}

function currentPageFile() {
  const url = new URL(window.location.href);
  const path = url.pathname || '';
  const file = path.split('/').pop() || '';
  if (file.endsWith('.html')) return file;
  return 'index.html';
}

function linkToRun(runId) {
  const url = new URL(window.location.href);
  const parts = (url.pathname || '').split('/').filter(Boolean);
  const inRunDir = parts.some((p) => String(p).startsWith('run_'));
  const base = inRunDir ? '..' : '.';
  return `${base}/${runId}/${currentPageFile()}`;
}

async function setupRunSelector(meta) {
  const sel = $('runSelect');
  if (!sel) return;

  const manifest = await loadRunsManifest();
  const runs = manifest && Array.isArray(manifest.runs) ? manifest.runs : [];

  sel.innerHTML = '';
  if (!runs.length) {
    const opt = document.createElement('option');
    opt.value = meta.run_id || '';
    opt.textContent = meta.run_id || 'run';
    sel.appendChild(opt);
    sel.disabled = true;
    return;
  }

  runs.forEach((r) => {
    const id = r && typeof r === 'object' ? (r.id || r.path) : String(r);
    if (!id) return;
    const label = r && typeof r === 'object' ? (r.label || r.method_short || '') : '';
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = label ? `${id} • ${label}` : id;
    sel.appendChild(opt);
  });

  const current = meta && meta.run_id ? String(meta.run_id) : '';
  if (current) sel.value = current;

  sel.addEventListener('change', () => {
    const target = linkToRun(sel.value);
    window.location.href = target;
  });
}

async function boot() {
  const meta = await loadJson('./data/meta.json');
  state.power = await loadJson('./data/power_scale.json');
  state.bracket = await loadJson('./data/bracket_predictions.json');

  await setupRunSelector(meta);

  setText('runMeta', formatRunMeta(meta));
  setText('teamsCount', String(state.power.length));
  setText('gamesCount', String(state.bracket.length));
  setText('championValue', meta.champion || '—');
  setText('championHint', computeChampionHint(meta.champion));

  if ($('firstFour') && $('regionGrid') && $('finalFour')) {
    renderBracketViz(meta);
  }

  const rounds = Array.from(new Set(state.bracket.map((r) => r.round_name))).filter(Boolean);
  if ($('roundFilter')) buildRoundFilter(rounds);

  setHref('downloadZip', meta.data_archive || '#');

  // hook controls
  if ($('roundFilter')) $('roundFilter').addEventListener('change', renderBracket);
  if ($('bracketSearch')) $('bracketSearch').addEventListener('input', renderBracket);
  if ($('powerSearch')) $('powerSearch').addEventListener('input', renderPower);

  // sortable headers
  if ($('bracketTable')) {
    $('bracketTable').querySelectorAll('thead th').forEach((th) => {
      th.addEventListener('click', () => {
        setSort('bracket', th);
        renderBracket();
      });
    });
    renderBracket();
  }
  if ($('powerTable')) {
    $('powerTable').querySelectorAll('thead th').forEach((th) => {
      th.addEventListener('click', () => {
        setSort('power', th);
        renderPower();
      });
    });
    renderPower();
  }
}

boot().catch((err) => {
  $('runMeta').textContent = `Error: ${err.message}`;
});
