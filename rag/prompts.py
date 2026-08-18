from __future__ import annotations

from rag.models import EvidenceChunk


def build_retrieval_query(stock_symbol: str, stock_name: str, headline: str) -> str:
    return (
        f"{stock_symbol} {stock_name}. Latest news: {headline}. "
        "Retrieve recent earnings, revenue growth, margins, deal wins, "
        "management guidance, segment performance, risks, debt, and outlook."
    )


def build_ollama_prompt(
    stock_symbol: str,
    headline: str,
    chunks: tuple[EvidenceChunk, ...],
) -> str:
    evidence = "\n\n".join(
        f"Source: {chunk.citation}\nText: {chunk.text[:1200]}"
        for chunk in chunks
    )
    return f"""
You are analyzing company fundamentals for an investing alert.
Do not predict tomorrow's stock price.
Use only the evidence below. If evidence is weak, say so.

Stock: {stock_symbol}
Latest news: {headline}

Evidence:
{evidence}

Return strict JSON with:
score: integer from -2 to 2
summary: one sentence
positives: array of short evidence-based points
risks: array of short evidence-based points
""".strip()

