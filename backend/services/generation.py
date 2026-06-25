from __future__ import annotations

import logging
import os

from backend.schemas import Citation, ScoredPaper


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are CiteMD, a biomedical research assistant.
Answer only from the supplied evidence context. Use concise scientific language.
Use the exact citation IDs supplied in context, such as [PMID:123456] or [Google Scholar:1]. If evidence is limited, say so.
Prefer direct synthesis over broad background."""


ANSWER_STYLE_GUIDE = """Use this answer style:
- Start with one concise thesis sentence.
- Then write 4-7 bullets. Each bullet must start exactly like this: - **Surgery**: ...
- Use bold key development labels such as **Surgery**, **Chemotherapy**, **Targeted Therapies**, **Immunotherapy**, **Radiotherapy**, **Biomarkers**, or **Combination Strategies**.
- Keep each bullet to 1-3 sentences.
- Use technical biomedical language, but avoid rambling, broad background, and layperson simplification.
- Do not use nested bullets.
- End with one short bottom-line sentence only if it adds useful synthesis.
- Every factual claim about a source must carry the exact citation ID supplied in context.

Template:
One-sentence synthesis.
- **Surgery**: Evidence and implication [PMID:123456].
- **Targeted Therapies**: Evidence and implication [PMID:123456].
- **Immunotherapy**: Evidence and implication [Google Scholar:1]."""


class GenerationService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def generate(self, question: str, papers: list[ScoredPaper]) -> tuple[str, tuple[Citation, ...], float]:
        citations = tuple(
            Citation(
                pmid=item.paper.pmid,
                title=item.paper.title,
                url=item.paper.url,
                score=round(item.confidence, 4),
                source=item.paper.source,
            )
            for item in papers
        )
        if not papers:
            return (
                "I could not find PubMed abstracts for this question. Try a narrower biomedical query.",
                citations,
                0.0,
            )

        llm_answer = self._generate_with_langchain(question, papers)
        if llm_answer:
            return llm_answer, citations, self._mean_confidence(papers)

        return self._extractive_answer(question, papers), citations, self._mean_confidence(papers)

    def _generate_with_langchain(self, question: str, papers: list[ScoredPaper]) -> str | None:
        if not os.getenv("OPENAI_API_KEY"):
            logger.info("OPENAI_API_KEY not set; using extractive answer fallback")
            return None
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            logger.warning("LangChain OpenAI packages unavailable; using fallback: %s", exc)
            return None

        context = self._format_context(papers)
        prompt = (
            f"Question: {question}\n\n"
            f"Evidence context:\n{context}\n\n"
            f"{ANSWER_STYLE_GUIDE}"
        )
        try:
            llm = ChatOpenAI(model=self.model_name, temperature=0.0)
            response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
            return str(response.content).strip()
        except Exception as exc:
            logger.warning("LLM generation failed; using fallback: %s", exc)
            return None

    def _extractive_answer(self, question: str, papers: list[ScoredPaper]) -> str:
        leading = papers[: min(5, len(papers))]
        lines = [
            "OpenAI generation is not configured, so CiteMD is showing an extractive evidence summary.",
            f"Question: {question}",
            "",
            "Most relevant PubMed findings:",
        ]
        for item in leading:
            sentence = _first_sentence(item.paper.abstract)
            lines.append(f"- **Evidence**: {sentence} {_citation_marker(item.paper)}")
        lines.append("")
        lines.append("Use the supporting papers table to inspect abstracts, journals, and scores.")
        return "\n".join(lines)

    def _format_context(self, papers: list[ScoredPaper]) -> str:
        chunks = []
        for index, item in enumerate(papers, start=1):
            paper = item.paper
            chunks.append(
                f"{index}. Citation ID: {_citation_marker(paper)}\n"
                f"Source: {paper.source}\n"
                f"Title: {paper.title}\n"
                f"Journal: {paper.journal}\n"
                f"Year: {paper.published}\n"
                f"Rank score: {item.confidence:.4f}\n"
                f"Abstract: {paper.abstract}"
            )
        return "\n\n".join(chunks)

    def _mean_confidence(self, papers: list[ScoredPaper]) -> float:
        if not papers:
            return 0.0
        return round(sum(item.confidence for item in papers) / len(papers), 4)


def _first_sentence(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "No abstract text was available."
    for separator in (". ", "? ", "! "):
        if separator in normalized:
            return normalized.split(separator, maxsplit=1)[0].strip() + separator.strip()
    return normalized[:350]


def _citation_marker(paper) -> str:
    if paper.source == "PubMed":
        return f"[PMID:{paper.pmid}]"
    source_id = paper.source_id or paper.pmid
    return f"[{paper.source}:{source_id}]"
