"""Circular heatmaps of body-site signature taxa in Corpusome.

Each panel: sectors = union of the top-12 taxa of every body site (per tier), ordered by
the site where mean abundance peaks; rings = body sites (stool innermost); cell colour =
mean relative abundance (log10) from taxa_prevalence_abundance_long.csv; black dot = taxon
is in that site's top-12 list (taxa_top_by_bodysite.csv); outer arc = site of peak abundance.
All geometry is drawn in millimetres on one canvas.
"""
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Patch
from matplotlib.colors import LogNorm

# ── repo paths (inputs from exports/, outputs to manuscript/figures/) ────────
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTS = os.path.join(REPO, "exports")
OUT = os.path.join(REPO, "manuscript", "figures")
os.makedirs(OUT, exist_ok=True)
OUT_PREFIX = os.path.join(OUT, "Figure4_circular_heatmap")

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'sans-serif']
mpl.rcParams.update({'svg.fonttype': 'none', 'pdf.fonttype': 42, 'font.size': 7,
                     'legend.frameon': False})

LONG = pd.read_csv(os.path.join(EXPORTS, 'taxa_prevalence_abundance_long.csv'))
TOP = pd.read_csv(os.path.join(EXPORTS, 'taxa_top_by_bodysite.csv'))
SITE_ORDER = {'16S': ['stool', 'oral', 'respiratory', 'skin', 'urogenital'],
              'shotgun': ['stool', 'oral', 'respiratory', 'skin', 'urogenital', 'milk']}
SITE_LABEL = {'stool': 'Stool', 'oral': 'Oral', 'respiratory': 'Respiratory',
              'skin': 'Skin', 'urogenital': 'Urogenital', 'milk': 'Milk'}
SITE_COLOR = {'stool': '#8C6D46', 'oral': '#C0392B', 'respiratory': '#3A78B5',
              'skin': '#E59A3B', 'urogenital': '#C94F94', 'milk': '#7A8C99'}
TIER_TITLE = {'16S': '16S rRNA tier (genus)', 'shotgun': 'Shotgun tier (species)'}
NORM = LogNorm(vmin=1e-5, vmax=1.0)   # values below 0.001% (including zero) drawn grey
CMAP = plt.get_cmap('YlGnBu').with_extremes(under='#E3E3E3')  # < 0.001% (incl. absent)
GAP_DEG = 44.0                         # opening at 12 o'clock for ring labels


def tier_tables(tier):
    sites = SITE_ORDER[tier]
    top = TOP[(TOP.tier == tier) & (TOP.taxon != 'Other')]
    taxa = top.taxon.unique()
    long = LONG[(LONG.tier == tier) & LONG.taxon.isin(taxa) & LONG.body_site.isin(sites)]
    assert len(long) == len(taxa) * len(sites), (tier, len(long))
    ab = long.pivot(index='taxon', columns='body_site', values='mean_relative_abundance')[sites]
    names = long.drop_duplicates('taxon').set_index('taxon').taxon_name
    peak = ab.idxmax(axis=1)
    order = sorted(ab.index, key=lambda t: (sites.index(peak[t]), -ab.loc[t, peak[t]]))
    in_top = {(r.taxon, r.body_site) for r in top.itertuples()}
    n = LONG[LONG.tier == tier].groupby('body_site').n_samples_in_site.first()
    return sites, ab.loc[order], names[order], peak[order], in_top, n


def label_name(name, tier):
    if tier == 'shotgun' and ' ' in name:
        g, sp = name.split(' ', 1)
        return f'{g[0]}. {sp}'
    return name


