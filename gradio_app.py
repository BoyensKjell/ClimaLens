"""ClimaLens as a small Gradio app: python gradio_app.py

A second front end next to the Streamlit app (app.py), built with Gradio as in the course's
Agentic AI / RAG lab, and ready for Hugging Face Spaces. It shows the stress test results,
the industries, the data check, the AI reading test and the ORSA brief. All numbers come
from the same model as run_munichre.py and app.py (src/climalens/munichre.py).
"""

import html
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import gradio as gr  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

from climalens import munichre  # noqa: E402
from climalens.hotspots import hotspot_losses  # noqa: E402
from climalens.report import brief_docx, brief_text  # noqa: E402
from climalens.sector_stress import run_sector_stress  # noqa: E402

GREEN, ASSETS, NATCAT, VIOLET = "#1f9d63", "#2a78d6", "#eb6834", "#7c5cd6"
FIELD_NAMES = {"scope1_tco2e": "Scope 1", "scope2_market_tco2e": "Scope 2 (market)",
               "scope2_location_tco2e": "Scope 2 (location)", "scope3_tco2e": "Scope 3"}
SECTOR_NAMES = {"Other (no GICS assignment)": "No industry given in the report",
                "Other GICS industries": "All other industries"}
VERDICTS = {"correct": "✓ correct", "wrong": "✗ other row", "unverified": "✗ quote not found", "missed": "✗ no answer"}
BASE = dict(pass_through=0.3, ev_ebitda_multiple=8.0, debt_loss_factor=0.3, repricing=0.5, trend=0.0)

INPUTS = munichre.load_inputs()
NAMES = [p[0].name for p in INPUTS.pairs]
GOLD = ROOT / "data" / "gold"
TRACE = pd.read_csv(GOLD / "trace_results.csv")
AI = pd.read_csv(GOLD / "llm_results.csv")
AI_MODEL = json.loads((GOLD / "llm_answers.json").read_text())["model"]

CSS = """
.cl-hero h1 { font-size: 2.6rem; font-weight: 800; margin: 0; letter-spacing: -.02em; }
.cl-hero .clima { color: #1f9d63; } .cl-hero .lens { color: #2a78d6; }
.cl-hero p { margin: .3rem 0 0; opacity: .8; max-width: 52rem; }
.cl-cards { display: grid; gap: .8rem; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
.cl-card { border: 1px solid rgba(128,140,155,.3); border-top: 4px solid var(--c); border-radius: 10px; padding: .8rem 1rem; }
.cl-card .lbl { font-size: .8rem; font-weight: 700; opacity: .75; }
.cl-card .val { font-size: 1.9rem; font-weight: 800; line-height: 1.2; }
.cl-card .sub { font-size: .82rem; opacity: .75; }
.cl-verdict { border-left: 6px solid var(--c); padding: .6rem 1rem; border-radius: 0 8px 8px 0;
  background: color-mix(in srgb, var(--c) 9%, transparent); margin-top: .6rem; }
"""


def pct(v: float) -> str:
    return f"{v:.1f} %"


def tonnes(v: float) -> str:
    if pd.isna(v):
        return "–"
    if v >= 1e6:
        return f"{v / 1e6:,.2f} Mt"
    if v >= 1e3:
        return f"{v / 1e3:,.1f} kt"
    return f"{v:,.0f} t"


def cards(items: list[tuple[str, str, str, str]]) -> str:
    return '<div class="cl-cards">' + "".join(
        f'<div class="cl-card" style="--c:{c}"><div class="lbl">{lbl}</div><div class="val">{val}</div>'
        f'<div class="sub">{sub}</div></div>' for c, lbl, val, sub in items) + "</div>"


def verdict(text: str, color: str) -> str:
    return f'<div class="cl-verdict" style="--c:{color}">{text}</div>'


# ---------------------------------------------------------------- model


def results(a: dict) -> pd.DataFrame:
    """The double climate trap table with the top nat-cat hotspot per scenario, as in app.py."""
    t = munichre.trap(INPUTS, trend=a["trend"], repricing=a["repricing"], pass_through=a["pass_through"],
                      ev_ebitda_multiple=a["ev_ebitda_multiple"], debt_loss_factor=a["debt_loss_factor"])
    t["carbon_price_eur"] = [p[0].carbon_price_eur for p in INPUTS.pairs]
    tops = [hotspot_losses(INPUTS.hotspots, p[1], INPUTS.baseline_eur, 2030, a["trend"], a["repricing"])
            .sort_values("extra_horizon_eur", ascending=False) for p in INPUTS.pairs]
    t["top_hotspot"] = [h["hotspot"].iloc[0] for h in tops]
    t["top_hotspot_share"] = [h["extra_horizon_eur"].iloc[0] / h["extra_horizon_eur"].sum() * 100 for h in tops]
    return t


