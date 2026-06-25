from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppConfig:
    pubmed_email: str = "citemd@example.com"
    pubmed_api_key: str | None = None
    pubmed_retmax: int = 100
    embedding_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    ranker_base_model: str = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"
    ranker_model_path: str = "models/pubmedbert-ranker"
    openai_model: str = "gpt-4o-mini"
    vector_store_dir: str = "data/vector_store"
    top_k_retrieval: int = 20
    top_k_context: int = 8
    log_level: str = "INFO"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_config(config_path: str | Path | None = None) -> AppConfig:
    _load_dotenv()
    path = Path(config_path) if config_path else ROOT_DIR / "config" / "config.yaml"
    raw = _load_yaml(path)
    pubmed = raw.get("pubmed", {})
    models = raw.get("models", {})
    rag = raw.get("rag", {})
    logging = raw.get("logging", {})

    return AppConfig(
        pubmed_email=os.getenv("PUBMED_EMAIL", pubmed.get("email", AppConfig.pubmed_email)),
        pubmed_api_key=os.getenv("PUBMED_API_KEY", pubmed.get("api_key")),
        pubmed_retmax=_env_int("PUBMED_RETMAX", int(pubmed.get("retmax", AppConfig.pubmed_retmax))),
        embedding_model=os.getenv("EMBEDDING_MODEL", models.get("embedding_model", AppConfig.embedding_model)),
        ranker_base_model=os.getenv("RANKER_BASE_MODEL", models.get("ranker_base_model", AppConfig.ranker_base_model)),
        ranker_model_path=os.getenv("RANKER_MODEL_PATH", models.get("ranker_model_path", AppConfig.ranker_model_path)),
        openai_model=os.getenv("OPENAI_MODEL", models.get("openai_model", AppConfig.openai_model)),
        vector_store_dir=os.getenv("VECTOR_STORE_DIR", rag.get("vector_store_dir", AppConfig.vector_store_dir)),
        top_k_retrieval=_env_int("TOP_K_RETRIEVAL", int(rag.get("top_k_retrieval", AppConfig.top_k_retrieval))),
        top_k_context=_env_int("TOP_K_CONTEXT", int(rag.get("top_k_context", AppConfig.top_k_context))),
        log_level=os.getenv("LOG_LEVEL", logging.get("level", AppConfig.log_level)),
    )


def resolve_path(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT_DIR / value


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT_DIR / ".env", override=False)
