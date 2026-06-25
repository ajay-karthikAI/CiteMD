from __future__ import annotations

from functools import lru_cache
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import load_config
from backend.logging_config import configure_logging
from backend.schemas import Paper, RAGResponse
from backend.services.rag import CiteMDAssistant


logger = logging.getLogger(__name__)


class PageContext(BaseModel):
    source: str = Field(default="Browser", max_length=80)
    title: str = Field(default="", max_length=500)
    url: str = Field(default="", max_length=1200)
    text: str = Field(default="", max_length=12000)


class AnswerRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    pubmed_limit: int = Field(default=100, ge=1, le=100)
    top_k: int = Field(default=20, ge=1, le=30)
    page_context: list[PageContext] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str


app = FastAPI(title="CiteMD API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_assistant() -> CiteMDAssistant:
    config = load_config()
    configure_logging(config.log_level)
    return CiteMDAssistant(config)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="citemd-api")


@app.post("/api/answer")
def answer(request: AnswerRequest) -> dict:
    try:
        response = get_assistant().answer(
            request.query.strip(),
            pubmed_limit=request.pubmed_limit,
            top_k=request.top_k,
            supplemental_papers=page_context_to_papers(request.page_context),
        )
    except Exception as exc:
        logger.exception("CiteMD API query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return serialize_response(response)


def serialize_response(response: RAGResponse) -> dict:
    return {
        "query": response.query,
        "answer": response.answer,
        "confidence": response.confidence,
        "conflict": {
            "conflicting": response.conflict_report.conflicting,
            "summary": response.conflict_report.summary,
            "supporting_pmids": list(response.conflict_report.supporting_pmids),
            "opposing_pmids": list(response.conflict_report.opposing_pmids),
        },
        "citations": [
            {
                "pmid": citation.pmid,
                "title": citation.title,
                "url": citation.url,
                "score": citation.score,
                "source": citation.source,
            }
            for citation in response.citations
        ],
        "papers": [
            {
                "pmid": item.paper.pmid,
                "title": item.paper.title,
                "abstract": item.paper.abstract,
                "journal": item.paper.journal,
                "published": item.paper.published,
                "url": item.paper.url,
                "retrieval_score": item.retrieval_score,
                "rank_score": item.rank_score,
                "confidence": item.confidence,
                "source": item.paper.source,
            }
            for item in response.supporting_papers
        ],
    }


def page_context_to_papers(contexts: list[PageContext]) -> list[Paper]:
    papers: list[Paper] = []
    for index, context in enumerate(contexts, start=1):
        text = " ".join(context.text.split())
        title = " ".join(context.title.split()) or f"{context.source} context {index}"
        if len(text) < 40:
            continue
        source = context.source.strip() or "Browser"
        papers.append(
            Paper(
                pmid=str(index),
                title=title,
                abstract=text[:9000],
                journal=source,
                source=source,
                source_id=str(index),
                external_url=context.url or None,
            )
        )
    return papers


def main() -> None:
    import uvicorn

    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