def themed(fig: go.Figure) -> go.Figure:
    """Transparent background and a grey font, so the charts read on the light and the dark theme."""
    grid = "rgba(128,140,155,.25)"
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#8a94a3")
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid)
    return fig


def trap_chart(t: pd.DataFrame) -> go.Figure:
    t = t.iloc[::-1]
    labels = [f"<b>{s}</b><br>{p:.0f} EUR/t CO2" for s, p in zip(t["scenario"], t["carbon_price_eur"])]
    fig = go.Figure()
    fig.add_bar(y=labels, x=t["asset_pct_equity"], orientation="h", name="Investments: loss from carbon price",
                marker_color=ASSETS, hovertemplate="Investments: %{x:.1f} % of equity<extra></extra>")
    fig.add_bar(y=labels, x=t["liability_pct_equity"], orientation="h", name="Underwriting: extra nat-cat losses 2026-2030",
                marker_color=NATCAT, hovertemplate="Nat-cat: %{x:.1f} % of equity<extra></extra>")
    for y, n in zip(labels, t["net_pct_equity"]):
        fig.add_annotation(x=n, y=y, text=f"<b>{n:.1f} %</b>", showarrow=False, xanchor="left", xshift=8, font=dict(size=15))
    fig.update_layout(barmode="stack", bargap=0.45, height=340, margin=dict(l=10, r=40, t=40, b=10),
                      legend=dict(orientation="h", y=1.15, x=0, traceorder="normal"),
                      xaxis=dict(title="% of group equity (EUR 33.4 bn)", ticksuffix=" %",
                                 range=[0, max(t["net_pct_equity"]) * 1.18]))
    return themed(fig)


def industries(a: dict, scenario: str) -> tuple[go.Figure, str]:
    sc = INPUTS.pairs[NAMES.index(scenario)][0]
    res = run_sector_stress(INPUTS.portfolio, sc, munichre.BASE_PRICE_EUR, pass_through=a["pass_through"],
                            ev_ebitda_multiple=a["ev_ebitda_multiple"], debt_loss_factor=a["debt_loss_factor"])
    g = res.groupby("sector_en")[["loss_eur", "carrying_amount_meur"]].sum().reset_index()
    g["name"] = g["sector_en"].replace(SECTOR_NAMES)
    g["share"] = g["loss_eur"] / (g["carrying_amount_meur"] * 1e6) * 100
    top = g.sort_values("loss_eur", ascending=False).head(10).iloc[::-1]
    fig = go.Figure(go.Bar(y=top["name"], x=top["loss_eur"] / 1e6, orientation="h", marker_color=ASSETS,
                           text=[f"EUR {v / 1e6:,.0f} m ({s:.0f} %)" for v, s in zip(top["loss_eur"], top["share"])],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="<b>%{y}</b><br>Loss: EUR %{x:,.0f} m<extra></extra>"))
    fig.update_layout(height=440, margin=dict(l=10, r=150, t=10, b=10), xaxis_title="Investment loss, EUR m")
    themed(fig)
    note = (f"Investment loss **EUR {g['loss_eur'].sum() / 1e9:.2f} bn** at {sc.carbon_price_eur:.0f} EUR/t CO2 "
            "(equity, loans and bonds). In brackets: share of the amount invested in that industry that is lost. "
            "Source: Munich Re annual report 2025, pp. 115–117.")
    return fig, note


