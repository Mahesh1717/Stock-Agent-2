from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import requests

from rag.models import EvidenceChunk, FundamentalAssessment
from rag.prompts import build_ollama_prompt


POSITIVE_TERMS = (
    "growth",
    "grew",
    "increase",
    "increased",
    "strong",
    "margin expansion",
    "deal win",
    "order book",
    "guidance",
    "improved",
    "profit",
)
NEGATIVE_TERMS = (
    "decline",
    "declined",
    "weak",
    "pressure",
    "margin pressure",
    "debt",
    "loss",
    "risk",
    "slowdown",
    "headwind",
)


@dataclass(frozen=True)
class OllamaSettings:
    enabled: bool
    model: str
    url: str
    timeout_seconds: int


class FundamentalAnalyzer:
    def __init__(self, ollama: OllamaSettings) -> None:
        self.ollama = ollama

    def analyze(
        self,
        stock_symbol: str,
        headline: str,
        chunks: tuple[EvidenceChunk, ...],
    ) -> FundamentalAssessment:
        if not chunks:
            return FundamentalAssessment(
                score=0,
                summary="No local financial-document evidence found.",
                positives=(),
                risks=("Add annual reports, results, or investor presentations for this stock.",),
                evidence=(),
            )

        if self.ollama.enabled:
            try:
                return self._analyze_with_ollama(stock_symbol, headline, chunks)
            except Exception:
                logging.exception("Ollama analysis failed; using local heuristic")

        return self._analyze_with_heuristic(chunks)

    def _analyze_with_ollama(
        self,
        stock_symbol: str,
        headline: str,
        chunks: tuple[EvidenceChunk, ...],
    ) -> FundamentalAssessment:
        response = requests.post(
            self.ollama.url,
            json={
                "model": self.ollama.model,
                "prompt": build_ollama_prompt(stock_symbol, headline, chunks),
                "stream": False,
                "format": "json",
            },
            timeout=self.ollama.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        analysis = json.loads(payload.get("response", "{}"))
        return FundamentalAssessment(
            score=max(-2, min(2, int(analysis.get("score", 0)))),
            summary=str(analysis.get("summary", "Local evidence analyzed.")),
            positives=tuple(str(item) for item in analysis.get("positives", [])[:4]),
            risks=tuple(str(item) for item in analysis.get("risks", [])[:4]),
            evidence=chunks,
        )

    def _analyze_with_heuristic(self, chunks: tuple[EvidenceChunk, ...]) -> FundamentalAssessment:
        text = " ".join(chunk.text.lower() for chunk in chunks)
        positive_hits = _count_terms(text, POSITIVE_TERMS)
        negative_hits = _count_terms(text, NEGATIVE_TERMS)
        raw_score = positive_hits - negative_hits
        score = 0
        if raw_score >= 3:
            score = 2
        elif raw_score >= 1:
            score = 1
        elif raw_score <= -3:
            score = -2
        elif raw_score <= -1:
            score = -1

        positives = _evidence_lines(chunks, POSITIVE_TERMS, limit=3)
        risks = _evidence_lines(chunks, NEGATIVE_TERMS, limit=3)
        summary = "Local financial evidence is mixed."
        if score > 0:
            summary = "Local financial evidence is modestly supportive."
        elif score < 0:
            summary = "Local financial evidence highlights risks."

        return FundamentalAssessment(
            score=score,
            summary=summary,
            positives=tuple(positives),
            risks=tuple(risks),
            evidence=chunks,
        )


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(text.count(term) for term in terms)


def _evidence_lines(
    chunks: tuple[EvidenceChunk, ...],
    terms: tuple[str, ...],
    limit: int,
) -> list[str]:
    lines: list[str] = []
    pattern = re.compile("|".join(re.escape(term) for term in terms), re.IGNORECASE)
    for chunk in chunks:
        sentences = re.split(r"(?<=[.!?])\s+", chunk.text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30 or not pattern.search(sentence):
                continue
            lines.append(f"{sentence[:220]} ({chunk.citation})")
            if len(lines) >= limit:
                return lines
    return lines

