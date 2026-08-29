/* ═══════════════════════════════════════════════════════════════
   browse.js  — Sample browser with Tabulator
   ═══════════════════════════════════════════════════════════════ */

let allRows = [];
let table;

async function loadBrowse() {
  const data = await fetch('data/samples_browse.json').then(r => r.json());
  allRows = data;

  document.getElementById('count-total').textContent = fmtNumFull(allRows.length);

  /* ── Populate filter dropdowns ─────────────────────────────────── */
  function uniq(key) {
    return [...new Set(allRows.map(r => r[key]).filter(Boolean))].sort();
  }
  fillSelect('filter-site',     uniq('body_site'));
  fillSelect('filter-modality', uniq('modality'));
  fillSelect('filter-source',   uniq('source'));
  fillSelect('filter-health',   uniq('health_status'));

  /* ── Init Tabulator ────────────────────────────────────────────── */
  table = new Tabulator('#sample-table', {
    data: allRows,
    layout: 'fitDataStretch',
    pagination: true,
    paginationSize: 50,
    paginationSizeSelector: [25, 50, 100, 200],
    movableColumns: true,
    responsiveLayout: 'collapse',
    placeholder: '<div style="padding:2rem;text-align:center;color:var(--text-muted)">No matching samples found.</div>',
    columns: [
      {
        title: 'Sample UID', field: 'sample_uid', minWidth: 230,
        formatter: cell => `<span style="font-family:monospace;font-size:0.76rem;word-break:break-all">${cell.getValue()}</span>`,
        tooltip: true,
      },
      {
        title: 'Source', field: 'source', minWidth: 140,
        formatter: cell => badge(cell.getValue()),
        headerFilter: false,
      },
      { title: 'Study', field: 'study', minWidth: 160 },
      {
        title: 'Modality', field: 'modality', minWidth: 80,
        formatter: cell => badge(cell.getValue()),
      },
      {
        title: 'Body Site', field: 'body_site', minWidth: 100,
        formatter: cell => badge(cell.getValue()),
      },
      { title: 'Region', field: 'region', minWidth: 55 },
      {
        title: 'Age', field: 'host_age', minWidth: 55, hozAlign: 'right',
        formatter: cell => cell.getValue() != null ? cell.getValue() : '—',
        sorter: 'number',
      },
      { title: 'Sex', field: 'host_sex', minWidth: 70 },
      { title: 'Country', field: 'country', minWidth: 60 },
      { title: 'Platform', field: 'sequencing_platform', minWidth: 145 },
      { title: 'Disease', field: 'disease', minWidth: 110 },
      { title: 'Condition', field: 'study_condition', minWidth: 90 },
      {
        title: 'Health Status', field: 'health_status', minWidth: 115,
        formatter: cell => badge(cell.getValue()),
      },
    ],
  });

  /* Set initial displayed count after table is built */
  table.on('tableBuilt', () => {
    document.getElementById('count-shown').textContent = fmtNumFull(table.getDataCount());
  });

  /* ── Buttons ───────────────────────────────────────────────────── */
  document.getElementById('btn-filter').addEventListener('click', applyFilters);
  document.getElementById('btn-reset').addEventListener('click', resetFilters);
  document.getElementById('btn-export').addEventListener('click', () =>
    table.download('csv', 'corpusome_samples.csv'));
  document.getElementById('filter-search').addEventListener('keydown', e => {
    if (e.key === 'Enter') applyFilters();
  });
}

function fillSelect(id, values) {
  const sel = document.getElementById(id);
  values.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  });
}

function applyFilters() {
  const site   = document.getElementById('filter-site').value;
  const modal  = document.getElementById('filter-modality').value;
  const source = document.getElementById('filter-source').value;
  const health = document.getElementById('filter-health').value;
  const search = document.getElementById('filter-search').value.toLowerCase().trim();

  const filtered = allRows.filter(r => {
    if (site   && r.body_site     !== site)   return false;
    if (modal  && r.modality      !== modal)  return false;
    if (source && r.source        !== source) return false;
    if (health && r.health_status !== health) return false;
    if (search) {
      const hay = [r.sample_uid, r.study, r.disease, r.country,
                   r.sequencing_platform, r.pipeline, r.region].join(' ').toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });

  table.setData(filtered);
  document.getElementById('count-shown').textContent = fmtNumFull(filtered.length);
}

function resetFilters() {
  ['filter-site','filter-modality','filter-source','filter-health'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('filter-search').value = '';
  table.setData(allRows);
  document.getElementById('count-shown').textContent = fmtNumFull(allRows.length);
}

loadBrowse();
