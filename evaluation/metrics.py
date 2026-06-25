from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(relevant_ids: set[str], ranked_ids: Sequence[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    retrieved = set(ranked_ids[:k])
    return len(relevant_ids & retrieved) / len(relevant_ids)


def reciprocal_rank(relevant_ids: set[str], ranked_ids: Sequence[str]) -> float:
    for index, pmid in enumerate(ranked_ids, start=1):
        if pmid in relevant_ids:
            return 1.0 / index
    return 0.0


def mean_reciprocal_rank(qrels: dict[str, set[str]], ranked: dict[str, Sequence[str]]) -> float:
    if not qrels:
        return 0.0
    return sum(reciprocal_rank(qrels[query], ranked.get(query, [])) for query in qrels) / len(qrels)


def retrieval_report(qrels: dict[str, set[str]], ranked: dict[str, Sequence[str]]) -> dict[str, float]:
    if not qrels:
        return {"recall@5": 0.0, "recall@10": 0.0, "mrr": 0.0}
    recall5 = sum(recall_at_k(qrels[query], ranked.get(query, []), 5) for query in qrels) / len(qrels)
    recall10 = sum(recall_at_k(qrels[query], ranked.get(query, []), 10) for query in qrels) / len(qrels)
    return {"recall@5": recall5, "recall@10": recall10, "mrr": mean_reciprocal_rank(qrels, ranked)}

