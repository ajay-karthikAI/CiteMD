from __future__ import annotations

import logging
import json
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET
from typing import Iterable

from backend.schemas import Paper


logger = logging.getLogger(__name__)


class PubMedClient:
    """Thin Entrez API client for PubMed search and abstract retrieval."""

    def __init__(self, email: str, api_key: str | None = None) -> None:
        self.email = email
        self.api_key = api_key

    def search(self, query: str, limit: int = 100, sort: str = "relevance") -> list[str]:
        try:
            from Bio import Entrez
        except ImportError:
            return self._search_stdlib(query=query, limit=limit, sort=sort)

        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key

        logger.info("Searching PubMed", extra={"query": query, "limit": limit})
        with Entrez.esearch(db="pubmed", term=query, retmax=limit, sort=sort) as handle:
            record = Entrez.read(handle)
        return [str(pmid) for pmid in record.get("IdList", [])]

    def fetch(self, pmids: Iterable[str]) -> list[Paper]:
        ids = [str(pmid) for pmid in pmids if str(pmid).strip()]
        if not ids:
            return []

        try:
            from Bio import Entrez
        except ImportError:
            return self._fetch_stdlib(ids)

        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key

        logger.info("Fetching PubMed abstracts", extra={"count": len(ids)})
        with Entrez.efetch(db="pubmed", id=",".join(ids), retmode="xml") as handle:
            record = Entrez.read(handle)

        articles = record.get("PubmedArticle", [])
        papers = [self._parse_article(article) for article in articles]
        return [paper for paper in papers if paper.abstract]

    def search_and_fetch(self, query: str, limit: int = 100) -> list[Paper]:
        return self.fetch(self.search(query=query, limit=limit))

    def _search_stdlib(self, query: str, limit: int, sort: str) -> list[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": str(limit),
            "sort": sort,
            "retmode": "json",
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(params)
        logger.info("Searching PubMed with stdlib client", extra={"query": query, "limit": limit})
        with urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [str(pmid) for pmid in payload.get("esearchresult", {}).get("idlist", [])]

    def _fetch_stdlib(self, ids: list[str]) -> list[Paper]:
        params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urlencode(params)
        logger.info("Fetching PubMed abstracts with stdlib client", extra={"count": len(ids)})
        with urlopen(url, timeout=60) as response:
            root = ET.fromstring(response.read())
        papers = [self._parse_article_xml(article) for article in root.findall(".//PubmedArticle")]
        return [paper for paper in papers if paper.abstract]

    def _parse_article(self, article: dict) -> Paper:
        citation = article.get("MedlineCitation", {})
        pubmed_data = article.get("PubmedData", {})
        pmid = str(citation.get("PMID", ""))
        article_data = citation.get("Article", {})

        title = _stringify(article_data.get("ArticleTitle", "")).strip()
        abstract = _parse_abstract(article_data.get("Abstract", {}))
        journal_data = article_data.get("Journal", {})
        journal = _stringify(journal_data.get("Title", "")).strip()
        published = _parse_pub_date(journal_data.get("JournalIssue", {}).get("PubDate", {}))
        authors = tuple(_parse_authors(article_data.get("AuthorList", [])))
        doi = _parse_doi(pubmed_data.get("ArticleIdList", []))

        return Paper(
            pmid=pmid,
            title=title or f"PubMed record {pmid}",
            abstract=abstract,
            journal=journal,
            published=published,
            authors=authors,
            doi=doi,
        )

    def _parse_article_xml(self, article: ET.Element) -> Paper:
        pmid = _xml_text(article.find("./MedlineCitation/PMID"))
        title = _xml_inner_text(article.find("./MedlineCitation/Article/ArticleTitle"))
        abstract_parts = []
        for element in article.findall("./MedlineCitation/Article/Abstract/AbstractText"):
            label = element.attrib.get("Label")
            text = _xml_inner_text(element)
            if text:
                abstract_parts.append(f"{label}: {text}" if label else text)
        journal = _xml_text(article.find("./MedlineCitation/Article/Journal/Title"))
        pub_date = article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate")
        published = ""
        if pub_date is not None:
            published = _xml_text(pub_date.find("Year")) or _xml_text(pub_date.find("MedlineDate"))
        authors = []
        for author in article.findall("./MedlineCitation/Article/AuthorList/Author"):
            collective = _xml_text(author.find("CollectiveName"))
            if collective:
                authors.append(collective)
                continue
            last = _xml_text(author.find("LastName"))
            initials = _xml_text(author.find("Initials"))
            if last:
                authors.append(f"{last} {initials}".strip())
        doi = None
        for article_id in article.findall("./PubmedData/ArticleIdList/ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = _xml_inner_text(article_id)
                break

        return Paper(
            pmid=pmid,
            title=title or f"PubMed record {pmid}",
            abstract=" ".join(abstract_parts),
            journal=journal,
            published=published,
            authors=tuple(authors),
            doi=doi,
        )


def _parse_abstract(abstract_data: dict) -> str:
    parts = abstract_data.get("AbstractText", []) if isinstance(abstract_data, dict) else []
    text_parts: list[str] = []
    for part in parts:
        label = getattr(part, "attributes", {}).get("Label")
        text = _stringify(part).strip()
        if not text:
            continue
        text_parts.append(f"{label}: {text}" if label else text)
    return " ".join(text_parts)


def _parse_authors(author_list: Iterable[dict]) -> list[str]:
    authors: list[str] = []
    for author in author_list:
        collective = author.get("CollectiveName")
        if collective:
            authors.append(_stringify(collective))
            continue
        last = _stringify(author.get("LastName", "")).strip()
        initials = _stringify(author.get("Initials", "")).strip()
        if last:
            authors.append(f"{last} {initials}".strip())
    return authors


def _parse_pub_date(pub_date: dict) -> str:
    year = _stringify(pub_date.get("Year", "")).strip()
    medline = _stringify(pub_date.get("MedlineDate", "")).strip()
    return year or medline


def _parse_doi(article_ids: Iterable[object]) -> str | None:
    for article_id in article_ids:
        attributes = getattr(article_id, "attributes", {})
        if attributes.get("IdType") == "doi":
            return _stringify(article_id).strip()
    return None


def _stringify(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _xml_text(element: ET.Element | None) -> str:
    return "" if element is None or element.text is None else element.text.strip()


def _xml_inner_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join(part.strip() for part in element.itertext() if part and part.strip())