def update(pass_through, ev_ebitda_multiple, debt_loss_factor, repricing, trend, scenario):
    """Recompute every output from the slider values."""
    a = dict(pass_through=pass_through, ev_ebitda_multiple=ev_ebitda_multiple, debt_loss_factor=debt_loss_factor,
             repricing=repricing, trend=trend)
    t = results(a)
    head = cards([(GREEN, html.escape(r.scenario), pct(r.net_pct_equity),
                   f"Investments {pct(r.asset_pct_equity)} · Nat-cat {pct(r.liability_pct_equity)}<br>"
                   f"Carbon price 2030: {r.carbon_price_eur:.0f} EUR/t") for r in t.itertuples()])
    cp, nz = t.iloc[0], t.iloc[-1]
    if min(cp.net_pct_equity, nz.net_pct_equity) >= 0.75 * max(cp.net_pct_equity, nz.net_pct_equity):
        head += verdict(f"<b>Partial natural hedge.</b> Each scenario mainly hits one side, so the total stays in a "
                        f"similar range ({pct(cp.net_pct_equity)} to {pct(nz.net_pct_equity)}).", GREEN)
    else:
        head += verdict(f"<b>No natural hedge up to 2030.</b> Under {nz.scenario} the investment loss "
                        f"({pct(nz.asset_pct_equity)}) is far larger than the extra nat-cat losses in any scenario "
                        f"(at most {pct(t['liability_pct_equity'].max())}). Largest nat-cat hotspot: {cp.top_hotspot} "
                        f"({cp.top_hotspot_share:.0f} % under {cp.scenario}).", NATCAT)
    table = pd.DataFrame({
        "Scenario": t["scenario"],
        "Carbon price 2030 (EUR/t)": t["carbon_price_eur"].map("{:.0f}".format),
        "Investment loss (EUR bn)": (t["asset_loss_eur"] / 1e9).map("{:.2f}".format),
        "Extra nat-cat losses (EUR bn)": (t["liability_extra_eur"] / 1e9).map("{:.2f}".format),
        "Total (% of equity)": t["net_pct_equity"].map("{:.1f}".format),
    })
    fig_ind, note_ind = industries(a, scenario)
    text = brief_text(t, a, INPUTS)
    docx = Path(tempfile.mkdtemp()) / "ClimaLens_ORSA_brief.docx"  # one folder per call, so visitors don't share a file
    docx.write_bytes(brief_docx(text, t))
    return head, trap_chart(t), table, fig_ind, note_ind, text, str(docx)


# ---------------------------------------------------------------- data check


def grid(df: pd.DataFrame, cell) -> pd.DataFrame:
    """Company x scope table; cell(row) gives the text for one value."""
    rows = []
    for co in dict.fromkeys(df["company"]):
        sub = df[df["company"] == co].set_index("field")
        rows.append({"Company": co, **{name: cell(sub.loc[f]) if f in sub.index else "" for f, name in FIELD_NAMES.items()}})
    return pd.DataFrame(rows)


def data_check() -> tuple[str, pd.DataFrame]:
    found, total = int(TRACE["found"].sum()), len(TRACE)
    head = cards([
        (GREEN, "Match rate", f"{found / total:.0%}", f"{found} of {total} hand-collected values found in the report text"),
        (ASSETS, "Companies checked", str(TRACE["company"].nunique()), "4 values each, more being collected"),
        (NATCAT, "Hand-data errors caught", "3", "in the first run (SAP Scope 3, BASF rows, Siemens Scope 2), all corrected"),
    ])
    table = grid(TRACE, lambda r: f"{tonnes(r.gold_tco2e)} · " + (f"✓ line {int(r.first_line)}" if r.found else "✗ not found"))
    return head, table


def ai_test() -> tuple[str, pd.DataFrame, pd.DataFrame]:
    scored = AI[AI["gold_tco2e"].notna()]
    correct, total = int((scored["verdict"] == "correct").sum()), len(scored)
    quotes, answered = int(AI["quote_ok"].sum()), int(AI["quote"].notna().sum())
    head = cards([
        (VIOLET, "Read correctly by the AI", f"{correct} of {total}",
         f"automatic check without AI: {int(TRACE['found'].sum())} of {len(TRACE)}"),
        (GREEN, "Quotes found in the report", f"{quotes} of {answered}", "no made-up numbers"),
        (NATCAT, "Wrong or missing", str(total - correct), "all at Allianz"),
    ]) + verdict("<b>Allianz.</b> The AI took the group totals, which include Allianz's real-estate investments. The "
                 "gold set uses the rows “davon Geschäftstätigkeit der Allianz” (own operations only). The numbers were "
                 "read correctly, but from the wrong row.", NATCAT) + verdict(
        "<b>What this means.</b> The AI reads numbers reliably and shows where it found them, so each value can be "
        "checked in seconds. A person still has to define which table row the analysis needs.", VIOLET)
    table = grid(AI, lambda r: f"{tonnes(r.llm_tco2e)} · {VERDICTS[r.verdict]}")
    quotes_df = pd.DataFrame({"Company": AI["company"], "Value": AI["field"].map(FIELD_NAMES),
                              "Result": AI["verdict"].map(VERDICTS), "Line": AI["line"].astype("Int64").astype(str),
                              "Quote from the report": AI["quote"].fillna("")})
    return head, table, quotes_df


