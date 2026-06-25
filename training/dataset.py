from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PairExample:
    question: str
    abstract: str
    label: int
    pmid: str = ""


def load_jsonl(path: str | Path) -> list[PairExample]:
    examples: list[PairExample] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            examples.append(
                PairExample(
                    question=item["question"],
                    abstract=item["abstract"],
                    label=int(item["label"]),
                    pmid=str(item.get("pmid", "")),
                )
            )
    return examples


def write_jsonl(examples: list[PairExample], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example.__dict__) + "\n")


class PairDataset:
    def __init__(self, examples: list[PairExample], tokenizer: Any, max_length: int = 512) -> None:
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("PyTorch is required to instantiate PairDataset.") from exc

        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self._torch = torch

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        example = self.examples[index]
        encoded = self.tokenizer(
            example.question,
            example.abstract,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = self._torch.tensor(example.label, dtype=self._torch.long)
        return item


def make_dataloader(
    examples: list[PairExample],
    tokenizer: Any,
    batch_size: int = 8,
    shuffle: bool = True,
    max_length: int = 512,
):
    try:
        from torch.utils.data import DataLoader
    except ImportError as exc:
        raise RuntimeError("PyTorch is required to create a DataLoader.") from exc
    return DataLoader(
        PairDataset(examples, tokenizer, max_length=max_length),
        batch_size=batch_size,
        shuffle=shuffle,
    )
