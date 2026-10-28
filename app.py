"""ClimaLens web app: streamlit run app.py

Pages: welcome, results, industries, ORSA brief, how it works, data check.
All numbers come from the same model as run_munichre.py (src/climalens/munichre.py).
The app has a light and a dark theme (.streamlit/config.toml); all custom colours below
are mixed with the current text colour, so they work on both backgrounds.
"""

import html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from climalens import munichre  # noqa: E402
from climalens.hotspots import hotspot_losses  # noqa: E402
from climalens.report import brief_docx, brief_text  # noqa: E402
from climalens.sector_stress import run_sector_stress  # noqa: E402
from climalens.trace import NUMBER, SPACED_NUMBER, match_precision  # noqa: E402

st.set_page_config(page_title="ClimaLens", page_icon="🌍", layout="wide", initial_sidebar_state="auto")

GREEN = "#1f9d63"
ASSETS = "#2a78d6"  # blue: investments
NATCAT = "#eb6834"  # orange: underwriting
VIOLET = "#7c5cd6"
TEAL = "#0f97a8"
RED = "#d64545"
FIELD_NAMES = {"scope1_tco2e": "Scope 1", "scope2_market_tco2e": "Scope 2 (market-based)",
               "scope2_location_tco2e": "Scope 2 (location-based)", "scope3_tco2e": "Scope 3"}
SECTOR_NAMES = {"Other (no GICS assignment)": "No industry given in the report",
                "Other GICS industries": "All other industries"}
BASE = dict(pass_through=0.3, ev_ebitda_multiple=8.0, debt_loss_factor=0.3, repricing=0.5, trend=0.0)

# Values the automatic check could not find, and the hand-data errors the first run exposed (lab 21.10).
NOT_FOUND = {("SAP SE", "scope2_market_tco2e"): "The report prints this value as “1 kt”. One significant digit is "
             "too coarse for an automatic match, so it was confirmed by hand."}
# Why the AI's answer differs from the gold set, for the values it did not read correctly.
AI_NOTES = {
    "Allianz SE": "The AI took the group totals, which include Allianz's real-estate investments. The gold set uses the "
                  "rows “davon Geschäftstätigkeit der Allianz” (own operations only). The numbers were read correctly, "
                  "but from the wrong row. For Scope 3 of the own operations it gave no answer.",
}
AI_VERDICTS = {"correct": ("ok", "✓ read correctly"), "wrong": ("miss", "✗ other row"),
               "unverified": ("miss", "✗ quote not found"), "missed": ("miss", "✗ no answer")}
ERRORS_CAUGHT = [
    ("SAP SE", "Scope 3", "Both Scope 3 totals (location- and market-based) were added up to 12,503 kt.",
     "Market-based value only: 6,239 kt."),
    ("BASF SE", "Scope 1 and 2", "Values came from the production companies subset, not the whole group.",
     "ESRS gross emissions, e.g. Scope 1 from 14.22 to 15.37 Mt."),
    ("Siemens AG", "Scope 2 (market-based)", "The rounded 71 kt was typed in.", "The printed 70.7 kt."),
]

