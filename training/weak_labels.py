from __future__ import annotations

import argparse
import random

from backend.config import load_config
from backend.services.pubmed import PubMedClient
from training.dataset import PairExample, write_jsonl


DEFAULT_NEGATIVE_QUERIES = [
    "plant chloroplast photosynthesis",
    "quantum dot solar cells",
    "marine sediment geochemistry",
    "software engineering code review",
]


def build_weak_dataset(
    query: str,
    pubmed_client: PubMedClient,
    positives: int = 50,
    negatives: int = 50,
    negative_queries: list[str] | None = None,
) -> list[PairExample]:
    examples: list[PairExample] = []
    positive_papers = pubmed_client.search_and_fetch(query, limit=positives)
    examples.extend(PairExample(query, paper.abstract, 1, paper.pmid) for paper in positive_papers)

    negative_pool = negative_queries or DEFAULT_NEGATIVE_QUERIES
    negative_count = 0
    attempts = 0
    max_attempts = max(8, len(negative_pool) * 3)
    seen_pmids = {example.pmid for example in examples if example.pmid}
    while negative_count < negatives and attempts < max_attempts:
        attempts += 1
        negative_query = random.choice(negative_pool)
        papers = pubmed_client.search_and_fetch(negative_query, limit=min(25, negatives))
        for paper in papers:
            if paper.pmid in seen_pmids:
                continue
            seen_pmids.add(paper.pmid)
            examples.append(PairExample(query, paper.abstract, 0, paper.pmid))
            negative_count += 1
            if negative_count >= negatives:
                break
    if negative_count == 0:
        raise RuntimeError("Could not collect negative PubMed examples. Try different negative queries.")
    random.shuffle(examples)
    return examples


def main() -> None:
    parser = argparse.ArgumentParser(description="Create weakly supervised PubMedBERT ranking data.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--output", default="data/weak_ranker_dataset.jsonl")
    parser.add_argument("--positives", type=int, default=50)
    parser.add_argument("--negatives", type=int, default=50)
    args = parser.parse_args()

    config = load_config()
    client = PubMedClient(config.pubmed_email, config.pubmed_api_key)
    examples = build_weak_dataset(args.query, client, args.positives, args.negatives)
    write_jsonl(examples, args.output)
    print(f"Wrote {len(examples)} examples to {args.output}")


if __name__ == "__main__":
    main()
