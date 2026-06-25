from __future__ import annotations

import argparse
import json

from backend.config import load_config
from backend.services.rag import CiteMDAssistant
from evaluation.metrics import retrieval_report


def load_qrels(path: str) -> dict[str, set[str]]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return {query: set(map(str, pmids)) for query, pmids in raw.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate CiteMD retrieval metrics against PMIDs.")
    parser.add_argument("--qrels", default="data/qrels.json", help="JSON mapping query text to relevant PMID list.")
    parser.add_argument("--pubmed-limit", type=int, default=100)
    args = parser.parse_args()

    config = load_config()
    assistant = CiteMDAssistant(config)
    qrels = load_qrels(args.qrels)
    ranked: dict[str, list[str]] = {}
    for query in qrels:
        response = assistant.answer(query, pubmed_limit=args.pubmed_limit)
        ranked[query] = [item.paper.pmid for item in response.supporting_papers]
    print(json.dumps(retrieval_report(qrels, ranked), indent=2))


if __name__ == "__main__":
    main()