def circle(ax, tier, cx, cy, r0, rw):
    sites, ab, names, peak, in_top, n = tier_tables(tier)
    nt, ns = len(ab), len(sites)
    span = 360.0 - GAP_DEG
    step = span / nt
    start = 90.0 - GAP_DEG / 2           # first sector just right of the opening, clockwise
    r_out = r0 + ns * rw
    for i, taxon in enumerate(ab.index):
        a1 = start - i * step            # clockwise: decreasing angle
        a0 = a1 - step
        for j, s in enumerate(sites):
            v = ab.loc[taxon, s]
            ax.add_patch(Wedge((cx, cy), r0 + (j + 1) * rw, a0, a1, width=rw,
                               facecolor=CMAP(NORM(v)) if v >= NORM.vmin else CMAP.get_under(), edgecolor='white', linewidth=0.35))
            if (taxon, s) in in_top:
                am = np.deg2rad((a0 + a1) / 2); rm = r0 + (j + 0.5) * rw
                ax.plot(cx + rm * np.cos(am), cy + rm * np.sin(am), 'o', ms=1.6,
                        mfc='black', mec='white', mew=0.3)
        # outer arc: site where this taxon peaks
        ax.add_patch(Wedge((cx, cy), r_out + 1.9, a0, a1, width=1.1,
                           facecolor=SITE_COLOR[peak[taxon]], edgecolor='white', linewidth=0.35))
        # radial taxon label, flipped on the left half for readability
        am = (a0 + a1) / 2
        rl = r_out + 2.6
        x, y = cx + rl * np.cos(np.deg2rad(am)), cy + rl * np.sin(np.deg2rad(am))
        ang = am % 360
        if 90 < ang < 270:
            rot, ha = ang - 180, 'right'
        else:
            rot, ha = ang, 'left'
        ax.text(x, y, label_name(names[taxon], tier), rotation=rot, rotation_mode='anchor',
                ha=ha, va='center', fontsize=6.5, fontstyle='italic')
    # ring labels in the opening (right-aligned just left of the 12 o'clock axis)
    for j, s in enumerate(sites):
        rm = r0 + (j + 0.5) * rw
        ax.text(cx, cy + rm, SITE_LABEL[s], ha='center', va='center',
                fontsize=6.5, color='#272727')
    return {s: n[s] for s in sites}


# Compact layout: two circles stacked on the left, all legends in a right column.
W, H = 150.0, 190.0
fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal'); ax.axis('off')

A = dict(cx=50.0, cy=H - 50.0, r0=11.0, rw=3.0)
B = dict(cx=50.0, cy=48.0, r0=11.0, rw=2.7)
nA = circle(ax, '16S', **A)
nB = circle(ax, 'shotgun', **B)

def n_block(x, y, nd):
    ax.text(x, y, 'Rings, inner → outer (n samples):\n' +
            '\n'.join(f'{SITE_LABEL[s]}  {v:,}' for s, v in nd.items()),
            fontsize=6.5, va='top', color='#4D4D4D', linespacing=1.35)

ax.text(2, H - 3, 'A', fontsize=16, fontweight='bold', va='top')
ax.text(10, H - 4.0, TIER_TITLE['16S'], fontsize=8.5, va='top')
ax.text(2, 95, 'B', fontsize=16, fontweight='bold', va='top')
ax.text(10, 94.0, TIER_TITLE['shotgun'], fontsize=8.5, va='top')

# ── right column: colourbar, legends, n-sample blocks ────────────────────────
RX = 104.0
ax.text(RX, H - 8, 'Mean relative\nabundance (%)', fontsize=7.5, va='top')
cax = fig.add_axes([RX / W, (H - 56) / H, 3.0 / W, 34 / H])
sm = mpl.cm.ScalarMappable(norm=NORM, cmap=CMAP)
cb = fig.colorbar(sm, cax=cax, extend='min', extendfrac=0.06)
cb.set_ticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1])
cb.set_ticklabels(['0.001', '0.01', '0.1', '1', '10', '100'])
cb.ax.tick_params(labelsize=6.5, width=0.5, length=2)
cb.outline.set_linewidth(0.5)
ax.text(RX + 5.5, H - 58, '<0.001 or absent', fontsize=6.5, va='top', color='#4D4D4D')

site_handles = [Patch(facecolor=SITE_COLOR[s], edgecolor='none', label=SITE_LABEL[s])
                for s in SITE_ORDER['shotgun']]
dot_handle = [mpl.lines.Line2D([], [], ls='', marker='o', ms=2.4, mfc='black', mec='white',
                               mew=0.3, label='Top-12 taxon of that site')]
leg1 = ax.legend(handles=site_handles, title='Peak site (outer arc)', loc='upper left',
                 bbox_to_anchor=(RX / W, (H - 70) / H), bbox_transform=fig.transFigure,
                 fontsize=6.5, title_fontsize=7.5, handlelength=1.0, handleheight=0.9,
                 labelspacing=0.45, borderaxespad=0)
leg1._legend_box.align = 'left'
ax.add_artist(leg1)
ax.legend(handles=dot_handle, loc='upper left', bbox_to_anchor=(RX / W, (H - 108) / H),
          bbox_transform=fig.transFigure, fontsize=6.5, handletextpad=0.4, borderaxespad=0)
n_block(RX, H - 120, nA)
n_block(RX, H - 150, nB)

fig.savefig(OUT_PREFIX + '.svg', bbox_inches='tight')
fig.savefig(OUT_PREFIX + '.pdf', bbox_inches='tight')
fig.savefig(OUT_PREFIX + '.tiff', dpi=600, bbox_inches='tight')
fig.savefig(OUT_PREFIX + '.png', dpi=300, bbox_inches='tight')
print('done')
