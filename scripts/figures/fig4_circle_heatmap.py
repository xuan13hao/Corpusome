#!/usr/bin/env python3
"""Figure 4 — body-site signature taxa as a circle heatmap.
Circle size = prevalence (fraction of samples detected); colour = mean relative
abundance. Rows = union of the top-12 taxa of each body site; black outline marks
taxa in the top-12 of that site. figures4papers style, Arial 12."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f4p_style import apply_publication_style, finalize_figure
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D

apply_publication_style(font_size=12)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT  = os.path.join(REPO, "manuscript", "figures"); os.makedirs(OUT, exist_ok=True)

T = json.load(open(os.path.join(REPO, "docs", "data", "taxon_stats.json")))
stats, top = T["taxon_stats"], T["top_taxa"]
SITE_ORDER = ["stool", "respiratory", "oral", "skin", "urogenital", "milk"]
CMAP = "magma_r"

def lab(t):
    return t.replace("g__", "").replace("s__", "").replace("_", " ")

def panel(ax, tier, title):
    sites = [s for s in SITE_ORDER if s in top[tier]]
    # row set = union of each site's top-12 (excl Other), ordered site-by-site
    seen, rows = set(), []
    topset = {s: {d["taxon"] for d in top[tier][s] if d["taxon"] != "Other"} for s in sites}
    for s in sites:
        for d in top[tier][s]:
            if d["taxon"] != "Other" and d["taxon"] not in seen:
                seen.add(d["taxon"]); rows.append(d["taxon"])
    # lookup prevalence / mean_relab
    idx = {(r["tier"], r["taxon"]): r["sites"] for r in stats}
    xs, ys, sizes, colors, edges = [], [], [], [], []
    for yi, tax in enumerate(rows):
        sd = idx.get((tier, tax), {})
        for xi, s in enumerate(sites):
            if s in sd:
                prev, mean = sd[s]
                if prev <= 0:
                    continue
                xs.append(xi); ys.append(yi)
                sizes.append(30 + prev * 320)
                colors.append(max(mean * 100, 1e-3))  # % , floor
                edges.append("black" if tax in topset[s] else "none")
    sc = ax.scatter(xs, ys, s=sizes, c=colors, cmap=CMAP,
                    norm=LogNorm(vmin=1e-2, vmax=60),
                    edgecolors=edges, linewidths=1.1, alpha=0.95, zorder=3)
    ax.set_xticks(range(len(sites)))
    ax.set_xticklabels([s.capitalize() for s in sites], rotation=30, ha="right")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([lab(t) for t in rows], fontstyle="italic", fontsize=10)
    ax.set_ylim(-0.7, len(rows) - 0.3); ax.set_xlim(-0.7, len(sites) - 0.3)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
    ax.grid(True, color="#eee", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    return sc, len(rows)

n16 = len({d["taxon"] for s in top["16S"] for d in top["16S"][s] if d["taxon"] != "Other"})
nsg = len({d["taxon"] for s in top["shotgun"] for d in top["shotgun"][s] if d["taxon"] != "Other"})
H = max(n16, nsg) * 0.285 + 2.0

fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.5, H))
fig.subplots_adjust(left=0.135, right=0.85, wspace=0.95, top=0.975, bottom=0.07)
sc, _ = panel(axA, "16S", "a   16S tier (genus)")
scB, _ = panel(axB, "shotgun", "b   Shotgun tier (species)")

# shared colourbar (mean relative abundance %) — dedicated right-margin axes
cax = fig.add_axes([0.885, 0.50, 0.014, 0.38])
cb = fig.colorbar(scB, cax=cax)
cb.set_label("Mean relative abundance (%)")

# size legend (prevalence) — right margin, below the colourbar, outside the panels
handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor="#9aa0a6",
                  markeredgecolor="none", markersize=np.sqrt((30 + p*320)/np.pi)*1.3,
                  label=f"{int(p*100)}%") for p in (0.1, 0.5, 0.9)]
fig.legend(handles=handles, title="Prevalence", loc="center left",
           bbox_to_anchor=(0.868, 0.22), labelspacing=1.4, borderpad=0.9,
           handletextpad=1.2, frameon=False, fontsize=10, title_fontsize=11)

for ext in ("png", "pdf"):
    fig.savefig(os.path.join(OUT, f"Figure4_circle_heatmap.{ext}"), dpi=300, bbox_inches="tight")
plt.close(fig)
print("saved Figure4_circle_heatmap.png/.pdf | rows 16S/shotgun:", n16, nsg)
