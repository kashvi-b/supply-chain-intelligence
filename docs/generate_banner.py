"""
Generate a professional README banner using matplotlib
Run: python docs/generate_banner.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(15, 5))
fig.patch.set_facecolor("#0F172A")
ax.set_facecolor("#0F172A")
ax.set_xlim(0, 15)
ax.set_ylim(0, 5)
ax.axis("off")

# Background grid lines (supply chain aesthetic)
for x in np.arange(0, 15, 1.5):
    ax.axvline(x, color="#1E293B", lw=0.5, alpha=0.8)
for y in np.arange(0, 5, 1):
    ax.axhline(y, color="#1E293B", lw=0.5, alpha=0.8)

# Node dots (supply chain network)
np.random.seed(42)
nodes_x = np.random.uniform(0.5, 14.5, 20)
nodes_y = np.random.uniform(0.3, 4.7, 20)
ax.scatter(nodes_x, nodes_y, color="#1A56DB",
           s=30, alpha=0.4, zorder=3)

# Connect some nodes (network lines)
for i in range(0, 18, 2):
    ax.plot([nodes_x[i], nodes_x[i+1]],
            [nodes_y[i], nodes_y[i+1]],
            color="#1A56DB", alpha=0.2, lw=1, zorder=2)

# Accent line
ax.add_patch(FancyBboxPatch(
    (0, 0), 0.4, 5,
    boxstyle="square,pad=0",
    facecolor="#1A56DB", alpha=1, zorder=4
))

# Main title
ax.text(1.0, 3.2,
        "⛓️  Supply Chain Disruption",
        fontsize=28, fontweight="bold",
        color="white", va="center",
        fontfamily="DejaVu Sans", zorder=5)

ax.text(1.0, 2.3,
        "Intelligence Platform",
        fontsize=28, fontweight="bold",
        color="#1A56DB", va="center",
        fontfamily="DejaVu Sans", zorder=5)

# Subtitle
ax.text(1.0, 1.4,
        "Enterprise-Grade Analytics · SQL · Python · ML · Streamlit",
        fontsize=12, color="#94A3B8",
        va="center", fontfamily="DejaVu Sans", zorder=5)

# Tech badges
badges = ["SQL", "Python", "scikit-learn", "Streamlit", "Plotly"]
badge_colors = ["#003B57","#3776AB","#F7931E","#FF4B4B","#3F4F75"]
for i, (badge, color) in enumerate(zip(badges, badge_colors)):
    x_pos = 1.0 + i * 2.2
    rect = FancyBboxPatch(
        (x_pos, 0.3), 1.9, 0.6,
        boxstyle="round,pad=0.1",
        facecolor=color, alpha=0.9, zorder=5
    )
    ax.add_patch(rect)
    ax.text(x_pos + 0.95, 0.6, badge,
            fontsize=9, color="white", fontweight="bold",
            ha="center", va="center", zorder=6)

# Right side metrics
metrics = [
    ("5,000+", "Shipments"),
    ("4", "ML Models"),
    ("$6M", "Impact"),
    ("0.81", "AUC Score"),
]
for i, (val, label) in enumerate(metrics):
    x = 11.0 + (i % 2) * 2.1
    y = 3.5 - (i // 2) * 1.8
    ax.text(x, y, val, fontsize=16, fontweight="bold",
            color="#1A56DB", ha="center", va="center", zorder=5)
    ax.text(x, y - 0.55, label, fontsize=8,
            color="#94A3B8", ha="center", va="center", zorder=5)

plt.tight_layout(pad=0)
plt.savefig("docs/screenshots/banner.png",
            dpi=150, bbox_inches="tight",
            facecolor="#0F172A")
print("✓ Banner saved to docs/screenshots/banner.png")
plt.show()