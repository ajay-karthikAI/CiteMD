from __future__ import annotations

import argparse
import json


def run_ragas(dataset_path: str) -> dict[str, float]:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness
    except ImportError as exc:
        raise RuntimeError("Install ragas and datasets to run generation evaluation.") from exc

    with open(dataset_path, "r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    dataset = Dataset.from_list(rows)
    result = evaluate(dataset, metrics=[faithfulness, context_precision, answer_relevancy])
    return dict(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate generated CiteMD answers with RAGAS.")
    parser.add_argument("--dataset", default="data/ragas_eval.jsonl")
    args = parser.parse_args()
    print(json.dumps(run_ragas(args.dataset), indent=2))


if __name__ == "__main__":
    main()

