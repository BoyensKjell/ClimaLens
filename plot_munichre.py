"""Charts of the Munich Re stress test for the slides: python plot_munichre.py [output folder]

Writes two 16:9 PNG files:
  double_trap.png   both sides of the balance sheet per NGFS scenario, in % of equity
  top_sectors.png   the sectors with the largest investment losses under Net Zero 2050
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import run_munichre as mr  # noqa: E402
from climalens.sector_stress import top_sectors  # noqa: E402

ASSETS = "#2a78d6"  # categorical slot 1
NATCAT = "#eb6834"  # categorical slot 2
INK, INK_2, GRID, SURFACE = "#1f1f1e", "#5f5e58", "#e4e3de", "#fcfcfb"
SOURCE = ("Source: Munich Re annual reports 2021-2025; NGFS Phase V (2030 carbon prices); "
          "Swiss Re sigma 4/2021 (nat-cat uplift); own calculation (ClimaLens)")

plt.rcParams.update({
    "font.size": 15, "text.color": INK, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def style(ax):
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.tick_params(axis="x", length=0)


def header(fig, title, subtitle):
    fig.text(0.04, 0.93, title, fontsize=24, fontweight="bold")
    fig.text(0.04, 0.87, subtitle, fontsize=16, color=INK_2)
    fig.text(0.04, 0.03, SOURCE, fontsize=11, color=INK_2)


def double_trap_chart(path):
    t = mr.trap().iloc[::-1]  # Net Zero at the bottom, Current Policies on top
    labels = [f"{name}\n{p:.0f} EUR/t CO2 in 2030"
              for name, p in zip(t["scenario"], [p[0].carbon_price_eur for p in mr.pairs][::-1])]
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    fig.subplots_adjust(left=0.25, right=0.93, top=0.74, bottom=0.16)
    y = range(len(t))
    gap = dict(edgecolor=SURFACE, linewidth=2, height=0.55)
    ax.barh(y, t["asset_pct_equity"], color=ASSETS, label="Investments: loss from carbon price", **gap)
    ax.barh(y, t["liability_pct_equity"], left=t["asset_pct_equity"], color=NATCAT,
            label="Underwriting: extra nat-cat losses 2026-2030", **gap)
    for yi, a, l, n in zip(y, t["asset_pct_equity"], t["liability_pct_equity"], t["net_pct_equity"]):
        if a > 1.5:
            ax.text(a / 2, yi, f"{a:.1f} %", ha="center", va="center", color="white", fontsize=14)
        ax.text(n + 0.25, yi, f"{n:.1f} %", ha="left", va="center", fontsize=17, fontweight="bold")
    ax.set_yticks(list(y), labels)
    ax.set_xlabel("% of Munich Re group equity (EUR 33.4 bn, end of 2025)")
    ax.set_xlim(0, max(t["net_pct_equity"]) * 1.15)
    style(ax)
    ax.legend(loc="lower right", frameon=False, fontsize=14, bbox_to_anchor=(1.0, 1.0), ncol=2)
    header(fig, "Munich Re: the double climate trap up to 2030",
           "No natural hedge yet: the carbon price hits the investments much harder than nat-cat losses hit underwriting")
    fig.savefig(path, dpi=150)
    plt.close(fig)


def top_sectors_chart(path, n=6):
    nz = mr.pairs[-1][0]
    top = top_sectors(mr.portfolio, nz, mr.BASE_PRICE_EUR, n=n, **mr.DEFAULTS).iloc[::-1]
    names = top["sector_en"].replace({"Other (no GICS assignment)": "No industry given in the report",
                                      "Other GICS industries": "All other industries",
                                      "Independent power & renewable electricity producers": "Independent power producers"})
    fig, ax = plt.subplots(figsize=(13.33, 7.5))
    fig.subplots_adjust(left=0.3, right=0.95, top=0.76, bottom=0.16)
    loss = top["loss_eur"] / 1e6
    ax.barh(names, loss, color=ASSETS, height=0.55, edgecolor=SURFACE, linewidth=2)
    for yi, (v, c) in enumerate(zip(loss, top["carrying_amount_meur"])):
        ax.text(v + loss.max() * 0.01, yi, f"EUR {v:,.0f} m  ({v / c * 100:.0f} % of EUR {c / 1e3:,.1f} bn invested)",
                va="center", fontsize=13, color=INK)
    ax.set_xlabel("Investment loss under Net Zero 2050, EUR m")
    ax.set_xlim(0, loss.max() * 1.85)
    style(ax)
    header(fig, f"Where the {nz.name} loss comes from",
           f"Largest investment losses by industry at {nz.carbon_price_eur:.0f} EUR/t CO2 (equity, loans and bonds together)")
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output")
    out.mkdir(parents=True, exist_ok=True)
    double_trap_chart(out / "double_trap.png")
    top_sectors_chart(out / "top_sectors.png")
    print(f"Charts written to {out}/")
