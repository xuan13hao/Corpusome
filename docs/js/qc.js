/* ═══════════════════════════════════════════════════════════════
   qc.js  — Quality Control visualizations
   ═══════════════════════════════════════════════════════════════ */

async function loadQC() {
  const data = QC_DATA;

  const ld  = plotlyLayout();
  const cfg = PLOTLY_CONFIG;
  const sites  = ['stool', 'oral', 'skin', 'respiratory', 'urogenital'];
  const dark   = isDark();

  /* ── Chart 1: Alpha diversity (Shannon) by body site — violin ─── */
  const alphaTraces = sites.map(bs => {
    const vals = data.filter(r => r.body_site === bs)
                     .map(r => r.alpha_diversity_shannon);
    const c = BODY_SITE_COLORS[bs] || '#94a3b8';
    return {
      type: 'violin', name: bs, y: vals,
      box:       { visible: true, width: 0.2 },
      meanline:  { visible: true, color: '#fff' },
      marker:    { color: c, size: 3, opacity: 0.5 },
      line:      { color: c },
      fillcolor: c + '44',
      points:    'outliers',
      hoverinfo: 'y+name',
    };
  });

  Plotly.newPlot('chart-alpha', alphaTraces, {
    ...ld,
    violinmode: 'overlay',
    xaxis:  { ...ld.xaxis, title: { text: 'Body site' } },
    yaxis:  { ...ld.yaxis, title: { text: "Shannon diversity (H′)" }, rangemode: 'tozero' },
    showlegend: false,
    margin: { l: 60, r: 20, t: 20, b: 60 },
  }, cfg);

  /* ── Chart 2: Read depth histogram by modality ─────────────────── */
  const depthByMod = {};
  data.forEach(r => {
    if (!depthByMod[r.modality]) depthByMod[r.modality] = [];
    depthByMod[r.modality].push(r.read_depth / 1_000_000);
  });

  const depthTraces = Object.entries(depthByMod).map(([m, vals]) => ({
    type: 'histogram', name: m, x: vals,
    opacity: 0.72,
    marker: { color: MODALITY_COLORS[m] },
    nbinsx: 35,
    hovertemplate: `<b>${m}</b><br>%{x:.1f}M reads<br>count: %{y}<extra></extra>`,
  }));

  Plotly.newPlot('chart-depth', depthTraces, {
    ...ld,
    barmode: 'overlay',
    xaxis: { ...ld.xaxis, title: { text: 'Read depth (millions)' } },
    yaxis: { ...ld.yaxis, title: { text: 'Sample count' } },
    legend: { ...ld.legend, x: 0.72, y: 0.95 },
    margin: { l: 60, r: 20, t: 20, b: 60 },
  }, cfg);

  /* ── Chart 3: Number of detected taxa by body site — box plot ─── */
  const taxaTraces = sites.map(bs => {
    const vals = data.filter(r => r.body_site === bs).map(r => r.n_taxa);
    const c = BODY_SITE_COLORS[bs] || '#94a3b8';
    return {
      type: 'box', name: bs, y: vals,
      boxpoints: 'outliers',
      marker:   { color: c, size: 3, opacity: 0.6 },
      line:     { color: c },
      fillcolor: c + '33',
    };
  });

  Plotly.newPlot('chart-taxa', taxaTraces, {
    ...ld,
    xaxis:  { ...ld.xaxis, title: { text: 'Body site' } },
    yaxis:  { ...ld.yaxis, title: { text: 'Detected taxa per sample' } },
    showlegend: false,
    margin: { l: 60, r: 20, t: 20, b: 60 },
  }, cfg);

  /* ── Chart 4: Unclassified read % histogram ─────────────────────── */
  Plotly.newPlot('chart-unclass', [{
    type: 'histogram',
    x: data.map(r => r.unclassified_pct),
    marker: { color: '#7c3aed', opacity: 0.8 },
    nbinsx: 40,
    hovertemplate: 'Unclassified: %{x:.1f}%<br>Samples: %{y}<extra></extra>',
  }], {
    ...ld,
    xaxis: { ...ld.xaxis, title: { text: 'Unclassified reads (%)' } },
    yaxis: { ...ld.yaxis, title: { text: 'Sample count' } },
    showlegend: false,
    margin: { l: 60, r: 20, t: 20, b: 60 },
  }, cfg);

  /* ── Summary stats table ─────────────────────────────────────────── */
  const tbody = document.getElementById('qc-summary-tbody');
  sites.forEach(bs => {
    const subset = data.filter(r => r.body_site === bs);
    if (!subset.length) return;
    const alphas = subset.map(r => r.alpha_diversity_shannon);
    const depths = subset.map(r => r.read_depth / 1_000_000);
    const taxa   = subset.map(r => r.n_taxa);
    const avg = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
    const med = arr => { const s = [...arr].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${badge(bs)}</td>
      <td style="text-align:right">${fmtNumFull(subset.length)}</td>
      <td style="text-align:right">${avg(alphas).toFixed(2)}</td>
      <td style="text-align:right">${med(alphas).toFixed(2)}</td>
      <td style="text-align:right">${avg(depths).toFixed(1)}M</td>
      <td style="text-align:right">${Math.round(avg(taxa))}</td>
    `;
    tbody.appendChild(tr);
  });
}

loadQC();
