from __future__ import annotations

from collections import Counter
import hashlib
import logging
import math
import re
from pathlib import Path
from typing import Iterable

import numpy as np

from backend.schemas import Paper, ScoredPaper


logger = logging.getLogger(__name__)
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9-]{1,}")


class EmbeddingService:
    """Sentence Transformer embeddings with a deterministic local fallback."""

    def __init__(self, model_name: str, fallback_dim: int = 384) -> None:
        self.model_name = model_name
        self.fallback_dim = fallback_dim
        self._model: object | None = None
        self._using_fallback = False

    @property
    def using_fallback(self) -> bool:
        return self._using_fallback

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.fallback_dim), dtype=np.float32)
        model = self._load_model()
        if model is None:
            return self._hash_encode(texts)
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(embeddings, dtype=np.float32)

    def _load_model(self) -> object | None:
        if self._model is not None or self._using_fallback:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            logger.info("Loaded sentence transformer model %s", self.model_name)
        except Exception as exc:
            self._using_fallback = True
            logger.warning("Falling back to hash embeddings: %s", exc)
            self._model = None
        return self._model

    def _hash_encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.fallback_dim), dtype=np.float32)
        for row, text in enumerate(texts):
            counts = Counter(token.lower() for token in TOKEN_RE.findall(text))
            for token, count in counts.items():
                digest = hashlib.md5(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], byteorder="big") % self.fallback_dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vectors[row, index] += sign * (1.0 + math.log(count))
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms


class FAISSVectorStore:
    """In-memory FAISS index with a NumPy fallback for small/test environments."""

    def __init__(self, embedding_service: EmbeddingService, persist_dir: str | Path | None = None) -> None:
        self.embedding_service = embedding_service
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.papers: list[Paper] = []
        self.embeddings: np.ndarray | None = None
        self.index: object | None = None

    def build(self, papers: Iterable[Paper]) -> None:
        self.papers = list(papers)
        texts = [paper.text for paper in self.papers]
        self.embeddings = self.embedding_service.encode(texts)
        if self.embeddings.size == 0:
            self.index = None
            return
        try:
            import faiss

            dimension = int(self.embeddings.shape[1])
            index = faiss.IndexFlatIP(dimension)
            index.add(self.embeddings)
            self.index = index
            logger.info("Built FAISS index", extra={"papers": len(self.papers), "dimension": dimension})
        except Exception as exc:
            self.index = None
            logger.warning("FAISS unavailable; using NumPy search: %s", exc)

    def search(self, query: str, top_k: int = 10) -> list[ScoredPaper]:
        if self.embeddings is None or not self.papers:
            return []
        query_embedding = self.embedding_service.encode([query])
        if self.index is not None:
            distances, indices = self.index.search(query_embedding, min(top_k, len(self.papers)))
            pairs = zip(indices[0].tolist(), distances[0].tolist(), strict=False)
        else:
            scores = np.dot(self.embeddings, query_embedding[0])
            ranked_indices = np.argsort(scores)[::-1][:top_k]
            pairs = ((int(index), float(scores[index])) for index in ranked_indices)
        results: list[ScoredPaper] = []
        for index, score in pairs:
            if index < 0:
                continue
            results.append(ScoredPaper(paper=self.papers[index], retrieval_score=float(score)))
        return results

