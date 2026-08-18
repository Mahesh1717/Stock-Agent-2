from __future__ import annotations

from dataclasses import dataclass

from news.fetch_news import Article
from news.sentiment import SentimentResult
from rag.models import FundamentalAssessment
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
    fundamentals: FundamentalAssessment | None = None


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
    fundamentals: FundamentalAssessment | None = None,
) -> Signal:
    score = 0
    reasons: list[str] = []
    risks: list[str] = []
    negative_news = False
    high_volume = indicators.volume_ratio >= volume_spike_threshold
    bearish_macd = not indicators.macd_bullish
    below_sma20 = not indicators.price_above_sma20

    if sentiment.label == "positive" and sentiment.score >= positive_threshold:
        score += 3
        reasons.append(f"Positive financial news ({sentiment.score:.0%})")
        if article.source_weight >= 8:
            score += 1
            reasons.append(f"High-trust news source ({article.source_weight}/10)")
    elif sentiment.label == "negative" and sentiment.score >= negative_threshold:
        negative_news = True
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

    if high_volume:
        score += 1
        if negative_news and bearish_macd:
            risks.append(f"High selling-volume confirmation ({indicators.volume_ratio:.1f}x average)")
        else:
            reasons.append(f"Volume is {indicators.volume_ratio:.1f}x the 20-day average")

    if indicators.price_above_sma20:
        score += 1
        reasons.append("Price is above SMA20")
    else:
        risks.append("Price is below SMA20")

    if fundamentals and fundamentals.has_evidence:
        score += fundamentals.score
        if fundamentals.score > 0:
            reasons.append(f"Fundamental evidence supportive (+{fundamentals.score})")
        elif fundamentals.score < 0:
            risks.append(f"Fundamental evidence negative ({fundamentals.score})")
    elif fundamentals:
        risks.append("No local financial-document evidence available")

    strong_sell = negative_news and bearish_macd and high_volume and below_sma20
    action = _action_from_score(score, strong_sell)
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
        fundamentals=fundamentals,
    )


def _action_from_score(score: int, strong_sell: bool) -> str:
    if score >= 6:
        return "BUY"
    if score >= 3:
        return "HOLD"
    if strong_sell:
        return "SELL"
    return "IGNORE"


def _confidence(score: int, source_weight: int) -> int:
    bounded_score = max(0, min(abs(score), 9))
    return min(95, max(10, int((bounded_score / 9) * 70 + source_weight * 2.5)))
