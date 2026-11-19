"""Personal website of Kjell Boyens (Streamlit, one page).

Run locally:  streamlit run website/app.py
Deploy:       share.streamlit.io -> repo BoyensKjell/ClimaLens, branch main, main file website/app.py

Everything you may want to change (texts, links) sits in the PROFILE block below.
"""

import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# PROFILE: edit texts and links here
# --------------------------------------------------------------------------- #
NAME = "Kjell Boyens"
TAGLINE = "Business student · Finance & sustainability risk · Building with data and AI"
INTRO = (
    "I study business administration with a focus on finance and I am heading towards audit "
    "and consulting. This semester I take *Sustainability and ESG Data Analytics* at National "
    "Taipei University (NTPU). My interest: where climate risk turns into balance-sheet risk, "
    "and whether AI can deliver ESG data that an auditor would sign off on."
)
GITHUB = "https://github.com/BoyensKjell"
GROUP_GITHUB = ""  # e.g. "https://github.com/greenproof-ntpu" once the group account exists
LINKEDIN = "https://www.linkedin.com/in/kjell-boyens-b5b856342"
EMAIL = ""         # optional

CLIMALENS_APP = "https://climalens.streamlit.app"
CLIMALENS_REPO = "https://github.com/BoyensKjell/ClimaLens"
GREENPROOF_APP = "https://greenproof-d9nzwoveamyh7fjkbfattx.streamlit.app/"
GREENPROOF_REPO = "https://github.com/hugoroeske/greenproof"
COURSE = "Sustainability and ESG Data Analytics · Prof. Min-Yuh Day · NTPU · Fall 2026"

KEYWORDS = ["Climate risk", "Reinsurance", "NGFS scenarios", "ESG data quality", "LLM extraction"]

# Stress test result for Munich Re, 2026-2030, in % of equity (ClimaLens, midterm)
SCENARIOS = ["Current Policies", "NDCs", "Net Zero 2050"]
ASSET_SIDE = [0.8, 2.9, 12.3]
NATCAT_SIDE = [1.5, 1.1, 0.7]

# --------------------------------------------------------------------------- #
st.set_page_config(page_title=f"{NAME}", page_icon="🌿", layout="centered")

st.html(
    """
<style>
  .block-container {max-width: 860px; padding-top: 4.5rem;}
  .kb-hero {display:flex; gap:1.4rem; align-items:center; margin-bottom:.6rem;}
  .kb-avatar {flex:0 0 84px; width:84px; min-width:84px; height:84px; border-radius:50%;
              background: linear-gradient(135deg,#16784f,#2a78d6);
              color:#fff; font-weight:800; font-size:2rem;
              display:flex; align-items:center; justify-content:center; letter-spacing:.02em;}
  .kb-name {font-size:2.4rem; font-weight:800; line-height:1.1; margin:0;}
  .kb-tag {opacity:.75; margin-top:.35rem; font-size:1.02rem;}
  .kb-chips {display:flex; flex-wrap:wrap; gap:.45rem; margin:.4rem 0 .2rem 0;}
  .kb-chip {border:1px solid rgba(128,128,128,.35); border-radius:999px;
            padding:.18rem .7rem; font-size:.85rem; opacity:.9;}
  .kb-label {text-transform:uppercase; letter-spacing:.09em; font-size:.75rem;
             font-weight:700; opacity:.6; margin-bottom:.1rem;}
  .kb-muted {opacity:.7; font-size:.92rem;}
  @media (max-width: 600px) {
    .kb-hero {flex-direction:column; align-items:flex-start; gap:.8rem;}
    .kb-name {font-size:2rem;}
    .kb-avatar {flex-basis:64px; width:64px; min-width:64px; height:64px; font-size:1.5rem;}
  }
</style>
"""
)

initials = "".join(part[0] for part in NAME.split()[:2])
chips = "".join(f'<span class="kb-chip">{k}</span>' for k in KEYWORDS)
st.html(
    f"""
<div class="kb-hero">
  <div class="kb-avatar">{initials}</div>
  <div>
    <p class="kb-name">{NAME}</p>
    <div class="kb-tag">{TAGLINE}</div>
  </div>
</div>
<div class="kb-chips">{chips}</div>
"""
)

st.markdown(INTRO)

buttons = [("GitHub", GITHUB, ":material/code:"),
           ("ClimaLens app", CLIMALENS_APP, ":material/public:"),
           ("GreenProof app", GREENPROOF_APP, ":material/eco:")]
if GROUP_GITHUB:
    buttons.append(("Group GitHub", GROUP_GITHUB, ":material/groups:"))
if LINKEDIN:
    buttons.append(("LinkedIn", LINKEDIN, ":material/person:"))
