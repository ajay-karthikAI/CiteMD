from __future__ import annotations

import logging
import math
import os
from pathlib import Path
import re

from backend.config import resolve_path
from backend.schemas import ScoredPaper


logger = logging.getLogger(__name__)
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]{2,}")


class RankingService:
    """Cross-encoder relevance scorer backed by fine-tuned PubMedBERT when present."""

    def __init__(self, model_path: str, base_model_name: str) -> None:
        self.model_path = model_path
        self.base_model_name = base_model_name
        self._tokenizer: object | None = None
        self._model: object | None = None
        self._device: str | None = None
        self._model_attempted = False

    @property
    def using_transformer(self) -> bool:
        return self._model is not None

    def rank(self, question: str, papers: list[ScoredPaper]) -> list[ScoredPaper]:
        if not papers:
            return []
        scores = self._score_transformer(question, papers)
        if scores is None:
            scores = [self._score_lexical(question, item.paper.title + " " + item.paper.abstract) for item in papers]
        reranked = [
            ScoredPaper(paper=item.paper, retrieval_score=item.retrieval_score, rank_score=float(score))
            for item, score in zip(papers, scores, strict=False)
        ]
        return sorted(reranked, key=lambda item: item.confidence, reverse=True)

    def _score_transformer(self, question: str, papers: list[ScoredPaper]) -> list[float] | None:
        if not self._load_model():
            return None
        try:
            import torch
        except ImportError:
            return None

        assert self._tokenizer is not None
        assert self._model is not None
        abstracts = [item.paper.abstract for item in papers]
        encoded = self._tokenizer(
            [question] * len(abstracts),
            abstracts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = self._model(**encoded).logits
            if logits.shape[-1] == 1:
                probs = torch.sigmoid(logits.squeeze(-1))
            else:
                probs = torch.softmax(logits, dim=-1)[:, 1]
        return probs.detach().cpu().tolist()

    def _load_model(self) -> bool:
        if self._model_attempted:
            return self._model is not None
        self._model_attempted = True
        model_dir = resolve_path(self.model_path)
        allow_untrained = os.getenv("CITEMD_ALLOW_UNTRAINED_RANKER", "false").lower() == "true"
        source = model_dir if model_dir.exists() else self.base_model_name if allow_untrained else None
        if source is None:
            logger.info("Fine-tuned ranker not found; using lexical relevance fallback")
            return False
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tokenizer = AutoTokenizer.from_pretrained(str(source))
            self._model = AutoModelForSequenceClassification.from_pretrained(str(source), num_labels=2)
            self._model.to(self._device)
            self._model.eval()
            logger.info("Loaded PubMedBERT ranker from %s", source)
            return True
        except Exception as exc:
            logger.warning("Could not load PubMedBERT ranker; using fallback: %s", exc)
            self._tokenizer = None
            self._model = None
            return False

    def _score_lexical(self, question: str, document: str) -> float:
        q_tokens = set(token.lower() for token in TOKEN_RE.findall(question))
        d_tokens = set(token.lower() for token in TOKEN_RE.findall(document))
        if not q_tokens or not d_tokens:
            return 0.0
        overlap = len(q_tokens & d_tokens) / len(q_tokens)
        coverage = len(q_tokens & d_tokens) / math.sqrt(len(d_tokens))
        return min(1.0, 0.85 * overlap + 0.15 * coverage)

