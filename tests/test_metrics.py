from evaluation.metrics import mean_reciprocal_rank, recall_at_k, retrieval_report


def test_recall_at_k() -> None:
    assert recall_at_k({"a", "b"}, ["c", "a"], 2) == 0.5


def test_mean_reciprocal_rank() -> None:
    qrels = {"q1": {"b"}, "q2": {"x"}}
    ranked = {"q1": ["a", "b"], "q2": ["x"]}
    assert mean_reciprocal_rank(qrels, ranked) == 0.75


def test_retrieval_report() -> None:
    report = retrieval_report({"q": {"1"}}, {"q": ["1", "2"]})
    assert report["recall@5"] == 1.0
    assert report["recall@10"] == 1.0
    assert report["mrr"] == 1.0