for col, (label, url, icon) in zip(st.columns(len(buttons)), buttons):
    col.link_button(label, url, icon=icon, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------- #
# Project 1: ClimaLens
# --------------------------------------------------------------------------- #
st.html('<div class="kb-label">Individual project</div>')
st.subheader("ClimaLens: the double climate trap of reinsurers")
st.markdown(
    "Reinsurers are hit by climate change twice. Their **investments** lose value when carbon "
    "gets expensive (transition risk), and their **claims** rise when natural catastrophes get "
    "worse (physical risk). Strict climate policy hurts the first side, weak policy the second. "
    "ClimaLens puts both sides into one number per NGFS scenario, in % of equity, with "
    "**Munich Re** as the case study, and writes the result as a short **ORSA climate brief**."
)

m1, m2, m3 = st.columns(3)
m1.metric("Net Zero: loss by 2030", "13.0 %", help="Assets 12.3 % + liabilities 0.7 % of equity")
m1.caption("of Munich Re's equity")
m2.metric("AI reading test", "16 / 20")
m2.caption("values right, 0 invented")
m3.metric("Natural hedge until 2030?", "No")
m3.caption("the asset side dominates")

fig = go.Figure()
fig.add_bar(name="Assets (carbon price)", y=SCENARIOS, x=ASSET_SIDE, orientation="h",
            marker_color="#2a78d6", text=[f"{v:.1f}" for v in ASSET_SIDE], textposition="inside")
fig.add_bar(name="Liabilities (extra nat-cat losses)", y=SCENARIOS, x=NATCAT_SIDE, orientation="h",
            marker_color="#eb6834", text=[f"{v:.1f}" for v in NATCAT_SIDE], textposition="inside")
fig.update_layout(
    barmode="stack", height=230, margin=dict(l=0, r=10, t=10, b=0),
    xaxis_title="Loss 2026-2030, % of Munich Re equity", yaxis=dict(autorange="reversed"),
    legend=dict(orientation="h", y=-0.45, x=0), paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
st.caption("Sources: NGFS Phase V carbon prices, Munich Re annual reports, Swiss Re sigma. "
           "First model version, assumptions are listed in the app.")

with st.expander("How it works and what I tested"):
    st.markdown(
        """
- **Asset side:** carbon-price stress test on Munich Re's sector portfolio with NGFS 2030 prices
  (financed emissions after PCAF).
- **Liability side:** extra natural-catastrophe losses on top of a ~€2.1bn yearly baseline.
- **AI data check:** a language model (Gemini) reads Scope 1-3 emissions from 20 sustainability
  reports. Every value must come with a quote from the report and is compared with a hand-checked
  gold set. Result: 16 of 20 right, none made up. The errors were the right number from the wrong
  row, so a human still has to define *which* figure counts.
- **Output:** a Streamlit app (plus a Gradio version) that downloads the ORSA brief as a Word file.
"""
    )

c1, c2 = st.columns(2)
c1.link_button("Open the ClimaLens app", CLIMALENS_APP, type="primary", use_container_width=True)
c2.link_button("Code on GitHub", CLIMALENS_REPO, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------- #
# Project 2: GreenProof
# --------------------------------------------------------------------------- #
st.html('<div class="kb-label">Group project · team of five</div>')
st.subheader("GreenProof: a greenwashing screener")
st.markdown(
    "GreenProof reads corporate sustainability reports and asks two questions. **Talk:** how "
    "honest are the green claims, measured against the new EU rules on green claims "
    "(Directive 2024/825)? **Evidence:** does the company back them up with climate data "
    "(GRI 305 checklist)? Both scores place a company in a talk-vs-evidence matrix, where "
    "*lots of green talk, little evidence* is flagged as greenwashing risk. Our sample: eight "
    "consumer-electronics firms from the US, Korea, Japan, Taiwan and the EU."
)
g1, g2 = st.columns(2)
g1.link_button("Open the GreenProof app", GREENPROOF_APP, type="primary", use_container_width=True)
g2.link_button("Code on GitHub", GREENPROOF_REPO, use_container_width=True)
st.caption("My part: research framing, company sample and report analysis, slides.")

st.divider()

# --------------------------------------------------------------------------- #
# Skills and contact
# --------------------------------------------------------------------------- #
left, right = st.columns(2)
with left:
    st.html('<div class="kb-label">What I work with</div>')
    st.markdown(
        """
- Finance: risk, valuation, insurance balance sheets
- ESG frameworks: NGFS, PCAF, ESRS/CSRD, GRI, EU green claims
- Python with AI assistance: pandas, Streamlit, Plotly, LLM APIs
- Audit mindset: every number traced back to its source
"""
    )
with right:
    st.html('<div class="kb-label">Next steps</div>')
    st.markdown(
        """
- Final report on ClimaLens (December 2026)
- Hannover Re as second case, larger gold set
- Long term: bachelor thesis on climate risk in reinsurance
"""
    )

contact = [f"[GitHub]({GITHUB})"]
if LINKEDIN:
    contact.append(f"[LinkedIn]({LINKEDIN})")
if EMAIL:
    contact.append(f"[{EMAIL}](mailto:{EMAIL})")
if GROUP_GITHUB:
    contact.append(f"[Group GitHub]({GROUP_GITHUB})")

st.divider()
st.markdown(" · ".join(contact))
st.caption(COURSE)
