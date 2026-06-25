from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Paper:
    pmid: str
    title: str
    abstract: str
    journal: str = ""
    published: str = ""
    authors: tuple[str, ...] = field(default_factory=tuple)
    doi: str | None = None
    source: str = "PubMed"
    source_id: str | None = None
    external_url: str | None = None

    @property
    def citation(self) -> str:
        if self.source != "PubMed":
            source_id = f" {self.source_id}" if self.source_id else ""
            return f"{self.title}. {self.source}{source_id}"
        year = f" ({self.published})" if self.published else ""
        journal = f" {self.journal}." if self.journal else ""
        return f"{self.title}{journal}{year} PMID:{self.pmid}"

    @property
    def url(self) -> str:
        if self.external_url:
            return self.external_url
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.abstract}".strip()


@dataclass(frozen=True)
class ScoredPaper:
    paper: Paper
    retrieval_score: float = 0.0
    rank_score: float | None = None

    @property
    def confidence(self) -> float:
        if self.rank_score is not None:
            return self.rank_score
        return self.retrieval_score


@dataclass(frozen=True)
class Citation:
    pmid: str
    title: str
    url: str
    score: float
    source: str = "PubMed"


@dataclass(frozen=True)
class ConflictReport:
    conflicting: bool
    summary: str = ""
    supporting_pmids: tuple[str, ...] = field(default_factory=tuple)
    opposing_pmids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RAGResponse:
    query: str
    answer: str
    citations: tuple[Citation, ...]
    supporting_papers: tuple[ScoredPaper, ...]
    conflict_report: ConflictReport
    confidence: float
