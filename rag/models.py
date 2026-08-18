from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceChunk:
    text: str
    stock: str
    document: str
    page: int | None
    source_path: str
    distance: float | None = None

    @property
    def citation(self) -> str:
        page_text = f", page {self.page}" if self.page else ""
        return f"{self.document}{page_text}"


@dataclass(frozen=True)
class FundamentalAssessment:
    score: int
    summary: str
    positives: tuple[str, ...]
    risks: tuple[str, ...]
    evidence: tuple[EvidenceChunk, ...]

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)

