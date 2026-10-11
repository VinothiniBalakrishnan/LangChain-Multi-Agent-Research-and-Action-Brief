"""Single-page consulting dashboard."""

import streamlit as st

from MAS_LangChain import EXAMPLE_QUESTION, WorkflowError, missing_keys, run_workflow

st.set_page_config(page_title="Research & Action Brief", page_icon="🔎", layout="wide")
st.markdown("""
<style>
    .block-container {max-width: 1120px; padding-top: 2.7rem;}
    h1 {letter-spacing: -0.04em;}
    [data-testid="stMetric"] {background: #eef3f6; padding: 16px; border-radius: 12px;}
    [data-testid="stMetricLabel"] {color: #44566b;}
    [data-testid="stMetricValue"] {color: #16324f; font-size: 1.25rem;}
    .eyebrow {color: #387c76; letter-spacing: .16em; font-size: .78rem; font-weight: 700;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="eyebrow">RESEARCH DESK / BUSINESS INTELLIGENCE</p>', unsafe_allow_html=True)
st.title("From business question to action brief.")
st.write("Explore the evidence, understand the risks, and find your next move.")

for col, label, value in zip(st.columns(4), ["01 / DISCOVER", "02 / RESEARCH", "03 / ANALYZE", "04 / ACT"],
                             ["Search the web", "Gather evidence", "Find implications", "Plan next steps"]):
    col.metric(label, value)
st.write("")

try:
    missing = missing_keys()
except Exception:
    missing = ["GEMINI_API_KEY", "SERP_API_KEY"]
    st.error("Secrets could not be read. Check that .streamlit/secrets.toml contains valid TOML.")

if missing:
    st.info("Setup needed: add " + ", ".join(missing) + " to Streamlit secrets or environment variables.")
    with st.expander("API key setup"):
        st.write("Locally, edit `.streamlit/secrets.toml`. On Streamlit Cloud, use App settings → Secrets.")
        st.code('GEMINI_API_KEY = "your-gemini-key"\nSERP_API_KEY = "your-serpapi-key"', language="toml")

with st.form("business_question"):
    question = st.text_area("What would you like to research?", value=EXAMPLE_QUESTION, height=140, max_chars=2000,
                            help="Include the topic, geography, target audience and the decision you need to make.")
    submitted = st.form_submit_button("Generate action brief", type="primary", disabled=bool(missing))

if submitted:
    # Clear an old result so a failed new request can never look like a success.
    st.session_state.pop("brief", None)
    st.session_state.pop("brief_question", None)
    if not question.strip():
        st.warning("Enter a business question before generating a brief.")
    else:
        with st.status("Researching your question…", expanded=True) as status:
            st.write("Searching the web, then running Researcher → Analysis → Operational Actions.")
            try:
                brief = run_workflow(question)
            except WorkflowError as exc:
                status.update(label="The brief could not be completed", state="error", expanded=True)
                st.error(str(exc))
            except Exception:
                status.update(label="The brief could not be completed", state="error", expanded=True)
                st.error("An unexpected configuration error occurred. Check your secrets and try again.")
            else:
                st.session_state.brief = brief
                st.session_state.brief_question = question.strip()
                status.update(label="Your action brief is ready", state="complete", expanded=False)

if "brief" in st.session_state:
    st.divider()
    heading, download = st.columns([3, 1])
    heading.subheader("Your action brief")
    download.download_button("Download brief", data=("# Research & Action Brief\n\n**Question:** "
                              + st.session_state.brief_question + "\n\n" + st.session_state.brief),
                             file_name="research-action-brief.md", mime="text/markdown")
    st.caption("Research question: " + st.session_state.brief_question)
    st.markdown(st.session_state.brief)
else:
    st.subheader("A clear brief for your next decision")
    st.caption("Your results will include an executive summary, key findings, risks, recommendations and source links.")

st.divider()
st.caption("Powered by LangChain · Gemini · SerpAPI | Evidence comes from search snippets; review the linked sources.")
