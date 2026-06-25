from backend.schemas import Paper
from backend.services.retrieval import EmbeddingService, FAISSVectorStore


def test_vector_store_hash_fallback_retrieves_relevant_paper() -> None:
    embedder = EmbeddingService("missing-model")
    embedder._using_fallback = True
    store = FAISSVectorStore(embedder)
    papers = [
        Paper("1", "Pancreatic cancer treatment", "FOLFIRINOX and gemcitabine are used in pancreatic cancer."),
        Paper("2", "Solar cell design", "Photovoltaic materials convert light into electricity."),
    ]

    store.build(papers)
    results = store.search("pancreatic cancer therapy", top_k=1)

    assert results[0].paper.pmid == "1"

