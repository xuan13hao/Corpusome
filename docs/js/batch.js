/* ═══════════════════════════════════════════════════════════════
   batch.js  — Batch effect / UMAP scatter visualization
   ═══════════════════════════════════════════════════════════════ */

let embData = [];
let currentColorBy = 'body_site';
let currentCoord   = 'pre';

async function loadBatch() {
  embData = await fetch('data/embedding.json').then(r => r.json());
  renderPlot();

  /* ── Color-by toggle ─────────────────────────────────────────── */
  document.querySelectorAll('.color-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentColorBy = btn.dataset.col;
      renderPlot();
    });
  });

  /* ── Pre / Post toggle ───────────────────────────────────────── */
  document.querySelectorAll('.coord-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.coord-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCoord = btn.dataset.coord;
      renderPlot();
    });
  });
}

function getColorMap() {
  return { body_site: BODY_SITE_COLORS, source: SOURCE_COLORS, modality: MODALITY_COLORS }[currentColorBy]
      || BODY_SITE_COLORS;
}

function renderPlot() {
  const xKey = currentCoord === 'pre' ? 'umap_x_pre' : 'umap_x_post';
  const yKey = currentCoord === 'pre' ? 'umap_y_pre' : 'umap_y_post';
  const colorMap = getColorMap();

  const groups = {};
  embData.forEach(d => {
    const key = d[currentColorBy] || 'unknown';
    if (!groups[key]) groups[key] = { x: [], y: [], ids: [] };
    groups[key].x.push(d[xKey]);
    groups[key].y.push(d[yKey]);
    groups[key].ids.push(d.sample_uid.length > 30 ? d.sample_uid.slice(0, 30) + '…' : d.sample_uid);
  });

  const traces = Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0])).map(([key, vals]) => ({
    type: 'scatter', mode: 'markers',
    name: key,
    x: vals.x, y: vals.y,
    text: vals.ids,
    marker: {
      color: colorMap[key] || '#94a3b8',
      size: 7, opacity: 0.78,
      line: { width: 0.5, color: isDark() ? '#0f172a' : '#ffffff' },
    },
    hovertemplate: `<b>${key}</b><br>%{text}<br>UMAP1: %{x:.3f}<br>UMAP2: %{y:.3f}<extra></extra>`,
  }));

  const colorLabels = {
    body_site: 'Body Site',
    source:    'Data Source',
    modality:  'Sequencing Modality',
  };
  const corrLabel = currentCoord === 'pre'
    ? '⚠ Batch effect visible (uncorrected coordinates)'
    : '✓ Batch-corrected coordinates';

  const ld = plotlyLayout();
  Plotly.react('chart-umap', traces, {
    ...ld,
    xaxis:  { ...ld.xaxis, title: { text: 'UMAP 1' }, zeroline: false },
    yaxis:  { ...ld.yaxis, title: { text: 'UMAP 2' }, zeroline: false },
    legend: { ...ld.legend, x: 1.02, y: 1, xanchor: 'left', title: { text: colorLabels[currentColorBy] } },
    margin: { l: 55, r: 160, t: 45, b: 60 },
    annotations: [
      {
        x: 0.01, y: 1.04, xref: 'paper', yref: 'paper',
        text: corrLabel, showarrow: false,
        font: { size: 11, color: isDark() ? '#94a3b8' : '#64748b' },
        xanchor: 'left', yanchor: 'bottom',
      },
      {
        x: 0.01, y: 0.98, xref: 'paper', yref: 'paper',
        text: `n = ${embData.length} samples (representative subset)`,
        showarrow: false,
        font: { size: 10, color: isDark() ? '#475569' : '#94a3b8' },
        xanchor: 'left', yanchor: 'top',
      },
    ],
  }, PLOTLY_CONFIG);
}

loadBatch();
