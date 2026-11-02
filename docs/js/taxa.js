/* ═══════════════════════════════════════════════════════════════
   taxa.js — Taxon browser + dominant-taxa stacked bar (real data)
   ═══════════════════════════════════════════════════════════════ */

const SITE_ORDER = ['stool', 'respiratory', 'oral', 'skin', 'urogenital', 'milk', 'brain'];
let currentTier = '16S';
let taxonTable  = null;

/* short display name: drop the g__/s__ prefix, swap underscores */
function taxonLabel(t) {
  return t.replace(/^[gs]__/, '').replace(/_/g, ' ');
}

/* ── Stacked bar: dominant taxa per body site ─────────────────────── */
function renderTopTaxa(tier) {
  const bySite = TOP_TAXA[tier] || {};
  const sites  = SITE_ORDER.filter(s => bySite[s]);

  // union of taxa across sites (keep "Other" last)
  const seen = new Set();
  const taxaOrder = [];
  sites.forEach(s => bySite[s].forEach(t => {
    if (t.taxon !== 'Other' && !seen.has(t.taxon)) { seen.add(t.taxon); taxaOrder.push(t.taxon); }
  }));
  taxaOrder.push('Other');

  const ld = plotlyLayout();
  const traces = taxaOrder.map(tax => ({
    type: 'bar',
    name: tax === 'Other' ? 'Other' : taxonLabel(tax),
    x: sites,
    y: sites.map(s => {
      const hit = (bySite[s] || []).find(t => t.taxon === tax);
      return hit ? +(hit.mean_relab * 100).toFixed(2) : 0;
    }),
    marker: tax === 'Other' ? { color: '#cbd5e1' } : {},
    hovertemplate: `<b>${tax === 'Other' ? 'Other' : taxonLabel(tax)}</b><br>%{x}: %{y:.2f}%<extra></extra>`,
  }));

  Plotly.react('chart-top-taxa', traces, {
    ...ld,
    barmode: 'stack',
    xaxis: { ...ld.xaxis, title: { text: 'Body site' } },
    yaxis: { ...ld.yaxis, title: { text: 'Mean relative abundance (%)' } },
    legend: { ...ld.legend, orientation: 'h', y: -0.18, x: 0, font: { size: 10 } },
    margin: { l: 60, r: 20, t: 20, b: 120 },
  }, PLOTLY_CONFIG);
}

/* ── Taxon browser table ──────────────────────────────────────────── */
function browserData(tier) {
  const sites = SITE_ORDER.filter(s =>
    TAXON_STATS.some(r => r.tier === tier && r.sites[s]));
  const rows = TAXON_STATS.filter(r => r.tier === tier).map(r => {
    const row = { taxon: taxonLabel(r.taxon), raw: r.taxon };
    sites.forEach(s => {
      const v = r.sites[s];               // [prevalence, mean_relab]
      row[s] = v ? v[0] : null;           // prevalence (sortable number)
      row[s + '_relab'] = v ? v[1] : null;
    });
    return row;
  });
  return { rows, sites };
}

function prevFormatter(cell) {
  const v = cell.getValue();
  if (v == null) return '<span style="color:var(--text-muted)">—</span>';
  const relab = cell.getData()[cell.getField() + '_relab'];
  const pct = (v * 100).toFixed(1) + '%';
  const title = relab != null ? `mean relative abundance: ${(relab * 100).toFixed(3)}%` : '';
  // shade by prevalence
  const a = Math.min(1, v) * 0.55 + 0.05;
  return `<span title="${title}" style="display:inline-block;min-width:3.2em;text-align:right;`
       + `background:rgba(37,99,235,${a.toFixed(2)});color:${v > 0.6 ? '#fff' : 'inherit'};`
       + `border-radius:4px;padding:1px 6px">${pct}</span>`;
}

function renderBrowser(tier) {
  const { rows, sites } = browserData(tier);
  const columns = [
    { title: 'Taxon', field: 'taxon', minWidth: 200, frozen: true,
      formatter: c => `<span style="font-style:italic">${c.getValue()}</span>`,
      headerFilter: false },
  ];
  sites.forEach(s => columns.push({
    title: s, field: s, hozAlign: 'right', minWidth: 95, sorter: 'number',
    formatter: prevFormatter,
  }));

  if (taxonTable) { taxonTable.destroy(); }
  taxonTable = new Tabulator('#taxon-table', {
    data: rows,
    layout: 'fitDataStretch',
    pagination: true,
    paginationSize: 25,
    paginationSizeSelector: [25, 50, 100],
    movableColumns: true,
    initialSort: [{ column: sites[0], dir: 'desc' }],
    placeholder: '<div style="padding:2rem;text-align:center;color:var(--text-muted)">No matching taxa.</div>',
    columns,
  });
  taxonTable.on('tableBuilt', () =>
    document.getElementById('taxa-count').textContent = fmtNumFull(taxonTable.getDataCount()));
}

/* ── Search ───────────────────────────────────────────────────────── */
function applyTaxonSearch() {
  const q = document.getElementById('taxon-search').value.toLowerCase().trim();
  if (!taxonTable) return;
  if (!q) taxonTable.clearFilter();
  else taxonTable.setFilter('taxon', 'like', q);
  document.getElementById('taxa-count').textContent = fmtNumFull(taxonTable.getDataCount());
}

/* ── Init ─────────────────────────────────────────────────────────── */
function loadTaxa() {
  renderTopTaxa(currentTier);
  renderBrowser(currentTier);

  document.querySelectorAll('.tier-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTier = btn.dataset.tier;
      renderTopTaxa(currentTier);
      renderBrowser(currentTier);
      document.getElementById('taxon-search').value = '';
    });
  });

  const si = document.getElementById('taxon-search');
  si.addEventListener('keyup', applyTaxonSearch);
}

loadTaxa();
