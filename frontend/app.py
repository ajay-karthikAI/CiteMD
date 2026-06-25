from __future__ import annotations

from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from backend.config import load_config
from backend.logging_config import configure_logging
from backend.schemas import RAGResponse, ScoredPaper
from backend.services.rag import CiteMDAssistant


st.set_page_config(page_title="CiteMD", layout="wide")


def format_percent(value: float | None) -> str:
    return f"{((value or 0.0) * 100):.1f}%"


def inject_dark_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #050807;
            color: #d8fbe8;
        }
        h1, h2, h3, [data-testid="stMetricValue"] {
            color: #31ff9a !important;
            text-shadow: 0 0 12px rgba(49, 255, 154, 0.35);
        }
        [data-testid="stSidebar"] {
            background: #020403;
            border-right: 1px solid rgba(49, 255, 154, 0.24);
        }
        div[data-testid="stAlert"] {
            background: #071a12;
            border: 1px solid rgba(49, 255, 154, 0.38);
            color: #d8fbe8;
            box-shadow: 0 0 18px rgba(49, 255, 154, 0.16);
        }
        .stButton > button, .stLinkButton > a {
            border: 1px solid #31ff9a;
            background: #0ebf6f;
            color: #02130d;
            font-weight: 800;
            box-shadow: 0 0 14px rgba(49, 255, 154, 0.32);
        }
        .stButton > button:hover, .stLinkButton > a:hover {
            border-color: #31ff9a;
            background: #31ff9a;
            color: #02130d;
            box-shadow: 0 0 22px rgba(49, 255, 154, 0.54);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def get_assistant() -> CiteMDAssistant:
    config = load_config()
    configure_logging(config.log_level)
    return CiteMDAssistant(config)


def render_answer(response: RAGResponse) -> None:
    st.subheader("Generated Answer")
    st.markdown(response.answer)
    if response.conflict_report.conflicting:
        st.warning(response.conflict_report.summary)
        st.caption(
            "Supporting PMIDs: "
            + ", ".join(response.conflict_report.supporting_pmids)
            + " | Opposing PMIDs: "
            + ", ".join(response.conflict_report.opposing_pmids)
        )
    else:
        st.info(response.conflict_report.summary)


def render_citations(response: RAGResponse) -> None:
    st.subheader("Supporting Citations")
    for citation in response.citations:
        with st.expander(f"PMID:{citation.pmid} | score {format_percent(citation.score)} | {citation.title}"):
            st.link_button("Open in PubMed", citation.url)


def render_papers(papers: tuple[ScoredPaper, ...]) -> None:
    st.subheader("Top Retrieved Papers")
    rows = [
        {
            "PMID": item.paper.pmid,
            "Title": item.paper.title,
            "Journal": item.paper.journal,
            "Year": item.paper.published,
            "Retrieval": format_percent(item.retrieval_score),
            "Rank": format_percent(item.rank_score) if item.rank_score is not None else None,
            "URL": item.paper.url,
        }
        for item in papers
    ]
    st.dataframe(rows, width="stretch", hide_index=True)
    for item in papers[:10]:
        with st.expander(f"{item.paper.title} | PMID:{item.paper.pmid}"):
            st.write(item.paper.abstract)


def render_eval_dashboard(response: RAGResponse) -> None:
    st.subheader("Evaluation Dashboard")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Papers ranked", len(response.supporting_papers))
    col_b.metric("Answer confidence", format_percent(response.confidence))
    col_c.metric("Citations", len(response.citations))
    col_d.metric("Conflict", "Yes" if response.conflict_report.conflicting else "No")

    st.caption(
        "Offline dashboard metrics are runtime diagnostics. Use evaluation/evaluate_retrieval.py "
        "for Recall@5, Recall@10, and MRR, and evaluation/evaluate_generation.py for RAGAS."
    )


def main() -> None:
    inject_dark_theme()
    st.title("CiteMD")
    st.caption("A PubMed Copilot for literature-grounded biomedical answers.")

    with st.sidebar:
        st.header("Settings")
        pubmed_limit = st.slider("PubMed abstracts", min_value=10, max_value=100, value=100, step=10)
        top_k = st.slider("Retrieved papers", min_value=5, max_value=30, value=20, step=5)
        st.caption("Set PUBMED_EMAIL and OPENAI_API_KEY in your environment for full production mode.")

    default_query = "What are the latest treatments for pancreatic cancer?"
    query = st.text_input("Ask a biomedical research question", value=default_query)
    run = st.button("Search PubMed", type="primary")

    if run and query.strip():
        assistant = get_assistant()
        with st.spinner("Searching PubMed, ranking abstracts, and generating a cited answer..."):
            try:
                st.session_state["response"] = assistant.answer(query.strip(), pubmed_limit=pubmed_limit, top_k=top_k)
            except Exception as exc:
                st.error(str(exc))
                with st.expander("Debug traceback"):
                    st.code(traceback.format_exc())

    response = st.session_state.get("response")
    if response:
        answer_tab, citations_tab, papers_tab, eval_tab = st.tabs(
            ["Answer", "Citations", "Retrieved Papers", "Evaluation"]
        )
        with answer_tab:
            render_answer(response)
        with citations_tab:
            render_citations(response)
        with papers_tab:
            render_papers(response.supporting_papers)
        with eval_tab:
            render_eval_dashboard(response)


if __name__ == "__main__":
    main()
