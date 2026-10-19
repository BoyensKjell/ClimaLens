"""ClimaLens web app: streamlit run app.py

Pages: welcome, results, industries, data check, ORSA brief, how it works.
All numbers come from the same model as run_munichre.py (src/climalens/munichre.py).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from climalens import munichre  # noqa: E402
from climalens.sector_stress import run_sector_stress  # noqa: E402

st.set_page_config(page_title="ClimaLens", page_icon="🌍", layout="wide")

ASSETS = "#2a78d6"
NATCAT = "#eb6834"
FIELD_NAMES = {"scope1_tco2e": "Scope 1", "scope2_market_tco2e": "Scope 2 (market-based)",
               "scope2_location_tco2e": "Scope 2 (location-based)", "scope3_tco2e": "Scope 3"}
SECTOR_NAMES = {"Other (no GICS assignment)": "No industry given in the report",
                "Other GICS industries": "All other industries"}
BASE = dict(pass_through=0.3, ev_ebitda_multiple=8.0, debt_loss_factor=0.3, repricing=0.5, trend=0.0)

st.markdown("""
<style>
.block-container { padding-top: 2.2rem; max-width: 1150px; }
.cl-hero { padding: 2.2rem 0 1.4rem; }
.cl-eyebrow { font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; opacity: .65; }
.cl-hero h1 { font-size: clamp(2.6rem, 6vw, 4.2rem); line-height: 1.02; margin: .3rem 0 .6rem; padding: 0; letter-spacing: -.02em; }
.cl-hero h1 span { color: #2a78d6; }
.cl-lead { font-size: 1.22rem; max-width: 46rem; opacity: .85; line-height: 1.5; }
.cl-card { border: 1px solid rgba(128,140,155,.28); border-radius: 10px; padding: 1rem 1.1rem; height: 100%; }
.cl-card h4 { margin: 0 0 .35rem; padding: 0; font-size: 1rem; }
.cl-card p { margin: 0; font-size: .93rem; opacity: .85; line-height: 1.45; }
.cl-step { font-size: .75rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; opacity: .55; }
.cl-verdict { border-left: 6px solid #2a78d6; padding: .5rem 0 .5rem 1rem; font-size: 1.02rem; }
.cl-note { font-size: .82rem; opacity: .7; }
.cl-brief { font-family: Georgia, "Source Serif 4", serif; font-size: 1.08rem; line-height: 1.65; max-width: 44rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def inputs():
    return munichre.load_inputs()


@st.cache_data
def trace_results():
    return pd.read_csv(ROOT / "data" / "gold" / "trace_results.csv")


def assumptions() -> dict:
    return {k: st.session_state.get(k, v) for k, v in BASE.items()}


def results() -> pd.DataFrame:
    a = assumptions()
    inp = inputs()
    table = munichre.trap(inp, trend=a["trend"], repricing=a["repricing"], pass_through=a["pass_through"],
                          ev_ebitda_multiple=a["ev_ebitda_multiple"], debt_loss_factor=a["debt_loss_factor"])
    table["carbon_price_eur"] = [p[0].carbon_price_eur for p in inp.pairs]
    return table


def pct(v: float) -> str:
    return f"{v:.1f}\u00a0%"


def bn(v: float) -> str:
    return f"EUR {v / 1e9:.2f} bn"


# ---------------------------------------------------------------- sidebar


def sidebar():
    with st.sidebar:
        st.markdown("### Assumptions")
        st.caption("Change them and every page updates. Base case = the values in the report.")
        st.slider("Carbon cost passed on to customers", 0.0, 0.8, BASE["pass_through"], 0.05, key="pass_through",
                  format="percent", help="Share of the extra carbon cost companies can add to their prices.")
        st.slider("Valuation multiple (EV/EBITDA)", 4.0, 14.0, BASE["ev_ebitda_multiple"], 0.5, key="ev_ebitda_multiple",
                  help="How much company value one euro of extra yearly cost destroys.")
        st.slider("Loss share for loans and bonds", 0.0, 1.0, BASE["debt_loss_factor"], 0.05, key="debt_loss_factor",
                  format="percent", help="Lenders lose less than shareholders. 30 % = they take 30 % of the shareholder loss.")
        st.slider("Extra nat-cat losses won back via prices", 0.0, 0.9, BASE["repricing"], 0.05, key="repricing",
                  format="percent", help="Reinsurers renew most contracts every year and can raise prices.")
        st.slider("Nat-cat loss trend per year", 0.0, 0.07, BASE["trend"], 0.005, key="trend", format="percent",
                  help="0 % = climate effect only. Swiss Re: 5-7 % a year including growth of insured values.")
        if st.button("Reset to base case", use_container_width=True):
            for k in BASE:
                st.session_state.pop(k, None)
            st.rerun()
        st.divider()
        st.caption("Reinsurer: **Munich Re** · Hannover Re follows after the midterm.")


# ---------------------------------------------------------------- charts


def trap_chart(t: pd.DataFrame) -> go.Figure:
    t = t.iloc[::-1]
    labels = [f"<b>{s}</b><br>{p:.0f} EUR/t CO2" for s, p in zip(t["scenario"], t["carbon_price_eur"])]
    fig = go.Figure()
    fig.add_bar(y=labels, x=t["asset_pct_equity"], orientation="h", name="Investments: loss from carbon price",
                marker=dict(color=ASSETS, line=dict(width=2, color="rgba(0,0,0,0)")),
                customdata=t["asset_loss_eur"] / 1e9,
                hovertemplate="Investments: %{x:.1f} % of equity<br>EUR %{customdata:.2f} bn<extra></extra>")
    fig.add_bar(y=labels, x=t["liability_pct_equity"], orientation="h", name="Underwriting: extra nat-cat losses 2026-2030",
                marker=dict(color=NATCAT), customdata=t["liability_extra_eur"] / 1e9,
                hovertemplate="Nat-cat: %{x:.1f} % of equity<br>EUR %{customdata:.2f} bn after repricing<extra></extra>")
    for y, n in zip(labels, t["net_pct_equity"]):
        fig.add_annotation(x=n, y=y, text=f"<b>{n:.1f} %</b>", showarrow=False, xanchor="left", xshift=8, font=dict(size=16))
    fig.update_layout(barmode="stack", bargap=0.45, height=340, margin=dict(l=10, r=40, t=10, b=10),
                      legend=dict(orientation="h", y=1.12, x=0, traceorder="normal"), xaxis=dict(title="% of group equity (EUR 33.4 bn)",
                      ticksuffix=" %", range=[0, max(t["net_pct_equity"]) * 1.18]))
    return fig


# ---------------------------------------------------------------- pages


def welcome():
    t = results()
    st.markdown("""
<div class="cl-hero">
  <div class="cl-eyebrow">Sustainability and ESG Data Analytics · NTPU · Kjell Boyens</div>
  <h1>Clima<span>Lens</span></h1>
  <p class="cl-lead">Reinsurers are hit by climate change twice. Climate policy makes their investments in
  carbon-heavy companies lose value. Climate change itself makes natural catastrophes more expensive.
  ClimaLens measures both sides of the balance sheet in one number per scenario and asks:
  <b>do the two risks cancel each other out, or is it a double climate trap?</b></p>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    cards = [
        ("Investments", "Transition risk", "A higher carbon price raises the costs of the companies Munich Re invests in, so their shares and bonds lose value."),
        ("Underwriting", "Physical risk", "Storms, floods and wildfires get worse with warming, so the reinsurer pays more claims."),
        ("One number", "% of equity", "Both effects are added up for each NGFS climate scenario and shown as a share of Munich Re's equity."),
    ]
    for col, (step, title, text) in zip((c1, c2, c3), cards):
        col.markdown(f'<div class="cl-card"><div class="cl-step">{step}</div><h4>{title}</h4><p>{text}</p></div>',
                     unsafe_allow_html=True)

    st.write("")
    st.markdown("#### First result for Munich Re, 2026–2030")
    cols = st.columns(len(t))
    for col, r in zip(cols, t.itertuples()):
        col.metric(r.scenario, pct(r.net_pct_equity), help=f"Investments {pct(r.asset_pct_equity)}, nat-cat {pct(r.liability_pct_equity)}")
    st.markdown('<p class="cl-note">Total burden in % of group equity with the current assumptions.</p>', unsafe_allow_html=True)

    b1, b2, _ = st.columns([1, 1, 2])
    b1.page_link(PAGES["results"], label="See the results", icon=":material/bar_chart:")
    b2.page_link(PAGES["how"], label="How the test works", icon=":material/menu_book:")


def results_page():
    t = results()
    st.title("Results")
    st.caption("Munich Re · ORSA horizon 2026–2030 · both sides of the balance sheet in % of group equity")
    cols = st.columns(len(t))
    for col, r in zip(cols, t.itertuples()):
        with col.container(border=True):
            st.markdown(f"**{r.scenario}**")
            st.caption(f"Carbon price 2030: {r.carbon_price_eur:.0f} EUR/t CO2")
            st.markdown(f"<span style='font-size:2.1rem;font-weight:600'>{pct(r.net_pct_equity)}</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:{ASSETS}'>■</span> Investments {pct(r.asset_pct_equity)}<br>"
                        f"<span style='color:{NATCAT}'>■</span> Nat-cat {pct(r.liability_pct_equity)}", unsafe_allow_html=True)
    st.plotly_chart(trap_chart(t), use_container_width=True, config={"displayModeBar": False})

    cp, nz = t.iloc[0], t.iloc[-1]
    if min(cp.net_pct_equity, nz.net_pct_equity) >= 0.75 * max(cp.net_pct_equity, nz.net_pct_equity):
        verdict = (f"<b>Partial natural hedge.</b> Each scenario mainly hits one side, so the total stays in a similar "
                   f"range ({pct(cp.net_pct_equity)} to {pct(nz.net_pct_equity)}).")
    else:
        verdict = (f"<b>No natural hedge up to 2030.</b> Under {nz.scenario} the investment loss ({pct(nz.asset_pct_equity)}) "
                   f"is far larger than the extra nat-cat losses in any scenario (at most {pct(t['liability_pct_equity'].max())}). "
                   "Warming up to 2030 is largely locked in, so the physical side differs little between scenarios.")
    st.markdown(f'<div class="cl-verdict">{verdict}</div>', unsafe_allow_html=True)

    with st.expander("Show the numbers as a table"):
        show = pd.DataFrame({
            "Scenario": t["scenario"],
            "Carbon price 2030 (EUR/t)": t["carbon_price_eur"].round(0),
            "Investment loss (EUR bn)": (t["asset_loss_eur"] / 1e9).round(2),
            "Extra nat-cat losses (EUR bn)": (t["liability_extra_eur"] / 1e9).round(2),
            "Total (% of equity)": t["net_pct_equity"].round(1),
        })
        st.dataframe(show, hide_index=True, use_container_width=True)


def industries_page():
    inp = inputs()
    a = assumptions()
    st.title("Industries")
    names = [p[0].name for p in inp.pairs]
    choice = st.segmented_control("Scenario", names, default=names[-1], key="sector_scenario") or names[-1]
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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<p class="cl-note">In brackets: share of the amount invested in that industry that is lost. '
                'Source: Munich Re annual report 2025, pp. 115–117 (financed Scope 1+2 emissions and carrying amounts per GICS industry).</p>',
                unsafe_allow_html=True)

    with st.expander("Split by asset class"):
        split = res.groupby("asset_class")[["loss_eur", "carrying_amount_meur", "emissions"]].sum()
        split = pd.DataFrame({
            "Invested (EUR bn)": (split["carrying_amount_meur"] / 1e3).round(1),
            "Financed emissions (kt CO2e)": (split["emissions"] / 1e3).round(0),
            "Loss (EUR m)": (split["loss_eur"] / 1e6).round(0),
        }).rename(index=str.capitalize)
        st.dataframe(split, use_container_width=True)


def data_page():
    tr = trace_results()
    found = int(tr["found"].sum())
    st.title("Data check")
    st.caption("Can the emissions data be trusted? Each hand-collected value is traced back to the text of the company's report.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Values found in the reports", f"{found} of {len(tr)}")
    c2.metric("Companies checked", tr["company"].nunique(), help="15 more are being collected, about 40 after the midterm.")
    c3.metric("Errors in hand data caught", 3, help="SAP Scope 3, BASF rows, Siemens Scope 2 (first run, corrected since).")
    show = pd.DataFrame({
        "Company": tr["company"],
        "Value": tr["field"].map(FIELD_NAMES),
        "t CO2e": tr["gold_tco2e"],
        "Found": tr["found"].map({True: "✅ found", False: "❌ not found"}),
        "Line in report": tr["first_line"].astype("Int64").astype(str).replace("<NA>", "–"),
        "Report text": tr["report_text"].fillna(""),
    })
    st.dataframe(show, hide_index=True, use_container_width=True, height=560, column_config={
        "t CO2e": st.column_config.NumberColumn(format="%,.1f"),
        "Found": st.column_config.TextColumn(width="small"),
        "Report text": st.column_config.TextColumn(width="large", help="The line of the report where the value was found"),
    })
    st.markdown('<p class="cl-note">The one value not found is SAP Scope 2 (market-based): the report prints it as "1 kt", '
                'too coarse for an automatic match. The same check will later test the values a language model extracts.</p>',
                unsafe_allow_html=True)


def brief_text(t: pd.DataFrame, a: dict, inp) -> str:
    cp, nz = t.iloc[0], t.iloc[-1]
    invested = inp.portfolio["carrying_amount_meur"].sum() / 1e3
    emissions = (inp.portfolio["scope1_financed_tco2e"] + inp.portfolio["scope2_financed_tco2e"]).sum() / 1e6
    return f"""### Scope
This section assesses Munich Re's exposure to climate change over the ORSA horizon 2026–2030 on both sides of the balance sheet. It covers corporate equity, loans and bonds with a carrying amount of EUR {invested:.1f} bn and financed Scope 1 and 2 emissions of {emissions:.1f} Mt CO2e, and the natural catastrophe business with average net large losses of {bn(inp.baseline_eur)} per year (2021–2025).

### Results
The combined burden ranges from {pct(cp.net_pct_equity)} of group equity under {cp.scenario} to {pct(nz.net_pct_equity)} under {nz.scenario}. Under {nz.scenario} a carbon price of about {nz.carbon_price_eur:.0f} EUR/t reduces the value of the investments by {bn(nz.asset_loss_eur)} ({pct(nz.asset_pct_equity)} of equity). Under {cp.scenario}, extra natural catastrophe losses after repricing reach {bn(cp.liability_extra_eur)} ({pct(cp.liability_pct_equity)} of equity) over five years.

### Assessment
Up to 2030 the two risks do not offset each other. Transition risk on the asset side dominates in ambitious policy scenarios, while physical risk grows slowly and differs little between scenarios, because warming up to 2030 is largely locked in. The asset-side risk is concentrated in a few carbon-intensive industries, above all power generation.

### Key assumptions
{a['pass_through']:.0%} of carbon costs passed on to customers; valuation multiple {a['ev_ebitda_multiple']:g}×; loans and bonds take {a['debt_loss_factor']:.0%} of the shareholder loss; {a['repricing']:.0%} of extra nat-cat losses recovered through repricing; nat-cat trend {a['trend']:.1%} per year. Physical damage to investee companies and effects after 2030 are not yet included.
"""


def brief_page():
    t, a, inp = results(), assumptions(), inputs()
    st.title("ORSA climate brief")
    st.caption("Draft text for the climate section of an Own Risk and Solvency Assessment, written from the current assumptions.")
    text = brief_text(t, a, inp)
    st.download_button("Download as text file", text, file_name="climalens_orsa_brief.md", mime="text/markdown",
                       icon=":material/download:")
    with st.container(border=True):
        st.markdown(f'<div class="cl-brief">\n\n{text}\n\n</div>', unsafe_allow_html=True)
    st.markdown('<p class="cl-note">In the finished product a language model writes this text from the same numbers. '
                'The numbers themselves are always computed by code, so every figure can be checked.</p>', unsafe_allow_html=True)


def how_page():
    inp = inputs()
    st.title("How the test works")
    st.markdown("ClimaLens runs a **climate stress test** for a reinsurer: it asks how much equity Munich Re would lose "
                "up to 2030 in three climate scenarios, and whether the losses on the two sides of the balance sheet "
                "offset each other.")

    st.subheader("The five steps")
    steps = [
        ("Step 1", "Read reports", "A language model reads the sustainability reports of the companies the reinsurer invests in and extracts their emissions."),
        ("Step 2", "Check values", "Every extracted number is traced back to its page in the report, like an audit procedure."),
        ("Step 3", "Investments", "A carbon price stress test computes how much the investments lose in value."),
        ("Step 4", "Underwriting", "A factor model computes how much more the reinsurer pays for natural catastrophes."),
        ("Step 5", "Write brief", "A language model turns the numbers into a short ORSA text. All numbers come from code."),
    ]
    cols = st.columns(5)
    for col, (step, title, text) in zip(cols, steps):
        col.markdown(f'<div class="cl-card"><div class="cl-step">{step}</div><h4>{title}</h4><p>{text}</p></div>',
                     unsafe_allow_html=True)
    st.caption("Status: steps 2–4 work with real data. Steps 1 and 5 use a language model and follow once API access is available.")

    st.subheader("Investments: the carbon price shock")
    st.markdown("If carbon gets more expensive, a company pays more for every tonne it emits. The part it cannot pass on "
                "to customers lowers its earnings, and lower earnings mean a lower company value. Munich Re owns a share "
                "of each company, so it loses the same share of that value:")
    st.latex(r"\text{loss} = \text{financed emissions} \times \Delta\text{carbon price} \times (1 - \text{pass-through}) \times \tfrac{\text{EV}}{\text{EBITDA}}")
    st.markdown("Shares take the full loss. Loans and bonds take only part of it, because lenders lose money only when a "
                "company gets into real trouble. No loss can be larger than the amount invested.")
    with st.container(border=True):
        st.markdown("**Worked example.** Munich Re finances 1,000 t CO2e of a power producer's emissions through its shares. "
                    "At 234 EUR/t the company pays EUR 234,000 more per year. It passes on 30 %, so EUR 163,800 hit its earnings. "
                    "At a valuation of 8 times earnings the company is worth EUR 1.31 m less, and Munich Re's shares lose exactly that.")

    st.subheader("Underwriting: more expensive natural catastrophes")
    st.markdown("The starting point is Munich Re's average net loss from large natural catastrophes, "
                f"{bn(inp.baseline_eur)} a year from 2021 to 2025. In each scenario, a climate factor raises these losses "
                "step by step up to 2030. Part of the extra cost comes back through higher prices, because reinsurance "
                "contracts are renewed every year:")
    st.latex(r"\text{extra loss} = \sum_{t=2026}^{2030} \left[ B \cdot (1+g)^{t-2025} \cdot M_t - B \right] \times (1 - \text{repricing})")
    st.caption("B = yearly baseline loss, g = loss trend, M = climate factor rising linearly to its 2030 value.")

    nat = inp.natcat[["year", "natcat_large_losses_meur"]].rename(columns={"year": "Year", "natcat_large_losses_meur": "Net nat-cat large losses (EUR m)"})
    fig = go.Figure(go.Bar(x=nat["Year"].astype(str), y=nat.iloc[:, 1], marker_color=NATCAT,
                           hovertemplate="%{x}: EUR %{y:,.0f} m<extra></extra>"))
    fig.add_hline(y=inp.baseline_eur / 1e6, line_dash="dot", annotation_text=f"Average {inp.baseline_eur / 1e9:.2f} bn",
                  annotation_position="top left")
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="EUR m")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.subheader("The three scenarios")
    sc = inp.scenarios.assign(price_eur=lambda d: (d["carbon_price_2030_usd2010"] * munichre.USD2010_TO_EUR2025).round(0))
    st.dataframe(pd.DataFrame({
        "NGFS scenario": sc["scenario"],
        "Carbon price 2030 (EUR/t)": sc["price_eur"],
        "Nat-cat factor 2030": sc["natcat_multiplier_2030"],
        "Source of the carbon price": sc["carbon_price_source"],
        "Status": sc["status"],
    }), hide_index=True, use_container_width=True)
    st.markdown("**Current Policies:** no new climate policy, almost no carbon price, more warming. "
                "**NDCs:** countries keep their current climate pledges. "
                "**Net Zero 2050:** strict policy that limits warming to 1.5 °C, with a high carbon price.")

    st.subheader("What the model leaves out")
    st.markdown("""
- Physical damage to the companies Munich Re invests in (for example a flooded factory).
- Effects after 2030, when the physical side grows much faster under Current Policies.
- Sovereign bonds and real estate, which Munich Re does not report by industry.
- The nat-cat factors are derived from a Swiss Re study (+30–63 % weather-related insured losses by 2040), not from a catastrophe model.
""")

    with st.expander("Glossary"):
        st.markdown("""
- **NGFS**: Network for Greening the Financial System, a group of central banks that publishes standard climate scenarios.
- **ORSA**: Own Risk and Solvency Assessment, the yearly risk report every European insurer must write under Solvency II.
- **Financed emissions**: the share of a company's emissions that belongs to an investor, by the PCAF standard.
- **Pass-through**: the part of a cost increase a company can add to its prices.
- **EV/EBITDA**: company value divided by yearly earnings before interest, taxes, depreciation and amortisation.
- **Repricing**: higher reinsurance prices at the yearly renewal of contracts.
""")
    st.markdown('<p class="cl-note">Sources: Munich Re annual reports 2021–2025; NGFS Phase V (2024/2025); Swiss Re Institute sigma 4/2021 and 1/2025. '
                'Code and data: github.com/BoyensKjell/ClimaLens.</p>', unsafe_allow_html=True)


PAGES = {
    "welcome": st.Page(welcome, title="Welcome", icon=":material/home:", default=True),
    "results": st.Page(results_page, title="Results", icon=":material/bar_chart:", url_path="results"),
    "industries": st.Page(industries_page, title="Industries", icon=":material/factory:", url_path="industries"),
    "data": st.Page(data_page, title="Data check", icon=":material/fact_check:", url_path="data-check"),
    "brief": st.Page(brief_page, title="ORSA brief", icon=":material/description:", url_path="orsa-brief"),
    "how": st.Page(how_page, title="How it works", icon=":material/menu_book:", url_path="how-it-works"),
}

sidebar()
if os.environ.get("CLIMALENS_PAGE"):  # render one page without navigation (used by the tests)
    {"welcome": welcome, "results": results_page, "industries": industries_page, "data": data_page,
     "brief": brief_page, "how": how_page}[os.environ["CLIMALENS_PAGE"]]()
else:
    st.navigation(list(PAGES.values())).run()
