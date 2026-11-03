"""
figures4papers house style (Chen Liu, github.com/ChenLiu-1996/figures4papers),
adapted to the user's requirement: Arial, font size 12.

Implements the repo's conventions: minimalist spines (top/right off), frameless
legends, the blue-green-red-neutral PALETTE, dpi=300 export, tight_layout(pad=2).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Official figures4papers palette ──────────────────────────────────────────
PALETTE = {
    "blue_main": "#0F4D92", "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE", "green_2": "#AADCA9", "green_3": "#8BCF8B",
    "red_1": "#F6CFCB", "red_2": "#E9A6A1", "red_strong": "#B64342",
    "neutral": "#CFCECE", "gray_mid": "#767676", "gray_dark": "#4D4D4D",
    "highlight": "#FFD700", "teal": "#42949E", "violet": "#9A4D8E",
}

# Distinct, palette-consistent colours for the seven body sites
BODY_SITE_COLORS = {
    "stool":       "#0F4D92",   # blue_main
    "respiratory": "#42949E",   # teal
    "oral":        "#B64342",   # red_strong
    "skin":        "#9A4D8E",   # violet
    "urogenital":  "#4E9A5B",   # green
    "milk":        "#C7962B",   # gold (darkened for contrast)
    "brain":       "#767676",   # neutral gray
}
MODALITY_COLORS = {"16S": "#3775BA", "shotgun": "#0F4D92"}

FONT_STACK = ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"]


def apply_publication_style(font_size=12, axes_linewidth=2.0):
    plt.rcParams.update({
        "font.family": FONT_STACK,
        "font.size": font_size,
        "axes.labelsize": font_size,
        "axes.titlesize": font_size,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
        "legend.fontsize": font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": axes_linewidth,
        "legend.frameon": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,          # editable text in PDF
        "ps.fonttype": 42,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def finalize_figure(fig, out_path_no_ext, formats=("png", "pdf"), dpi=300, pad=2):
    fig.tight_layout(pad=pad)
    paths = []
    for ext in formats:
        p = f"{out_path_no_ext}.{ext}"
        fig.savefig(p, dpi=dpi, bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    return paths
