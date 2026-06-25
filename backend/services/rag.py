from __future__ import annotations

import logging

from backend.config import AppConfig
from backend.schemas import Paper, RAGResponse
from backend.services.conflict import EvidenceConflictDetector
from backend.services.generation import GenerationService
from backend.services.pubmed import PubMedClient
from backend.services.ranking import RankingService
from backend.services.retrieval import EmbeddingService, FAISSVectorStore


logger = logging.getLogger(__name__)


class CiteMDAssistant:
    def __init__(
        self,
        config: AppConfig,
        pubmed_client: PubMedClient | None = None,
        embedding_service: EmbeddingService | None = None,
        ranking_service: RankingService | None = None,
        generation_service: GenerationService | None = None,
        conflict_detector: EvidenceConflictDetector | None = None,
    ) -> None:
        self.config = config
        self.pubmed_client = pubmed_client or PubMedClient(config.pubmed_email, config.pubmed_api_key)
        self.embedding_service = embedding_service or EmbeddingService(config.embedding_model)
        self.ranking_service = ranking_service or RankingService(config.ranker_model_path, config.ranker_base_model)
        self.generation_service = generation_service or GenerationService(config.openai_model)
        self.conflict_detector = conflict_detector or EvidenceConflictDetector()

    def answer(
        self,
        query: str,
        pubmed_limit: int | None = None,
        top_k: int | None = None,
        supplemental_papers: list[Paper] | None = None,
    ) -> RAGResponse:
        limit = pubmed_limit or self.config.pubmed_retmax
        retrieve_k = top_k or self.config.top_k_retrieval
        logger.info("Running CiteMD query", extra={"query": query, "limit": limit, "top_k": retrieve_k})

        papers = self.pubmed_client.search_and_fetch(query, limit=limit)
        if supplemental_papers:
            papers.extend(supplemental_papers)
        vector_store = FAISSVectorStore(self.embedding_service, self.config.vector_store_dir)
        vector_store.build(papers)
        retrieved = vector_store.search(query, top_k=retrieve_k)
        ranked = self.ranking_service.rank(query, retrieved)
        context = ranked[: self.config.top_k_context]
        answer, citations, confidence = self.generation_service.generate(query, context)
        conflict_report = self.conflict_detector.detect(context)

        return RAGResponse(
            query=query,
            answer=answer,
            citations=citations,
            supporting_papers=tuple(ranked),
            conflict_report=conflict_report,
            confidence=confidence,
        )
