from __future__ import annotations

import re

from backend.schemas import ConflictReport, ScoredPaper


SUPPORT_PATTERNS = [
    r"\bimproved\b",
    r"\bbenefit\b",
    r"\beffective\b",
    r"\bsuperior\b",
    r"\bprolonged survival\b",
    r"\bincreased response\b",
    r"\bsignificantly (improved|reduced|increased)\b",
]
OPPOSE_PATTERNS = [
    r"\bno (significant )?benefit\b",
    r"\bno (significant )?difference\b",
    r"\bdid not improve\b",
    r"\bnot associated\b",
    r"\bfailed to improve\b",
    r"\bineffective\b",
    r"\bno survival advantage\b",
]


class EvidenceConflictDetector:
    """Simple rule-based detector for contradictory biomedical conclusions."""

    def detect(self, papers: list[ScoredPaper]) -> ConflictReport:
        supporting: list[str] = []
        opposing: list[str] = []
        for item in papers:
            text = f"{item.paper.title} {item.paper.abstract}".lower()
            has_support = any(re.search(pattern, text) for pattern in SUPPORT_PATTERNS)
            has_oppose = any(re.search(pattern, text) for pattern in OPPOSE_PATTERNS)
            if has_oppose:
                opposing.append(item.paper.pmid)
            elif has_support:
                supporting.append(item.paper.pmid)

        if supporting and opposing:
            return ConflictReport(
                conflicting=True,
                summary=(
                    "Conflicting evidence detected. Some retrieved papers report benefit or improved outcomes, "
                    "while others report no significant benefit or no clear advantage."
                ),
                supporting_pmids=tuple(supporting),
                opposing_pmids=tuple(opposing),
            )
        return ConflictReport(conflicting=False, summary="No obvious conflict detected in the top retrieved abstracts.")

