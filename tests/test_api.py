from backend.api import PageContext, page_context_to_papers, serialize_response
from backend.schemas import Citation, ConflictReport, Paper, RAGResponse, ScoredPaper


def test_serialize_response_for_extension_api() -> None:
    paper = Paper("123", "Test paper", "Abstract", journal="Journal", published="2026")
    response = RAGResponse(
        query="test",
        answer="answer [PMID:123]",
        citations=(Citation("123", "Test paper", paper.url, 0.91),),
        supporting_papers=(ScoredPaper(paper, retrieval_score=0.8, rank_score=0.91),),
        conflict_report=ConflictReport(False, "No conflict."),
        confidence=0.91,
    )

    payload = serialize_response(response)

    assert payload["confidence"] == 0.91
    assert payload["citations"][0]["pmid"] == "123"
    assert payload["citations"][0]["source"] == "PubMed"
    assert payload["papers"][0]["rank_score"] == 0.91


def test_page_context_to_papers_preserves_google_scholar_source() -> None:
    papers = page_context_to_papers(
        [
            PageContext(
                source="Google Scholar",
                title="Scholar results for pancreatic cancer",
                url="https://scholar.google.com/scholar?q=pancreatic+cancer",
                text="A visible Google Scholar result snippet about pancreatic cancer therapy and biomarkers.",
            )
        ]
    )

    assert papers[0].source == "Google Scholar"
    assert papers[0].source_id == "1"
    assert papers[0].url == "https://scholar.google.com/scholar?q=pancreatic+cancer"
