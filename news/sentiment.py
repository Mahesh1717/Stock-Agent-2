from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float

    @property
    def positive_score(self) -> float:
        return self.score if self.label == "positive" else 0.0

    @property
    def negative_score(self) -> float:
        return self.score if self.label == "negative" else 0.0


class FinbertSentimentAnalyzer:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def classifier(self):
        from transformers import pipeline

        return pipeline("text-classification", model=self.model_name)

    def analyze(self, text: str) -> SentimentResult:
        result = self.classifier(text, truncation=True)[0]
        return SentimentResult(
            label=str(result["label"]).lower(),
            score=float(result["score"]),
        )