st.markdown("""
<style>
.block-container { padding-top: 2rem; max-width: 1150px; }
.cl-tint { color: color-mix(in srgb, var(--c) 82%, currentColor); }

/* welcome */
.cl-hero { padding: 1.4rem 0 1.2rem; }
.cl-eyebrow { font-size: .76rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 700;
  color: color-mix(in srgb, var(--c, #1f9d63) 80%, currentColor); }
.cl-hero h1 { font-size: clamp(2.8rem, 7vw, 4.6rem); font-weight: 800; line-height: 1.02; margin: .3rem 0 .7rem;
  padding: 0; letter-spacing: -.03em; }
.cl-hero h1 .clima { color: color-mix(in srgb, #1f9d63 88%, currentColor); }
.cl-hero h1 .lens { color: color-mix(in srgb, #2a78d6 88%, currentColor); }
.cl-lead { font-size: 1.2rem; max-width: 46rem; opacity: .86; line-height: 1.55; }

/* page headers and section titles */
.cl-head { margin: 0 0 1.3rem; padding-top: 1.2rem; }
.cl-head .cl-title { font-size: clamp(2rem, 4.5vw, 2.7rem); font-weight: 800; letter-spacing: -.02em; line-height: 1.15;
  padding: .1rem 0 .25rem; display: inline-block;
  background: linear-gradient(90deg, var(--c1), var(--c2)); -webkit-background-clip: text; background-clip: text;
  color: transparent; }
.cl-head p { margin: .2rem 0 0; opacity: .75; font-size: 1.02rem; max-width: 50rem; }
.cl-sec { display: flex; align-items: center; gap: .65rem; font-size: 1.32rem; font-weight: 700; margin: 2rem 0 .75rem;
  color: color-mix(in srgb, var(--c) 70%, currentColor); }
.cl-sec::before { content: ""; flex: none; width: .38rem; height: 1.35rem; border-radius: 4px; background: var(--c); }

/* cards and steps */
.cl-grid { display: grid; gap: .9rem; grid-template-columns: repeat(auto-fit, minmax(min(var(--min, 220px), 100%), 1fr)); }
.cl-card { border: 1px solid rgba(128,140,155,.25); border-top: 4px solid var(--c); border-radius: 10px;
  padding: 1rem 1.1rem; background: color-mix(in srgb, var(--c) 7%, transparent); }
.cl-card h4 { margin: .25rem 0 .35rem; padding: 0; font-size: 1.02rem; }
.cl-card p { margin: 0; font-size: .92rem; opacity: .86; line-height: 1.45; }
.cl-num { display: inline-flex; align-items: center; justify-content: center; width: 1.9rem; height: 1.9rem;
  border-radius: 50%; background: var(--c); color: #fff; font-weight: 800; font-size: .95rem; }
.cl-badge { display: inline-block; margin-top: .7rem; font-size: .72rem; font-weight: 700; letter-spacing: .04em;
  padding: .15rem .55rem; border-radius: 999px; }
.cl-badge.live { background: rgba(31,157,99,.16); color: color-mix(in srgb, #1f9d63 75%, currentColor); }
.cl-badge.next { background: rgba(128,140,155,.18); opacity: .85; }

/* results */
.cl-verdict { border-left: 6px solid var(--c, #2a78d6); padding: .7rem 1rem; border-radius: 0 8px 8px 0;
  background: color-mix(in srgb, var(--c, #2a78d6) 8%, transparent); font-size: 1.02rem; }
.cl-big { font-size: 2.1rem; font-weight: 700; line-height: 1.2; }
.cl-sw { display: inline-block; width: .7rem; height: .7rem; border-radius: 2px; margin-right: .35rem; background: var(--c); }
.cl-note { font-size: .82rem; opacity: .7; }
.cl-brief { font-family: Georgia, "Source Serif 4", serif; font-size: 1.08rem; line-height: 1.65; max-width: 44rem; }

/* assumptions bar */
.cl-abar { display: flex; flex-wrap: wrap; gap: .55rem; align-items: center; }
.cl-atitle { font-weight: 700; font-size: 1rem; }
.cl-avals { font-size: .86rem; opacity: .75; margin: .25rem 0 .4rem; }
.cl-avals span.on { color: color-mix(in srgb, #eb6834 80%, currentColor); font-weight: 700; opacity: 1; }
.cl-pill { font-size: .75rem; font-weight: 700; padding: .22rem .65rem; border-radius: 999px; letter-spacing: .03em; }
.cl-pill.base { background: rgba(31,157,99,.16); color: color-mix(in srgb, #1f9d63 75%, currentColor); }
.cl-pill.custom { background: rgba(235,104,52,.16); color: color-mix(in srgb, #eb6834 75%, currentColor); }

/* data check */
.cl-kpi { border: 1px solid rgba(128,140,155,.25); border-radius: 10px; padding: .9rem 1rem;
  background: color-mix(in srgb, var(--c) 6%, transparent); }
.cl-kpi .lbl { font-size: .8rem; font-weight: 600; opacity: .75; }
.cl-kpi .val { font-size: 2rem; font-weight: 800; line-height: 1.2; color: color-mix(in srgb, var(--c) 80%, currentColor); }
.cl-kpi .sub { font-size: .8rem; opacity: .7; }
.cl-bar { height: .4rem; border-radius: 999px; background: rgba(128,140,155,.2); margin: .35rem 0 .3rem; overflow: hidden; }
.cl-bar span { display: block; height: 100%; border-radius: 999px; background: var(--c); }
.cl-scroll { overflow-x: auto; }
table.cl-matrix { width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: .35rem; min-width: 680px; font-size: .9rem; }
table.cl-matrix th:first-child { width: 8.5rem; }
table.cl-matrix th:last-child { width: 4.6rem; }
table.cl-matrix th { text-align: left; font-size: .76rem; text-transform: uppercase; letter-spacing: .06em; opacity: .65;
  font-weight: 700; padding: 0 .4rem; border: none; }
table.cl-matrix td { border: none; padding: 0; vertical-align: middle; }
table.cl-matrix td.co { font-weight: 700; padding-right: .6rem; white-space: nowrap; }
.cl-cell { border-radius: 8px; padding: .45rem .6rem; line-height: 1.3; border: 1px solid transparent; }
.cl-cell b { display: block; font-size: .95rem; }
.cl-cell span { font-size: .76rem; opacity: .8; }
.cl-cell.ok { background: rgba(31,157,99,.12); border-color: rgba(31,157,99,.3); }
.cl-cell.miss { background: rgba(214,69,69,.12); border-color: rgba(214,69,69,.35); }
.cl-score { font-weight: 700; font-size: .85rem; white-space: nowrap; }
.cl-evi { border: 1px solid rgba(128,140,155,.25); border-left: 4px solid var(--c); border-radius: 8px; padding: .7rem .9rem; }
.cl-evi .hd { display: flex; flex-wrap: wrap; gap: .3rem .8rem; align-items: baseline; margin-bottom: .45rem; }
.cl-evi .hd b { font-size: .95rem; }
.cl-evi .hd .ln { margin-left: auto; font-size: .78rem; opacity: .65; }
.cl-quote { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; line-height: 1.5;
  padding: .45rem .6rem; border-radius: 6px; background: rgba(128,140,155,.1); word-break: break-word; }
.cl-quote mark { background: rgba(31,157,99,.3); color: inherit; padding: 0 .15rem; border-radius: 3px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def inputs():
    return munichre.load_inputs()


@st.cache_data
def trace_results():
    return pd.read_csv(ROOT / "data" / "gold" / "trace_results.csv")


@st.cache_data
def llm_results() -> tuple[pd.DataFrame, str]:
    """The checked answers of the last real AI run (run_extract.py) and the model that gave them."""
    gold = ROOT / "data" / "gold"
    return pd.read_csv(gold / "llm_results.csv"), json.loads((gold / "llm_answers.json").read_text())["model"]


# Keep the assumptions when the user moves to a page without the sliders (Streamlit
# otherwise forgets the value of a widget that is not shown).
for _k, _v in BASE.items():
    st.session_state[_k] = st.session_state.get(_k, _v)


def assumptions() -> dict:
    return {k: st.session_state[k] for k in BASE}


def changed() -> list[str]:
    return [k for k, v in BASE.items() if abs(st.session_state[k] - v) > 1e-9]


def reset():
    for k, v in BASE.items():
        st.session_state[k] = v


def results() -> pd.DataFrame:
    a = assumptions()
    inp = inputs()
    table = munichre.trap(inp, trend=a["trend"], repricing=a["repricing"], pass_through=a["pass_through"],
                          ev_ebitda_multiple=a["ev_ebitda_multiple"], debt_loss_factor=a["debt_loss_factor"])
    table["carbon_price_eur"] = [p[0].carbon_price_eur for p in inp.pairs]
    tops = [hotspots(i).sort_values("extra_horizon_eur", ascending=False) for i in range(len(inp.pairs))]
    table["top_hotspot"] = [h["hotspot"].iloc[0] for h in tops]
    table["top_hotspot_share"] = [h["extra_horizon_eur"].iloc[0] / h["extra_horizon_eur"].sum() * 100 for h in tops]
    return table


def hotspots(scenario_index: int, year: int = 2030) -> pd.DataFrame:
    """Extra nat-cat losses per hotspot with the current assumptions (hotspots.py)."""
    a, inp = assumptions(), inputs()
    return hotspot_losses(inp.hotspots, inp.pairs[scenario_index][1], inp.baseline_eur, year, a["trend"], a["repricing"])


def pct(v: float) -> str:
    return f"{v:.1f} %"


def bn(v: float) -> str:
    return f"EUR {v / 1e9:.2f} bn"


def tonnes(v: float) -> str:
    if v >= 1e6:
        return f"{v / 1e6:,.2f} Mt"
    if v >= 1e3:
        return f"{v / 1e3:,.1f} kt"
    return f"{v:,.0f} t"


def html_block(text: str):
    st.markdown(text, unsafe_allow_html=True)


def page_header(title: str, eyebrow: str, lead: str, c1: str = GREEN, c2: str = ASSETS):
    html_block(f'<div class="cl-head" style="--c:{c1};--c1:{c1};--c2:{c2}"><div class="cl-eyebrow">{eyebrow}</div>'
               f'<div class="cl-title">{title}</div><p>{lead}</p></div>')


def section(title: str, color: str = GREEN):
    html_block(f'<div class="cl-sec" style="--c:{color}">{title}</div>')


# ---------------------------------------------------------------- assumptions


def assumption_bar():
    """One panel: the current assumptions in a line, and the sliders when the user opens it."""
    a, diff = assumptions(), changed()
    values = [("pass_through", f"Pass-through {a['pass_through']:.0%}"),
              ("ev_ebitda_multiple", f"EV/EBITDA {a['ev_ebitda_multiple']:g}×"),
              ("debt_loss_factor", f"Loans & bonds {a['debt_loss_factor']:.0%}"),
              ("repricing", f"Repricing {a['repricing']:.0%}"),
              ("trend", f"Nat-cat trend {a['trend']:.1%}")]
    status = ('<span class="cl-pill base">Base case</span>' if not diff
              else f'<span class="cl-pill custom">{len(diff)} changed</span>')
    with st.container(border=True):
        left, right = st.columns([5, 1], vertical_alignment="center")
        with left:
            html_block(f'<div class="cl-abar"><span class="cl-atitle">Assumptions</span>{status}</div>'
                       '<div class="cl-avals">' + " · ".join(
                           f'<span class="{"on" if k in diff else ""}">{label}</span>' for k, label in values) + "</div>")
        with right:
            show = st.toggle("Adjust", key="show_assumptions")
        if show:
            inv, uw = st.columns(2, gap="large")
            with inv:
                html_block(f'<div class="cl-eyebrow" style="--c:{ASSETS}">Investments</div>')
                st.slider("Carbon cost passed on to customers", 0.0, 0.8, step=0.05, key="pass_through", format="percent",
                          help="Share of the extra carbon cost companies can add to their prices.")
                st.slider("Valuation multiple (EV/EBITDA)", 4.0, 14.0, step=0.5, key="ev_ebitda_multiple", format="%.1f×",
                          help="How much company value one euro of extra yearly cost destroys.")
                st.slider("Loss share for loans and bonds", 0.0, 1.0, step=0.05, key="debt_loss_factor", format="percent",
                          help="Lenders lose less than shareholders. 30 % = they take 30 % of the shareholder loss.")
            with uw:
                html_block(f'<div class="cl-eyebrow" style="--c:{NATCAT}">Underwriting</div>')
                st.slider("Extra nat-cat losses won back via prices", 0.0, 0.9, step=0.05, key="repricing", format="percent",
                          help="Reinsurers renew most contracts every year and can raise prices.")
                st.slider("Nat-cat loss trend per year", 0.0, 0.07, step=0.005, key="trend", format="percent",
                          help="0 % = climate effect only. Swiss Re: 5-7 % a year including growth of insured values.")
                st.button("Reset to base case", on_click=reset, icon=":material/restart_alt:", width="stretch",
                          disabled=not diff)
    st.write("")


def sidebar_footer():
    with st.sidebar:
        html_block('<div class="cl-eyebrow">Case study</div>')
        st.markdown("**Munich Re** · annual report 2025  \nHannover Re follows after the midterm.")
        st.caption("Dark mode: menu ⋮ at the top right → Settings.")


# ---------------------------------------------------------------- charts


def trap_chart(t: pd.DataFrame) -> go.Figure:
    t = t.iloc[::-1]
    labels = [f"<b>{s}</b><br>{p:.0f} EUR/t CO2" for s, p in zip(t["scenario"], t["carbon_price_eur"])]
    fig = go.Figure()
    fig.add_bar(y=labels, x=t["asset_pct_equity"], orientation="h", name="Investments: loss from carbon price",
                marker=dict(color=ASSETS), customdata=t["asset_loss_eur"] / 1e9,
                hovertemplate="Investments: %{x:.1f} % of equity<br>EUR %{customdata:.2f} bn<extra></extra>")
    fig.add_bar(y=labels, x=t["liability_pct_equity"], orientation="h", name="Underwriting: extra nat-cat losses 2026-2030",
                marker=dict(color=NATCAT),
                customdata=list(zip(t["liability_extra_eur"] / 1e9, t["top_hotspot"], t["top_hotspot_share"])),
                hovertemplate="Nat-cat: %{x:.1f} % of equity<br>EUR %{customdata[0]:.2f} bn after repricing"
                              "<br>Largest hotspot: %{customdata[1]} (%{customdata[2]:.0f} %)<extra></extra>")
    for y, n in zip(labels, t["net_pct_equity"]):
        fig.add_annotation(x=n, y=y, text=f"<b>{n:.1f} %</b>", showarrow=False, xanchor="left", xshift=8, font=dict(size=16))
    fig.update_layout(barmode="stack", bargap=0.45, height=340, margin=dict(l=10, r=40, t=10, b=10),
                      legend=dict(orientation="h", y=1.12, x=0, traceorder="normal"), xaxis=dict(title="% of group equity (EUR 33.4 bn)",
                      ticksuffix=" %", range=[0, max(t["net_pct_equity"]) * 1.18]))
    return fig


# ---------------------------------------------------------------- pages


def welcome():
    t = results()
    html_block("""
<div class="cl-hero">
  <div class="cl-eyebrow">Sustainability and ESG Data Analytics · NTPU · Kjell Boyens</div>
  <h1><span class="clima">Clima</span><span class="lens">Lens</span></h1>
  <p class="cl-lead">Reinsurers are hit by climate change twice. Climate policy makes their investments in
  carbon-heavy companies lose value. Climate change itself makes natural catastrophes more expensive.
  ClimaLens measures both sides of the balance sheet in one number per scenario and asks:
  <b>do the two risks cancel each other out, or is it a double climate trap?</b></p>
</div>
""")
    cards = [
        (ASSETS, "Investments", "Transition risk", "A higher carbon price raises the costs of the companies Munich Re invests in, so their shares and bonds lose value."),
        (NATCAT, "Underwriting", "Physical risk", "Storms, floods and wildfires get worse with warming, so the reinsurer pays more claims."),
        (GREEN, "One number", "% of equity", "Both effects are added up for each NGFS climate scenario and shown as a share of Munich Re's equity."),
    ]
    html_block('<div class="cl-grid">' + "".join(
        f'<div class="cl-card" style="--c:{c}"><div class="cl-eyebrow" style="--c:{c}">{tag}</div><h4>{title}</h4><p>{text}</p></div>'
        for c, tag, title, text in cards) + "</div>")

    section("First result for Munich Re, 2026–2030", GREEN)
    cols = st.columns(len(t))
    for col, r in zip(cols, t.itertuples()):
        col.metric(r.scenario, pct(r.net_pct_equity), help=f"Investments {pct(r.asset_pct_equity)}, nat-cat {pct(r.liability_pct_equity)}",
                   border=True)
    basis = "the base case assumptions" if not changed() else "your changed assumptions"
    html_block(f'<p class="cl-note">Total burden in % of group equity with {basis}.</p>')

    b1, b2, _ = st.columns([1, 1, 2])
    b1.page_link(PAGES["results"], label="See the results", icon=":material/bar_chart:")
    b2.page_link(PAGES["how"], label="How the test works", icon=":material/menu_book:")


def results_page():
    t = results()
    page_header("Results", "Analysis · Munich Re · 2026–2030",
                "Both sides of the balance sheet in % of group equity, for three NGFS climate scenarios.")
    assumption_bar()
    cols = st.columns(len(t))
    for col, r in zip(cols, t.itertuples()):
        with col.container(border=True):
            st.markdown(f"**{r.scenario}**")
            st.caption(f"Carbon price 2030: {r.carbon_price_eur:.0f} EUR/t CO2")
            html_block(f'<div class="cl-big">{pct(r.net_pct_equity)}</div>'
                       f'<span class="cl-sw" style="--c:{ASSETS}"></span>Investments {pct(r.asset_pct_equity)}<br>'
                       f'<span class="cl-sw" style="--c:{NATCAT}"></span>Nat-cat {pct(r.liability_pct_equity)}<div style="height:.5rem"></div>')
    st.plotly_chart(trap_chart(t), config={"displayModeBar": False})

    cp, nz = t.iloc[0], t.iloc[-1]
    if min(cp.net_pct_equity, nz.net_pct_equity) >= 0.75 * max(cp.net_pct_equity, nz.net_pct_equity):
        color = GREEN
        verdict = (f"<b>Partial natural hedge.</b> Each scenario mainly hits one side, so the total stays in a similar "
                   f"range ({pct(cp.net_pct_equity)} to {pct(nz.net_pct_equity)}).")
    else:
        color = NATCAT
        verdict = (f"<b>No natural hedge up to 2030.</b> Under {nz.scenario} the investment loss ({pct(nz.asset_pct_equity)}) "
                   f"is far larger than the extra nat-cat losses in any scenario (at most {pct(t['liability_pct_equity'].max())}). "
                   "Warming up to 2030 is largely locked in, so the physical side differs little between scenarios.")
    html_block(f'<div class="cl-verdict" style="--c:{color}">{verdict}</div>')
    st.write("")
    st.page_link(PAGES["hotspots"], label=f"Where the nat-cat losses come from: largest hotspot {cp.top_hotspot}",
                 icon=":material/public:")

    with st.expander("Show the numbers as a table", icon=":material/table:"):
        show = pd.DataFrame({
            "Scenario": t["scenario"],
            "Carbon price 2030 (EUR/t)": t["carbon_price_eur"].round(0),
            "Investment loss (EUR bn)": (t["asset_loss_eur"] / 1e9).round(2),
            "Extra nat-cat losses (EUR bn)": (t["liability_extra_eur"] / 1e9).round(2),
            "Total (% of equity)": t["net_pct_equity"].round(1),
        })
        st.dataframe(show, hide_index=True)


def industries_page():
    inp = inputs()
    a = assumptions()
    page_header("Industries", "Analysis · investment side",
                "Which industries drive the investment loss? Pick a scenario.", ASSETS, VIOLET)
    assumption_bar()
    names = [p[0].name for p in inp.pairs]
    choice = st.segmented_control("Scenario", names, default=names[-1], key="sector_scenario", required=True)
    sc = inp.pairs[names.index(choice)][0]
    res = run_sector_stress(inp.portfolio, sc, munichre.BASE_PRICE_EUR, pass_through=a["pass_through"],
                            ev_ebitda_multiple=a["ev_ebitda_multiple"], debt_loss_factor=a["debt_loss_factor"])
    res["emissions"] = res["scope1_financed_tco2e"] + res["scope2_financed_tco2e"]
    g = res.groupby("sector_en")[["loss_eur", "carrying_amount_meur", "emissions"]].sum().reset_index()
    g["name"] = g["sector_en"].replace(SECTOR_NAMES)
    g["loss_share"] = g["loss_eur"] / (g["carrying_amount_meur"] * 1e6) * 100
    total = g["loss_eur"].sum()
    st.caption(f"Investment loss {bn(total)} at {sc.carbon_price_eur:.0f} EUR/t CO2 · equity, loans and bonds together")

    top = g.sort_values("loss_eur", ascending=False).head(10).iloc[::-1]
    fig = go.Figure(go.Bar(
        y=top["name"], x=top["loss_eur"] / 1e6, orientation="h", marker_color=ASSETS,
        text=[f"EUR {v / 1e6:,.0f} m ({s:.0f} %)" for v, s in zip(top["loss_eur"], top["loss_share"])],
        textposition="outside", cliponaxis=False,
        customdata=list(zip(top["carrying_amount_meur"] / 1e3, top["emissions"] / 1e3)),
        hovertemplate="<b>%{y}</b><br>Loss: EUR %{x:,.0f} m<br>Invested: EUR %{customdata[0]:.1f} bn"
                      "<br>Financed emissions: %{customdata[1]:,.0f} kt CO2e<extra></extra>"))
    fig.update_layout(height=470, margin=dict(l=10, r=150, t=10, b=10), xaxis_title="Investment loss, EUR m")
    st.plotly_chart(fig, config={"displayModeBar": False})
    html_block('<p class="cl-note">In brackets: share of the amount invested in that industry that is lost. '
               'Source: Munich Re annual report 2025, pp. 115–117 (financed Scope 1+2 emissions and carrying amounts per GICS industry).</p>')

    with st.expander("Split by asset class", icon=":material/pie_chart:"):
        split = res.groupby("asset_class")[["loss_eur", "carrying_amount_meur", "emissions"]].sum()
        split = pd.DataFrame({
            "Invested (EUR bn)": (split["carrying_amount_meur"] / 1e3).round(1),
            "Financed emissions (kt CO2e)": (split["emissions"] / 1e3).round(0),
            "Loss (EUR m)": (split["loss_eur"] / 1e6).round(0),
        }).rename(index=str.capitalize)
        st.dataframe(split)


YEARS = list(range(2026, 2051))
QUAKE = dict(lat=34.6, lon=-117.0, text="Earthquake California")
LABEL_POS = {"Winter storms Europe": "middle left", "Floods Germany": "bottom center", "Hurricanes North America": "bottom center"}


def hotspot_trace(h: pd.DataFrame, size_ref_eur: float) -> go.Scattergeo:
    rise = (h["factor_year"] - 1) * 100
    return go.Scattergeo(
        lat=h["lat"], lon=h["lon"], mode="markers+text", text=h["hotspot"], showlegend=False,
        textposition=[LABEL_POS.get(x, "top center") for x in h["hotspot"]], textfont=dict(size=13),
        marker=dict(size=h["extra_year_eur"] / 1e6, sizemode="area", sizeref=2 * size_ref_eur / 1e6 / 90 ** 2, sizemin=10,
                    color=rise, cmin=0, cmax=100, opacity=.9,
                    colorscale=[[0, "#fbd5bf"], [0.5, "#f08a5d"], [1, "#b5361c"]],
                    line=dict(width=1.5, color="rgba(255,255,255,.85)"),
                    colorbar=dict(title=dict(text="Losses vs 2025", side="top"), orientation="h", x=.5, xanchor="center",
                                  y=-.02, yanchor="top", len=.4, thickness=10, outlinewidth=0,
                                  tickvals=[0, 50, 100], ticktext=["+0 %", "+50 %", "≥+100 %"])),
        customdata=list(zip(h["peril"], h["var_mid_meur"], h["weight"] * 100, rise, h["extra_year_eur"] / 1e6)),
        hovertemplate="<b>%{text}</b> · %{customdata[0]}<br>Munich Re 1-in-200 VaR: EUR %{customdata[1]:,.0f} m "
                      "(%{customdata[2]:.0f} % weight)<br>Losses vs 2025: +%{customdata[3]:.1f} %"
                      "<br>Extra loss this year: EUR %{customdata[4]:,.0f} m<extra></extra>")


def hotspot_map(by_year: dict[int, pd.DataFrame], size_ref_eur: float, start_year: int = 2030) -> go.Figure:
    """Map with one animation frame per year. The year slider and the play button run in the browser,
    so moving through the years is smooth and does not reload the page."""
    fig = go.Figure()
    fig.add_scattergeo(lat=[QUAKE["lat"]], lon=[QUAKE["lon"]], mode="markers", showlegend=False,
                       marker=dict(size=13, symbol="diamond", color="rgba(128,140,155,.45)",
                                   line=dict(width=1, color="rgba(128,140,155,.9)")),
                       hovertemplate="<b>Earthquake California</b><br>Not driven by the climate,<br>"
                                     "so not part of the climate stress test<extra></extra>")
    fig.add_trace(hotspot_trace(by_year[start_year], size_ref_eur))
    fig.frames = [go.Frame(name=str(y), data=[hotspot_trace(h, size_ref_eur)], traces=[1]) for y, h in by_year.items()]

    def go_to(name, duration=0):
        return [name, dict(mode="immediate", frame=dict(duration=duration, redraw=True), transition=dict(duration=0))]

    fig.update_layout(
        height=640, margin=dict(l=0, r=0, t=86, b=56),
        sliders=[dict(active=YEARS.index(start_year), x=.17, len=.81, y=1.0, yanchor="bottom", pad=dict(t=0, b=10),
                      currentvalue=dict(prefix="Year ", font=dict(size=15), xanchor="left"),
                      ticklen=4, font=dict(size=9), bgcolor="rgba(128,140,155,.25)", bordercolor="rgba(0,0,0,0)",
                      activebgcolor="#eb6834",
                      steps=[dict(method="animate", label=str(y),
                                  args=go_to([str(y)])) for y in YEARS])],
        updatemenus=[dict(type="buttons", showactive=False, direction="left", x=0, y=1.0, xanchor="left",
                          yanchor="bottom", pad=dict(t=0, b=14, r=6), bgcolor="rgba(128,140,155,.15)",
                          bordercolor="rgba(128,140,155,.4)", font=dict(size=13),
                          buttons=[dict(label="▶ Play", method="animate",
                                        args=[None, dict(mode="immediate", fromcurrent=True,
                                                         frame=dict(duration=380, redraw=True), transition=dict(duration=0))]),
                                   dict(label="❚❚", method="animate", args=[[None], dict(mode="immediate",
                                        frame=dict(duration=0, redraw=False), transition=dict(duration=0))])])],
    )
    fig.update_geos(projection_type="natural earth", lonaxis_range=[-126, 30], lataxis_range=[10, 68],
                    showland=True, landcolor="rgba(128,140,155,.22)", showocean=False, showlakes=False,
                    showcountries=True, countrycolor="rgba(128,140,155,.55)", showcoastlines=True,
                    coastlinecolor="rgba(128,140,155,.7)", showframe=False, bgcolor="rgba(0,0,0,0)")
    return fig


def hotspots_page():
    inp = inputs()
    page_header("Hotspots", "Analysis · underwriting side",
                "Where do the extra nat-cat losses come from? The nat-cat result of the stress test, split into the "
                "peril regions where Munich Re carries its largest climate risks.", NATCAT, VIOLET)
    assumption_bar()
    names = [p[0].name for p in inp.pairs]
    choice = st.segmented_control("Scenario", names, default=names[0], key="hotspot_scenario", required=True)
    i = names.index(choice)
    by_year = {y: hotspots(i, y) for y in YEARS}
    h, h50 = by_year[2030], by_year[2050]
    # Fixed bubble scale (largest value in 2050 over all scenarios), so the bubbles grow over the years.
    size_ref = max(hotspots(j, 2050)["extra_year_eur"].max() for j in range(len(names)))

    top = h.sort_values("extra_horizon_eur", ascending=False).iloc[0]
    kpis = [
        (NATCAT, "Extra nat-cat losses in 2030", f"EUR {h['extra_year_eur'].sum() / 1e6:,.0f} m",
         f"after repricing · outlook 2050: EUR {h50['extra_year_eur'].sum() / 1e6:,.0f} m"),
        (VIOLET, "Largest hotspot", html.escape(top["hotspot"]),
         f"{top['extra_horizon_eur'] / h['extra_horizon_eur'].sum() * 100:.0f} % of the extra losses 2026–2030"),
        (ASSETS, "Stress test 2026–2030", pct(h["extra_horizon_eur"].sum() / inp.equity_eur * 100),
         "of equity: the same nat-cat bar as on the Results page"),
    ]
    html_block('<div class="cl-grid" style="--min:200px">' + "".join(
        f'<div class="cl-kpi" style="--c:{c}"><div class="lbl">{label}</div><div class="val" style="font-size:1.6rem">{value}</div>'
        f'<div class="sub">{sub}</div></div>' for c, label, value, sub in kpis) + "</div>")

    st.plotly_chart(hotspot_map(by_year, size_ref),
                    config={"displayModeBar": False, "scrollZoom": False, "topojsonURL": "app/static/"})
    html_block('<p class="cl-note">Press ▶ Play or drag the year. Bubble size = extra loss in that year (EUR m). Colour = how '
               'much higher the losses are than in 2025 because of climate change. <b>After 2030 is an outlook:</b> the factors '
               'simply continue their straight line, while the NGFS scenarios drift further apart. Grey diamond: earthquakes '
               'are not driven by the climate, so no climate scenario changes them.</p>')

    section("Ranking: 2030 and outlook 2050", NATCAT)
    r = h.assign(e50=h50["extra_year_eur"], f50=h50["factor_year"]).sort_values("extra_year_eur")
    fig = go.Figure()
    fig.add_bar(y=r["hotspot"], x=r["extra_year_eur"] / 1e6, orientation="h", name="2030", marker_color=NATCAT,
                text=[f"EUR {v / 1e6:,.0f} m" for v in r["extra_year_eur"]], textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>2030: EUR %{x:,.0f} m<extra></extra>")
    fig.add_bar(y=r["hotspot"], x=r["e50"] / 1e6, orientation="h", name="2050 (outlook)", marker_color="#b5361c",
                text=[f"EUR {v / 1e6:,.0f} m · +{(f - 1) * 100:.0f} %" for v, f in zip(r["e50"], r["f50"])],
                textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>2050: EUR %{x:,.0f} m<extra></extra>")
    fig.update_layout(barmode="group", bargap=.3, height=380, margin=dict(l=10, r=150, t=10, b=10),
                      legend=dict(orientation="h", y=1.08, x=0, traceorder="reversed"),
                      xaxis_title="Extra nat-cat loss in the year, EUR m")
    st.plotly_chart(fig, config={"displayModeBar": False})

    section("How the split works", VIOLET)
    steps = [
        ("Weights from Munich Re", "Munich Re reports the 1-in-200-year loss of its five largest climate perils. Their "
         "shares of the total are the weights."),
        ("Different climate effects", "Climate change raises some perils much more than others, e.g. floods in Germany "
         "more than winter storms in Europe. Each hotspot gets its own rise from the literature."),
        ("Same total", "The regional factors are set so that together they give exactly the global factor of each "
         "scenario. The hotspots therefore add up to the nat-cat bar of the stress test."),
    ]
    html_block('<div class="cl-grid">' + "".join(
        f'<div class="cl-card" style="--c:{VIOLET}"><span class="cl-num">{n}</span><h4>{t}</h4><p>{x}</p></div>'
        for n, (t, x) in enumerate(steps, 1)) + "</div>")

    with st.expander("Data and sources", icon=":material/table:"):
        d = inp.hotspots
        st.dataframe(pd.DataFrame({
            "Hotspot": d["hotspot"], "Peril": d["peril"],
            "VaR 1-in-200 (EUR m)": d["var_mid_meur"], "Weight (%)": (d["weight"] * 100).round(1),
            "Climate rise of losses (literature)": (d["uplift"] * 100).round(0).astype(int).astype(str) + " %",
            "Source of the rise": d["uplift_source"], "Status": d["status"],
        }), hide_index=True)
        html_block('<p class="cl-note">Limits: Munich Re does not publish its exposure by country, so the map shows peril '
                   'regions, not exact countries. The VaR describes extreme years, not the average year. Asia and '
                   'Australia (about 20 % of the reinsurance business) are not split out because Munich Re reports no '
                   'peril figures for them.</p>')


def highlight(quote: str, value_t: float) -> str:
    """The report text with the number that matches the hand-collected value marked."""
    spans = sorted((p, m.start(), m.end()) for pattern in (SPACED_NUMBER, NUMBER) for m in pattern.finditer(quote)
                   if (p := match_precision(m.group(), value_t)) is not None)
    if not spans:
        return html.escape(quote)
    _, s, e = spans[0]
    return html.escape(quote[:s]) + f"<mark>{html.escape(quote[s:e])}</mark>" + html.escape(quote[e:])


def data_page():
    tr = trace_results()
    found, total = int(tr["found"].sum()), len(tr)
    companies = list(dict.fromkeys(tr["company"]))
    page_header("Data check", "Method · audit trail",
                "Can the emissions data be trusted? Every hand-collected value is traced back to the text of the "
                "company's sustainability report, like an audit procedure.", GREEN, TEAL)

    rate = found / total * 100
    kpis = [
        (GREEN, "Match rate", f"{rate:.0f} %", f'<div class="cl-bar"><span style="width:{rate:.0f}%"></span></div>'
         f'<div class="sub">{found} of {total} values found in the report text</div>'),
        (ASSETS, "Companies checked", f"{len(companies)}", '<div class="sub">4 values each · 15 more being collected, '
         'about 40 after the midterm</div>'),
        (NATCAT, "Hand-data errors caught", f"{len(ERRORS_CAUGHT)}", '<div class="sub">in the first run, all corrected '
         'since</div>'),
    ]
    html_block('<div class="cl-grid" style="--min:200px">' + "".join(
        f'<div class="cl-kpi" style="--c:{c}"><div class="lbl">{label}</div><div class="val">{value}</div>{extra}</div>'
        for c, label, value, extra in kpis) + "</div>")

    section("Coverage by company", GREEN)
    head = "".join(f"<th>{FIELD_NAMES[f]}</th>" for f in FIELD_NAMES)
    rows = []
    for co in companies:
        sub = tr[tr["company"] == co].set_index("field")
        cells = []
        for f in FIELD_NAMES:
            if f not in sub.index:
                cells.append("<td></td>")
                continue
            r = sub.loc[f]
            status = f"✓ line {int(r.first_line)}" if r.found else "✗ not found"
            cells.append(f'<td><div class="cl-cell {"ok" if r.found else "miss"}"><b>{tonnes(r.gold_tco2e)}</b>'
                         f"<span>{status}</span></div></td>")
        n = int(sub["found"].sum())
        color = GREEN if n == len(sub) else NATCAT
        rows.append(f'<tr><td class="co">{html.escape(co)}</td>{"".join(cells)}'
                    f'<td><span class="cl-score cl-tint" style="--c:{color}">{n}/{len(sub)}</span></td></tr>')
    html_block(f'<div class="cl-scroll"><table class="cl-matrix"><thead><tr><th>Company</th>{head}<th>Found</th></tr></thead>'
               f'<tbody>{"".join(rows)}</tbody></table></div>')

    section("Evidence from the reports", TEAL)
    co = st.segmented_control("Company", companies, default=companies[0], key="evidence_company", required=True)
    cards = []
    for r in tr[tr["company"] == co].itertuples():
        if r.found:
            body = f'<div class="cl-quote">{highlight(r.report_text, r.gold_tco2e)}</div>'
            where, color = f"report text, line {int(r.first_line)}", GREEN
        else:
            body = f'<div class="cl-quote">{NOT_FOUND.get((r.company, r.field), "No matching number on an emissions line.")}</div>'
            where, color = "not found automatically", RED
        cards.append(f'<div class="cl-evi" style="--c:{color}"><div class="hd"><b>{FIELD_NAMES[r.field]}</b>'
                     f'<span>{tonnes(r.gold_tco2e)} CO2e</span><span class="ln">{where}</span></div>{body}</div>')
    html_block('<div class="cl-grid" style="--min:420px">' + "".join(cards) + "</div>")
    html_block('<p class="cl-note" style="margin-top:.6rem">Highlighted: the number in the report that matches the hand-collected value.</p>')

    ai_section(tr)

    section("What the first run caught", NATCAT)
    html_block('<div class="cl-grid">' + "".join(
        f'<div class="cl-card" style="--c:{NATCAT}"><div class="cl-eyebrow" style="--c:{NATCAT}">{html.escape(co)} · {field}</div>'
        f'<p style="margin-top:.4rem"><b>Wrong:</b> {wrong}</p><p style="margin-top:.3rem"><b>Corrected to:</b> {right}</p></div>'
        for co, field, wrong, right in ERRORS_CAUGHT) + "</div>")

    section("How the check works", VIOLET)
    steps = [
        ("Collect blind", "Kjell types each value from the report PDF without AI help, so the test data is not biased."),
        ("Read every number", "Each number in the report is read in German and English format and in t, kt and Mt."),
        ("Match", "A value counts as found if it appears on an emissions line within the rounding of the printed number."),
    ]
    html_block('<div class="cl-grid">' + "".join(
        f'<div class="cl-card" style="--c:{VIOLET}"><span class="cl-num">{i}</span><h4>{title}</h4><p>{text}</p></div>'
        for i, (title, text) in enumerate(steps, 1)) + "</div>")
    html_block('<p class="cl-note" style="margin-top:.8rem">The same idea checks the AI: its quote must stand on the '
               'line it names and contain its number, otherwise the answer counts as made up.</p>')

    with st.expander("All values as a table", icon=":material/table:"):
        show = pd.DataFrame({
            "Company": tr["company"],
            "Value": tr["field"].map(FIELD_NAMES),
            "t CO2e": tr["gold_tco2e"],
            "Found": tr["found"],
            "Line in report": tr["first_line"].astype("Int64"),
            "Report text": tr["report_text"].fillna(""),
        })
        st.dataframe(show, hide_index=True, column_config={
            "t CO2e": st.column_config.NumberColumn(format="%,.1f"),
            "Found": st.column_config.CheckboxColumn(width="small"),
            "Report text": st.column_config.TextColumn(width="large"),
        })
        st.download_button("Download as CSV", tr.to_csv(index=False), file_name="climalens_data_check.csv",
                           mime="text/csv", icon=":material/download:")


def ai_section(tr: pd.DataFrame):
    """The AI reading test: the same values, read by a language model, compared with the gold set."""
    ai, model = llm_results()
    scored = ai[ai["gold_tco2e"].notna()]
    correct, total = int((scored["verdict"] == "correct").sum()), len(scored)
    quotes, answered = int(ai["quote_ok"].sum()), int(ai["quote"].notna().sum())
    found = int(tr["found"].sum())

    section(f"AI reading test · {html.escape(model)}", VIOLET)
    st.markdown("A language model read the same reports and returned each value with its line and a quote. It never saw "
                "the hand-collected values. Code then checked every answer against the report and the gold set.")
    kpis = [
        (VIOLET, "Read correctly by the AI", f"{correct} of {total}",
         f'<div class="cl-bar" style="--c:{VIOLET}"><span style="width:{correct / total * 100:.0f}%"></span></div>'
         f'<div class="sub">automatic check without AI: {found} of {len(tr)}</div>'),
        (GREEN, "Quotes found in the report", f"{quotes} of {answered}",
         '<div class="sub">no made-up numbers: every quote stands on the line the AI named</div>'),
        (NATCAT, "Wrong or missing", f"{total - correct}",
         f'<div class="sub">at {html.escape(", ".join(dict.fromkeys(scored.loc[scored["verdict"] != "correct", "company"])) or "none")}'
         "</div>"),
    ]
    html_block('<div class="cl-grid" style="--min:200px">' + "".join(
        f'<div class="cl-kpi" style="--c:{c}"><div class="lbl">{label}</div><div class="val">{value}</div>{extra}</div>'
        for c, label, value, extra in kpis) + "</div>")

    head = "".join(f"<th>{FIELD_NAMES[f]}</th>" for f in FIELD_NAMES)
    rows = []
    for co in dict.fromkeys(ai["company"]):
        sub = ai[ai["company"] == co].set_index("field")
        cells = []
        for f in FIELD_NAMES:
            if f not in sub.index:
                cells.append("<td></td>")
                continue
            r = sub.loc[f]
            cls, label = AI_VERDICTS[r.verdict]
            value = tonnes(r.llm_tco2e) if pd.notna(r.llm_tco2e) else "–"
            where = f" · line {int(r.line)}" if pd.notna(r.line) else ""
            cells.append(f'<td><div class="cl-cell {cls}"><b>{value}</b><span>{label}{where}</span></div></td>')
        n = int((sub["verdict"] == "correct").sum())
        color = GREEN if n == len(sub) else NATCAT
        rows.append(f'<tr><td class="co">{html.escape(co)}</td>{"".join(cells)}'
                    f'<td><span class="cl-score cl-tint" style="--c:{color}">{n}/{len(sub)}</span></td></tr>')
    html_block(f'<div class="cl-scroll"><table class="cl-matrix"><thead><tr><th>Company</th>{head}<th>Score</th></tr></thead>'
               f'<tbody>{"".join(rows)}</tbody></table></div>')

    for co, note in AI_NOTES.items():
        sub = ai[(ai["company"] == co) & (ai["verdict"] != "correct")]
        if sub.empty:
            continue
        lines = "".join(f"<li>{FIELD_NAMES[r.field]}: AI {tonnes(r.llm_tco2e) if pd.notna(r.llm_tco2e) else 'no answer'}, "
                        f"gold set {tonnes(r.gold_tco2e)}</li>" for r in sub.itertuples())
        html_block(f'<div class="cl-verdict" style="--c:{NATCAT};margin-top:.8rem"><b>{html.escape(co)}.</b> '
                   f'{html.escape(note)}<ul style="margin:.4rem 0 0">{lines}</ul></div>')
    html_block(f'<div class="cl-verdict" style="--c:{VIOLET};margin-top:.8rem"><b>What this means.</b> The AI reads '
               "numbers reliably and shows where it found them, so each value can be checked in seconds. It does not "
               "know which table row the analysis needs: a person has to define that. The AI got SAP's “1 kt” right, the "
               "one value the automatic check could not match.</div>")

    with st.expander("AI answers with quotes", icon=":material/smart_toy:"):
        st.dataframe(pd.DataFrame({
            "Company": ai["company"],
            "Value": ai["field"].map(FIELD_NAMES),
            "AI (t CO2e)": ai["llm_tco2e"],
            "Gold set (t CO2e)": ai["gold_tco2e"],
            "Result": ai["verdict"],
            "Line": ai["line"].astype("Int64"),
            "Quote from the report": ai["quote"].fillna(""),
        }), hide_index=True, column_config={
            "AI (t CO2e)": st.column_config.NumberColumn(format="%,.1f"),
            "Gold set (t CO2e)": st.column_config.NumberColumn(format="%,.1f"),
            "Quote from the report": st.column_config.TextColumn(width="large"),
        })
        st.download_button("Download as CSV", ai.to_csv(index=False), file_name="climalens_ai_reading_test.csv",
                           mime="text/csv", icon=":material/download:", key="ai_csv")


def brief_page():
    t, a, inp = results(), assumptions(), inputs()
    page_header("ORSA climate brief", "Analysis · report",
                "Draft text for the climate section of an Own Risk and Solvency Assessment, written from the current assumptions.",
                GREEN, VIOLET)
    assumption_bar()
    text = brief_text(t, a, inp)
    st.download_button("Download as Word", brief_docx(text, t), file_name="ClimaLens_ORSA_brief.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       icon=":material/download:", type="primary")
    with st.container(border=True):
        html_block(f'<div class="cl-brief">\n\n{text}\n\n</div>')
    html_block('<p class="cl-note">In the finished product a language model writes this text from the same numbers. '
               'The numbers themselves are always computed by code, so every figure can be checked.</p>')


def how_page():
    inp = inputs()
    page_header("How the test works", "Method · step by step",
                "ClimaLens runs a <b>climate stress test</b> for a reinsurer: how much equity would Munich Re lose up to "
                "2030 in three climate scenarios, and do the losses on the two sides of the balance sheet offset each other?")

    section("The five steps", GREEN)
    steps = [
        (GREEN, "Read reports", "A language model reads the sustainability reports of the companies the reinsurer invests in and extracts their emissions.", True),
        (TEAL, "Check values", "Every extracted number is traced back to its line in the report, like an audit procedure.", True),
        (ASSETS, "Investments", "A carbon price stress test computes how much the investments lose in value.", True),
        (NATCAT, "Underwriting", "A factor model computes how much more the reinsurer pays for natural catastrophes.", True),
        (VIOLET, "Write brief", "A language model turns the numbers into a short ORSA text. All numbers come from code.", False),
    ]
    html_block('<div class="cl-grid" style="--min:150px">' + "".join(
        f'<div class="cl-card" style="--c:{c}"><span class="cl-num">{i}</span><h4>{title}</h4><p>{text}</p>'
        f'<span class="cl-badge {"live" if live else "next"}">{"Working" if live else "Next step"}</span></div>'
        for i, (c, title, text, live) in enumerate(steps, 1)) + "</div>")
    ai, model = llm_results()
    scored = ai[ai["gold_tco2e"].notna()]
    html_block(f'<p class="cl-note" style="margin-top:.6rem">Steps 1–4 work with real data. In the first real run the AI '
               f'({html.escape(model)}) read {int((scored["verdict"] == "correct").sum())} of {len(scored)} values correctly '
               'and made none up. Step 5 still writes the brief from a template.</p>')
    st.page_link(PAGES["data"], label="See the AI reading test", icon=":material/fact_check:")

    section("Investments: the carbon price shock", ASSETS)
    st.markdown("If carbon gets more expensive, a company pays more for every tonne it emits. The part it cannot pass on "
                "to customers lowers its earnings, and lower earnings mean a lower company value. Munich Re owns a share "
                "of each company, so it loses the same share of that value:")
    st.latex(r"\text{loss} = \text{financed emissions} \times \Delta\text{carbon price} \times (1 - \text{pass-through}) \times \tfrac{\text{EV}}{\text{EBITDA}}")
    st.markdown("Shares take the full loss. Loans and bonds take only part of it, because lenders lose money only when a "
                "company gets into real trouble. No loss can be larger than the amount invested.")
    html_block(f'<div class="cl-verdict" style="--c:{ASSETS}"><b>Worked example.</b> Munich Re finances 1,000 t CO2e of a '
               "power producer's emissions through its shares. At 234 EUR/t the company pays EUR 234,000 more per year. "
               "It passes on 30 %, so EUR 163,800 hit its earnings. At a valuation of 8 times earnings the company is worth "
               "EUR 1.31 m less, and Munich Re's shares lose exactly that.</div>")

    section("Underwriting: more expensive natural catastrophes", NATCAT)
    st.markdown("The starting point is Munich Re's average net loss from large natural catastrophes, "
                f"{bn(inp.baseline_eur)} a year from 2021 to 2025. In each scenario, a climate factor raises these losses "
                "step by step up to 2030. Part of the extra cost comes back through higher prices, because reinsurance "
                "contracts are renewed every year:")
    st.latex(r"\text{extra loss} = \sum_{t=2026}^{2030} \left[ B \cdot (1+g)^{t-2025} \cdot M_t - B \right] \times (1 - \text{repricing})")
    st.caption("B = yearly baseline loss, g = loss trend, M = climate factor rising linearly to its 2030 value.")

    nat = inp.natcat[["year", "natcat_large_losses_meur"]]
    fig = go.Figure(go.Bar(x=nat["year"].astype(str), y=nat["natcat_large_losses_meur"], marker_color=NATCAT,
                           hovertemplate="%{x}: EUR %{y:,.0f} m<extra></extra>"))
    fig.add_hline(y=inp.baseline_eur / 1e6, line_dash="dot", annotation_text=f"Average {inp.baseline_eur / 1e9:.2f} bn",
                  annotation_position="top left")
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="EUR m")
    st.plotly_chart(fig, config={"displayModeBar": False})
    st.markdown("**Where the losses come from.** Climate change does not raise every peril by the same amount. ClimaLens "
                "splits the nat-cat result into Munich Re's five largest climate perils, weighted by their 1-in-200-year loss "
                "from the annual report, and gives each its own climate rise. Together they add up to the same total.")
    st.page_link(PAGES["hotspots"], label="Open the hotspot map", icon=":material/public:")

    section("The three scenarios", VIOLET)
    sc = inp.scenarios.assign(price_eur=lambda d: (d["carbon_price_2030_usd2010"] * munichre.USD2010_TO_EUR2025).round(0))
    st.dataframe(pd.DataFrame({
        "NGFS scenario": sc["scenario"],
        "Carbon price 2030 (EUR/t)": sc["price_eur"],
        "Nat-cat factor 2030": sc["natcat_multiplier_2030"],
        "Source of the carbon price": sc["carbon_price_source"],
        "Status": sc["status"],
    }), hide_index=True)
    st.markdown("**Current Policies:** no new climate policy, almost no carbon price, more warming. "
                "**NDCs:** countries keep their current climate pledges. "
                "**Net Zero 2050:** strict policy that limits warming to 1.5 °C, with a high carbon price.")

    section("What the model leaves out", TEAL)
    st.markdown("""
- Physical damage to the companies Munich Re invests in (for example a flooded factory).
- Effects after 2030, when the physical side grows much faster under Current Policies.
- Earthquakes, because they are not driven by the climate.
- Sovereign bonds and real estate, which Munich Re does not report by industry.
- The nat-cat factors are derived from a Swiss Re study (+30–63 % weather-related insured losses by 2040), not from a catastrophe model.
""")

    with st.expander("Glossary", icon=":material/dictionary:"):
        st.markdown("""
- **NGFS**: Network for Greening the Financial System, a group of central banks that publishes standard climate scenarios.
- **ORSA**: Own Risk and Solvency Assessment, the yearly risk report every European insurer must write under Solvency II.
- **Financed emissions**: the share of a company's emissions that belongs to an investor, by the PCAF standard.
- **Pass-through**: the part of a cost increase a company can add to its prices.
- **EV/EBITDA**: company value divided by yearly earnings before interest, taxes, depreciation and amortisation.
- **Repricing**: higher reinsurance prices at the yearly renewal of contracts.
""")
    html_block('<p class="cl-note">Sources: Munich Re annual reports 2021–2025; NGFS Phase V (2024/2025); Swiss Re Institute sigma 4/2021 and 1/2025. '
               'Code and data: github.com/BoyensKjell/ClimaLens.</p>')


PAGES = {
    "welcome": st.Page(welcome, title="Welcome", icon=":material/home:", default=True),
    "results": st.Page(results_page, title="Results", icon=":material/bar_chart:", url_path="results"),
    "industries": st.Page(industries_page, title="Industries", icon=":material/factory:", url_path="industries"),
    "hotspots": st.Page(hotspots_page, title="Hotspots", icon=":material/public:", url_path="hotspots"),
    "brief": st.Page(brief_page, title="ORSA brief", icon=":material/description:", url_path="orsa-brief"),
    "how": st.Page(how_page, title="How it works", icon=":material/menu_book:", url_path="how-it-works"),
    "data": st.Page(data_page, title="Data check", icon=":material/fact_check:", url_path="data-check"),
}
SECTIONS = {
    "Start": [PAGES["welcome"]],
    "Analysis": [PAGES["results"], PAGES["industries"], PAGES["hotspots"], PAGES["brief"]],
    "Method": [PAGES["how"], PAGES["data"]],
}

if os.environ.get("CLIMALENS_PAGE"):  # render one page without navigation (used by the tests)
    {"welcome": welcome, "results": results_page, "industries": industries_page, "hotspots": hotspots_page, "data": data_page,
     "brief": brief_page, "how": how_page}[os.environ["CLIMALENS_PAGE"]]()
else:
    page = st.navigation(SECTIONS)
    sidebar_footer()
    page.run()
