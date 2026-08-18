from __future__ import annotations

import logging

import requests

from stocks.signals import Signal


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, dry_run: bool = True) -> None:
        self.token = token
        self.chat_id = chat_id
        self.dry_run = dry_run

    def send_signal(self, signal: Signal) -> None:
        self.send_text(self._format_signal(signal))

    def send_text(self, message: str) -> None:
        if self.dry_run:
            logging.info("DRY_RUN Telegram alert:\n%s", message)
            return

        if not self.token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required when DRY_RUN=false")

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": self.chat_id, "text": message, "disable_web_page_preview": True},
            timeout=15,
        )
        response.raise_for_status()

    @staticmethod
    def _format_signal(signal: Signal) -> str:
        direction = "BUY SIGNAL" if signal.action == "BUY" else f"{signal.action} SIGNAL"
        reasons = "\n".join(f"- {reason}" for reason in signal.reasons) or "- No strong bullish factors"
        risks = "\n".join(f"- {risk}" for risk in signal.risks) or "- No major risk flags"
        fundamentals = TelegramNotifier._format_fundamentals(signal)

        return (
            f"{direction}\n\n"
            f"Stock: {signal.stock.symbol} ({signal.stock.name})\n"
            f"News: {signal.article.title}\n"
            f"Source: {signal.article.source} (weight {signal.article.source_weight}/10)\n\n"
            f"Sentiment: {signal.sentiment.label.title()} {signal.sentiment.score:.0%}\n"
            f"RSI: {signal.indicators.rsi:.1f}\n"
            f"MACD: {'Bullish' if signal.indicators.macd_bullish else 'Bearish'}\n"
            f"Close: {signal.indicators.close:.2f}\n"
            f"SMA20: {signal.indicators.sma20:.2f}\n"
            f"Volume: {signal.indicators.volume_ratio:.1f}x 20-day average\n\n"
            f"Score: {signal.score}\n"
            f"Confidence: {signal.confidence}%\n"
            f"Action: {signal.action}\n\n"
            f"Reasons:\n{reasons}\n\n"
            f"Risks:\n{risks}\n\n"
            f"{fundamentals}"
            f"Link: {signal.article.link}"
        )

    @staticmethod
    def _format_fundamentals(signal: Signal) -> str:
        if signal.fundamentals is None:
            return ""
        assessment = signal.fundamentals
        if not assessment.has_evidence:
            return f"RAG Evidence:\n- {assessment.summary}\n\n"

        positives = "\n".join(f"- {item}" for item in assessment.positives) or "- No clear positive evidence"
        risks = "\n".join(f"- {item}" for item in assessment.risks) or "- No clear document risk"
        sources = "\n".join(
            f"- {chunk.citation}"
            for chunk in assessment.evidence[:3]
        )
        return (
            f"RAG Evidence:\n"
            f"Summary: {assessment.summary}\n"
            f"Fundamental Score: {assessment.score}\n"
            f"Positives:\n{positives}\n"
            f"Document Risks:\n{risks}\n"
            f"Sources:\n{sources}\n\n"
        )
