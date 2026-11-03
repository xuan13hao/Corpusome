#!/usr/bin/env python3
"""Figure 1 — Corpusome construction pipeline (schematic), figures4papers style."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f4p_style import apply_publication_style, finalize_figure, PALETTE
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

apply_publication_style(font_size=12)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT  = os.path.join(REPO, "manuscript", "figures"); os.makedirs(OUT, exist_ok=True)

fig, ax = plt.subplots(figsize=(9.2, 7.4))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

def box(x, y, w, h, title, sub, ec, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.8",
                                linewidth=2.0, edgecolor=ec, facecolor=fc))
    ax.text(x + w/2, y + h*(0.63 if sub else 0.5), title, ha="center", va="center",
            fontsize=12, fontweight="bold", color="#1a1a1a")
    if sub:
        ax.text(x + w/2, y + h*0.25, sub, ha="center", va="center",
                fontsize=9.5, color=PALETTE["gray_dark"])

def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=15, linewidth=1.8, color=PALETTE["gray_mid"]))

# Row 1 — source resources (color by data type: blue=shotgun, teal=16S, red=disease)
box( 1, 87, 22, 10, "curatedMetagenomic\nData", "shotgun · MetaPhlAn3/HUMAnN3", PALETTE["blue_main"])
box(26, 87, 22, 10, "American Gut\nProject", "16S · Greengenes 13_8", PALETTE["teal"])
box(51, 87, 22, 10, "EBI MGnify\n(full pull)", "16S · SILVA SSU", PALETTE["teal"])
box(76, 87, 23, 10, "Disease cohorts (6)", "Kraken2 · DADA2 · NINJA-OPS", PALETTE["red_strong"])

box(10, 66, 80, 10, "Harmonization",
    "body-site vocabulary · genus correspondence map (Greengenes ↔ SILVA) · metadata provenance",
    PALETTE["gray_dark"])
box(10, 50, 80, 8, "Normalization & prevalence filter",
    "per-sample relative abundance (L1) · prevalence filter at every rank", PALETTE["gray_dark"])

box( 2, 30, 28, 12, "Shotgun tier", "species + pathways\n22,747 × 765  /  22,512 × 510", PALETTE["blue_main"])
box(36, 30, 28, 12, "16S genus tier", "harmonized genus\n165,325 × 1,491", PALETTE["teal"])
box(70, 30, 28, 12, "Disease add-ons", "condition-labelled\n1,506 samples", PALETTE["red_strong"])

box(16, 15, 68, 8, "Unified metadata catalogue",
    "189,052 samples · 7 body sites · 2 modalities · 15 fields", PALETTE["highlight"])
box(16, 1, 32, 8, "Technical validation", "PCoA · PERMANOVA", PALETTE["gray_dark"])
box(52, 1, 32, 8, "File manifest", "per-file SHA-256", PALETTE["gray_dark"])

for x in (12, 37, 62, 87.5):
    arrow(x, 87, x, 76.5)
arrow(50, 66, 50, 58.3)
arrow(50, 50, 50, 42.3)
for x in (16, 50, 84):
    arrow(x, 30, x, 23.3)
arrow(50, 15, 50, 9.2)

paths = finalize_figure(fig, os.path.join(OUT, "Figure1_pipeline"))
print("saved:", *paths)
