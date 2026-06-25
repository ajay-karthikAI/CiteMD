from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from backend.config import load_config
from models.ranker import load_pubmedbert_ranker
from training.dataset import PairDataset, load_jsonl


def compute_metrics(eval_pred):
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1": f1_score(labels, predictions, zero_division=0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune PubMedBERT as a question/abstract relevance ranker.")
    parser.add_argument("--train-file", default="data/weak_ranker_dataset.jsonl")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--eval-ratio", type=float, default=0.2)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--save-total-limit", type=int, default=1)
    args = parser.parse_args()

    from transformers import Trainer, TrainingArguments

    config = load_config()
    output_dir = Path(args.output_dir or config.ranker_model_path)
    examples = load_jsonl(args.train_file)
    if len(examples) < 4:
        raise ValueError("Need at least four labeled examples for a train/eval split.")

    split = max(1, int(len(examples) * (1.0 - args.eval_ratio)))
    train_examples = examples[:split]
    eval_examples = examples[split:]

    tokenizer, model = load_pubmedbert_ranker(config.ranker_base_model, num_labels=2)
    train_dataset = PairDataset(train_examples, tokenizer, max_length=args.max_length)
    eval_dataset = PairDataset(eval_examples, tokenizer, max_length=args.max_length)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        save_total_limit=args.save_total_limit,
        logging_steps=20,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Saved fine-tuned ranker to {output_dir}")


if __name__ == "__main__":
    main()
