/* ═══════════════════════════════════════════════════════════════
   Corpusome — main.js  (shared utilities + nav injection)
   ═══════════════════════════════════════════════════════════════ */

/* ── Colour palettes ─────────────────────────────────────────────── */
const BODY_SITE_COLORS = {
  stool:       '#059669',
  oral:        '#dc2626',
  skin:        '#7c3aed',
  respiratory: '#0284c7',
  urogenital:  '#db2777',
  milk:        '#d97706',
};
const SOURCE_COLORS = {
  MGnify_full:            '#1d4ed8',
  curatedMetagenomicData: '#7c3aed',
  AGP:                    '#059669',
  MGnify:                 '#d97706',
};
const MODALITY_COLORS = {
  '16S':    '#1d4ed8',
  shotgun:  '#dc2626',
};

/* ── Dark-mode helpers ───────────────────────────────────────────── */
function isDark() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function plotlyLayout(overrides = {}) {
  const dark = isDark();
  const base = {
    paper_bgcolor: dark ? '#1e293b' : '#ffffff',
    plot_bgcolor:  dark ? '#1e293b' : '#ffffff',
    font: {
      color:  dark ? '#e2e8f0' : '#1e293b',
      family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      size:   12,
    },
    xaxis: {
      gridcolor:     dark ? '#334155' : '#e2e8f0',
      linecolor:     dark ? '#475569' : '#cbd5e1',
      zerolinecolor: dark ? '#475569' : '#cbd5e1',
      tickfont:      { size: 11 },
    },
    yaxis: {
      gridcolor:     dark ? '#334155' : '#e2e8f0',
      linecolor:     dark ? '#475569' : '#cbd5e1',
      zerolinecolor: dark ? '#475569' : '#cbd5e1',
      tickfont:      { size: 11 },
    },
    margin:   { l: 55, r: 20, t: 30, b: 55 },
    legend:   { bgcolor: 'transparent', font: { size: 11 } },
    hoverlabel: {
      bgcolor:    dark ? '#334155' : '#f8fafc',
      bordercolor:dark ? '#475569' : '#e2e8f0',
      font:       { color: dark ? '#e2e8f0' : '#1e293b', size: 12 },
    },
  };
  return Object.assign(base, overrides);
}

const PLOTLY_CONFIG = {
  displayModeBar: true,
  displaylogo:    false,
  responsive:     true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
};

/* ── Number formatting ───────────────────────────────────────────── */
function fmtNum(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000)     return Math.round(n / 1_000) + 'k';
  return String(n);
}
function fmtNumFull(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US');
}

/* ── Badge renderer ──────────────────────────────────────────────── */
function badge(val) {
  if (!val) return '';
  const cls = 'badge-' + val.replace(/\s+/g, '_').replace(/[^A-Za-z0-9_-]/g, '');
  return `<span class="badge ${cls}">${val}</span>`;
}

/* ── Nav injection ───────────────────────────────────────────────── */
const NAV_LINKS = [
  { href: 'index.html',         label: 'Overview'       },
  { href: 'browse.html',        label: 'Browse'         },
  { href: 'qc.html',            label: 'Quality Control'},
  { href: 'batch.html',         label: 'Batch Effects'  },
  { href: 'documentation.html', label: 'Documentation'  },
  { href: 'cite.html',          label: 'Cite'           },
  { href: 'download.html',      label: 'Download'       },
];

(function initNav() {
  const cur = window.location.pathname.split('/').pop() || 'index.html';

  const links = (mobile) => NAV_LINKS.map(l => {
    const cls = cur === l.href ? ' active' : '';
    return `<a class="nav-link${cls}" href="${l.href}">${l.label}</a>`;
  }).join(mobile ? '' : '');

  document.body.insertAdjacentHTML('afterbegin', `
    <nav class="nav">
      <a class="nav-brand" href="index.html">Corpusome <span class="version">v1.1</span></a>
      <div class="nav-links">${links(false)}</div>
      <button class="nav-hamburger" id="_nav_ham" aria-label="Toggle menu">&#9776;</button>
    </nav>
    <div class="nav-mobile-menu" id="_nav_mob">${links(true)}</div>
  `);

  document.getElementById('_nav_ham').addEventListener('click', () => {
    document.getElementById('_nav_mob').classList.toggle('open');
  });

  document.body.insertAdjacentHTML('beforeend', `
    <footer class="footer">
      Corpusome v1.1 &mdash; 187,546 human microbiome samples · 6 body sites · 775 studies &mdash;
      <a href="cite.html">How to Cite</a> &middot;
      <a href="download.html">Download</a> &middot;
      <a href="https://github.com/xuan13hao/Corpusome" target="_blank" rel="noopener">GitHub</a>
    </footer>
  `);
})();
