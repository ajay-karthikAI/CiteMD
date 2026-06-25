from backend.schemas import Paper, ScoredPaper
from backend.services.ranking import RankingService


def test_ranking_lexical_fallback_orders_relevant_abstract() -> None:
    service = RankingService("does-not-exist", "base")
    papers = [
        ScoredPaper(Paper("1", "Unrelated", "This abstract discusses software testing."), retrieval_score=0.1),
        ScoredPaper(Paper("2", "Pancreatic cancer", "Pancreatic cancer treatment includes chemotherapy."), retrieval_score=0.1),
    ]

    ranked = service.rank("pancreatic cancer treatment", papers)

    assert ranked[0].paper.pmid == "2"
    assert ranked[0].rank_score is not None

