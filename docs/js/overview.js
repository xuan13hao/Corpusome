/* ═══════════════════════════════════════════════════════════════
   overview.js  — Overview / landing page
   ═══════════════════════════════════════════════════════════════ */

async function loadOverview() {
  const stats    = SUMMARY_STATS;
  const breakdown = BREAKDOWN_DATA;

  /* ── Stat cards ───────────────────────────────────────────────── */
  document.getElementById('stat-samples').textContent    = fmtNumFull(stats.n_samples_total);
  document.getElementById('stat-studies').textContent    = fmtNumFull(stats.n_studies);
  document.getElementById('stat-sites').textContent      = stats.n_body_sites;
  document.getElementById('stat-countries').textContent  = stats.n_countries;
  document.getElementById('stat-taxa-16s').textContent   = fmtNumFull(stats.n_taxa_16s);
  document.getElementById('stat-taxa-shg').textContent   = fmtNumFull(stats.n_taxa_shotgun);

  const ld  = plotlyLayout();
  const cfg = PLOTLY_CONFIG;

  /* ── Chart 1: Samples by body site × source (stacked bar) ─────── */
  const sites  = ['stool', 'respiratory', 'oral', 'skin', 'urogenital', 'brain'];
  const bySrc  = {};
  breakdown.forEach(row => {
    if (!bySrc[row.source]) bySrc[row.source] = {};
    bySrc[row.source][row.body_site] = (bySrc[row.source][row.body_site] || 0) + row.n_samples;
  });

  const srcOrder = ['MGnify_full', 'curatedMetagenomicData', 'AGP', 'MGnify',
                    'Ferreiro2023', 'Brain_16S', 'TCGA_Poore2020', 'BALF_mNGS', 'Hartwig_Battaglia2024', 'MLRepo'];
  const srcTraces = srcOrder.map(src => ({
    name: src.replace('curatedMetagenomicData', 'cMD'),
    type: 'bar',
    x: sites,
    y: sites.map(s => bySrc[src]?.[s] || 0),
    marker: { color: SOURCE_COLORS[src] },
    hovertemplate: `<b>${src}</b><br>%{x}: %{y:,} samples<extra></extra>`,
  }));

  Plotly.newPlot('chart-site-src', srcTraces, {
    ...ld,
    barmode: 'stack',
    xaxis:  { ...ld.xaxis, title: { text: 'Body site' } },
    yaxis:  { ...ld.yaxis, title: { text: 'Sample count' } },
    legend: { ...ld.legend, orientation: 'h', y: -0.26, x: 0 },
    margin: { l: 60, r: 20, t: 20, b: 95 },
  }, cfg);

  /* ── Chart 2: 16S vs Shotgun per body site (grouped bar) ─────── */
  const mod16Trace = {
    name: '16S', type: 'bar',
    x: sites,
    y: sites.map(s => stats.body_site_x_modality['16S'][s] || 0),
    marker: { color: MODALITY_COLORS['16S'] },
    hovertemplate: '<b>16S</b><br>%{x}: %{y:,}<extra></extra>',
  };
  const modSgTrace = {
    name: 'Shotgun', type: 'bar',
    x: sites,
    y: sites.map(s => stats.body_site_x_modality['shotgun'][s] || 0),
    marker: { color: MODALITY_COLORS.shotgun },
    hovertemplate: '<b>Shotgun</b><br>%{x}: %{y:,}<extra></extra>',
  };

  Plotly.newPlot('chart-modality', [mod16Trace, modSgTrace], {
    ...ld,
    barmode: 'group',
    xaxis:  { ...ld.xaxis, title: { text: 'Body site' } },
    yaxis:  { ...ld.yaxis, title: { text: 'Sample count' }, type: 'log' },
    legend: { ...ld.legend, x: 0.70, y: 0.95 },
    margin: { l: 65, r: 20, t: 20, b: 60 },
  }, cfg);

  /* ── Chart 3: Health status breakdown (shotgun tier) ─────────── */
  const hsLabels = ['healthy', 'diseased', 'unlabeled'];
  const hsColors = { healthy: '#059669', diseased: '#dc2626', unlabeled: '#94a3b8' };

  Plotly.newPlot('chart-health', [{
    type: 'pie', hole: 0.52,
    values: hsLabels.map(h => stats.health_status[h] || 0),
    labels: hsLabels,
    marker: { colors: hsLabels.map(h => hsColors[h]) },
    textinfo: 'label+percent',
    textposition: 'outside',
    hovertemplate: '<b>%{label}</b><br>%{value:,} samples<br>%{percent}<extra></extra>',
  }], {
    ...ld,
    showlegend: false,
    margin: { l: 20, r: 20, t: 20, b: 20 },
  }, cfg);

  /* ── Chart 4: Body-site total bars ──────────────────────────── */
  const bsTotals = Object.entries(stats.by_body_site)
    .filter(([k]) => k !== 'milk')
    .sort((a, b) => b[1] - a[1]);

  Plotly.newPlot('chart-bodysite', [{
    type: 'bar',
    x: bsTotals.map(([k]) => k),
    y: bsTotals.map(([, v]) => v),
    marker: { color: bsTotals.map(([k]) => BODY_SITE_COLORS[k] || '#94a3b8') },
    hovertemplate: '<b>%{x}</b><br>%{y:,} samples<extra></extra>',
    text: bsTotals.map(([, v]) => fmtNum(v)),
    textposition: 'outside',
  }], {
    ...ld,
    xaxis:  { ...ld.xaxis, title: { text: 'Body site' } },
    yaxis:  { ...ld.yaxis, title: { text: 'Sample count' } },
    margin: { l: 65, r: 20, t: 35, b: 60 },
    showlegend: false,
  }, cfg);
}

loadOverview();
