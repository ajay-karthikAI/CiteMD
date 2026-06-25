from backend.schemas import Paper, ScoredPaper
from backend.services.conflict import EvidenceConflictDetector


def test_conflict_detector_finds_opposing_conclusions() -> None:
    papers = [
        ScoredPaper(Paper("1", "Drug X improved survival", "Treatment was effective."), rank_score=0.9),
        ScoredPaper(Paper("2", "Drug X trial", "There was no significant benefit."), rank_score=0.8),
    ]

    report = EvidenceConflictDetector().detect(papers)

    assert report.conflicting is True
    assert report.supporting_pmids == ("1",)
    assert report.opposing_pmids == ("2",)