# ---------------------------------------------------------------- layout


def build() -> gr.Blocks:
    with gr.Blocks(title="ClimaLens") as demo:
        gr.HTML('<div class="cl-hero"><h1><span class="clima">Clima</span><span class="lens">Lens</span></h1>'
                "<p>Reinsurers are hit by climate change twice: climate policy makes their investments in carbon-heavy "
                "companies lose value, and climate change makes natural catastrophes more expensive. ClimaLens measures "
                "both sides for Munich Re in % of equity per NGFS scenario, 2026–2030. "
                "<b>Do the two risks cancel out, or is it a double climate trap?</b></p></div>")

        with gr.Accordion("Assumptions (change them and every tab recalculates)", open=False):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Investments**")
                    s_pass = gr.Slider(0, 0.8, BASE["pass_through"], step=0.05, label="Carbon cost passed on to customers")
                    s_mult = gr.Slider(4, 14, BASE["ev_ebitda_multiple"], step=0.5, label="Valuation multiple (EV/EBITDA)")
                    s_debt = gr.Slider(0, 1, BASE["debt_loss_factor"], step=0.05, label="Loss share for loans and bonds")
                with gr.Column():
                    gr.Markdown("**Underwriting**")
                    s_rep = gr.Slider(0, 0.9, BASE["repricing"], step=0.05, label="Extra nat-cat losses won back via prices")
                    s_trend = gr.Slider(0, 0.07, BASE["trend"], step=0.005, label="Nat-cat loss trend per year")
                    reset = gr.Button("Reset to base case", size="sm")

        with gr.Tabs():
            with gr.Tab("Results"):
                o_head = gr.HTML()
                o_chart = gr.Plot(show_label=False)
                o_table = gr.Dataframe(label="Numbers", interactive=False)
            with gr.Tab("Industries"):
                scenario = gr.Radio(NAMES, value=NAMES[-1], label="Scenario")
                o_ind = gr.Plot(show_label=False)
                o_ind_note = gr.Markdown()
            with gr.Tab("Data check"):
                d_head, d_table = data_check()
                gr.Markdown("Every hand-collected value is traced back to the text of the company's sustainability "
                            "report, like an audit procedure.")
                gr.HTML(d_head)
                gr.Dataframe(d_table, label="Coverage by company (value · where it was found)", interactive=False)
            with gr.Tab("AI reading test"):
                a_head, a_table, a_quotes = ai_test()
                gr.Markdown(f"A language model (**{AI_MODEL}**) read the same reports and returned each value with its "
                            "line and a quote. It never saw the hand-collected values; code checked every answer.")
                gr.HTML(a_head)
                gr.Dataframe(a_table, label="AI answers by company", interactive=False)
                with gr.Accordion("AI answers with quotes", open=False):
                    gr.Dataframe(a_quotes, interactive=False, wrap=True)
            with gr.Tab("ORSA brief"):
                o_file = gr.File(label="Download as Word")
                o_brief = gr.Markdown()

        sliders = [s_pass, s_mult, s_debt, s_rep, s_trend]
        outputs = [o_head, o_chart, o_table, o_ind, o_ind_note, o_brief, o_file]
        for c in [*sliders, scenario]:
            c.change(update, [*sliders, scenario], outputs)
        reset.click(lambda: [BASE[k] for k in ("pass_through", "ev_ebitda_multiple", "debt_loss_factor", "repricing", "trend")],
                    None, sliders)
        demo.load(update, [*sliders, scenario], outputs)
        gr.Markdown("Kjell Boyens · Sustainability and ESG Data Analytics, NTPU · Main app: "
                    "[climalens.streamlit.app](https://climalens.streamlit.app) · Same Python model as the Streamlit app.")
    return demo


if __name__ == "__main__":
    build().launch(css=CSS, theme=gr.themes.Soft(primary_hue="emerald"))
