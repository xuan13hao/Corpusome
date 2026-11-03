#!/usr/bin/env python3
"""Figure 2 — total sample counts by body site (16S + shotgun combined), log scale."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f4p_style import apply_publication_style, finalize_figure, BODY_SITE_COLORS
import numpy as np
import matplotlib.pyplot as plt

apply_publication_style(font_size=12)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT  = os.path.join(REPO, "manuscript", "figures"); os.makedirs(OUT, exist_ok=True)

stats = json.load(open(os.path.join(REPO, "docs", "data", "stats.json")))
bbs = stats["corpus"]["by_body_site"]
items = sorted(bbs.items(), key=lambda kv: -kv[1])
sites = [k for k, _ in items]
vals  = [v for _, v in items]
colors = [BODY_SITE_COLORS[s] for s in sites]

fig, ax = plt.subplots(figsize=(7.2, 4.6))
x = np.arange(len(sites))
bars = ax.bar(x, vals, width=0.68, color=colors, edgecolor="black", linewidth=1.5, zorder=3)

ax.set_yscale("log")
ax.set_ylim(1, 3e5)
ax.set_xticks(x)
ax.set_xticklabels([s.capitalize() for s in sites], rotation=20, ha="right")
ax.set_ylabel("Samples (log scale)")
ax.yaxis.grid(True, which="major", color="#e5e7eb", linewidth=1.0, zorder=0)
ax.set_axisbelow(True)

for rect, v in zip(bars, vals):
    ax.text(rect.get_x() + rect.get_width()/2, v * 1.25, f"{v:,}",
            ha="center", va="bottom", fontsize=11, fontweight="bold", color="#1a1a1a")

paths = finalize_figure(fig, os.path.join(OUT, "Figure2_bodysite"))
print("saved:", *paths)
print("values:", dict(items))
