from __future__ import annotations

from dataclasses import dataclass

from news.fetch_news import Article
from news.sentiment import SentimentResult
from stocks.indicators import IndicatorResult
from stocks.watchlist import Stock


@dataclass(frozen=True)
class Signal:
    stock: Stock
    article: Article
    sentiment: SentimentResult
    indicators: IndicatorResult
    score: int
    action: str
    confidence: int
    reasons: tuple[str, ...]
    risks: tuple[str, ...]


def build_signal(
    stock: Stock,
    article: Article,
    sentiment: SentimentResult,
    indicators: IndicatorResult,
    positive_threshold: float,
    negative_threshold: float,
    rsi_buy_threshold: float,
    rsi_sell_threshold: float,
    volume_spike_threshold: float,
) -> Signal:
    score = 0
    reasons: list[str] = []
    risks: list[str] = []

    if sentiment.label == "positive" and sentiment.score >= positive_threshold:
        score += 3
        reasons.append(f"Positive financial news ({sentiment.score:.0%})")
        if article.source_weight >= 8:
            score += 1
            reasons.append(f"High-trust news source ({article.source_weight}/10)")
    elif sentiment.label == "negative" and sentiment.score >= negative_threshold:
        score -= 3
        risks.append(f"Negative financial news ({sentiment.score:.0%})")
        if article.source_weight >= 8:
            score -= 1
            risks.append(f"High-trust negative source ({article.source_weight}/10)")

    if indicators.rsi < rsi_buy_threshold:
        score += 2
        reasons.append(f"RSI is oversold at {indicators.rsi:.1f}")
    elif indicators.rsi > rsi_sell_threshold:
        score -= 2
        risks.append(f"RSI is overbought at {indicators.rsi:.1f}")

    if indicators.macd_bullish:
        score += 2
        reasons.append("MACD is bullish")
    else:
        risks.append("MACD is not bullish")

    if indicators.volume_ratio >= volume_spike_threshold:
        score += 1
        reasons.append(f"Volume is {indicators.volume_ratio:.1f}x the 20-day average")

    if indicators.price_above_sma20:
        score += 1
        reasons.append("Price is above SMA20")
    else:
        risks.append("Price is below SMA20")

    action = _action_from_score(score)
    confidence = _confidence(score, article.source_weight)

    return Signal(
        stock=stock,
        article=article,
        sentiment=sentiment,
        indicators=indicators,
        score=score,
        action=action,
        confidence=confidence,
        reasons=tuple(reasons),
        risks=tuple(risks),
    )


def _action_from_score(score: int) -> str:
    if score >= 6:
        return "BUY"
    if score >= 3:
        return "HOLD"
    return "SELL"


def _confidence(score: int, source_weight: int) -> int:
    bounded_score = max(0, min(score, 9))
    return min(95, max(10, int((bounded_score / 9) * 70 + source_weight * 2.5)))
