from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from config import Settings, load_settings
from news.fetch_news import fetch_recent_articles
from news.sentiment import FinbertSentimentAnalyzer
from stocks.indicators import TechnicalAnalyzer
from stocks.signals import build_signal
from stocks.watchlist import Stock, load_watchlist, match_stock
from storage.processed_news import ProcessedNewsStore
from telegram.notifier import TelegramNotifier


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


@dataclass
class StockAgent:
    settings: Settings
    watchlist: list[Stock]
    processed: ProcessedNewsStore
    sentiment: FinbertSentimentAnalyzer
    technicals: TechnicalAnalyzer
    notifier: TelegramNotifier
    retriever: object
    fundamentals: object

    @classmethod
    def create(cls) -> "StockAgent":
        settings = load_settings()
        from rag.fundamentals import FundamentalAnalyzer, OllamaSettings
        from rag.retriever import RagRetriever

        retriever = RagRetriever(
            chroma_path=settings.chroma_path,
            collection_name=settings.rag_collection,
            embedding_model_name=settings.embedding_model,
            top_k=settings.rag_top_k,
        )
        fundamentals = FundamentalAnalyzer(
            OllamaSettings(
                enabled=settings.ollama_enabled,
                model=settings.ollama_model,
                url=settings.ollama_url,
                timeout_seconds=settings.ollama_timeout_seconds,
            )
        )

        return cls(
            settings=settings,
            watchlist=load_watchlist(settings.watchlist_path),
            processed=ProcessedNewsStore(settings.processed_store_path),
            sentiment=FinbertSentimentAnalyzer(settings.sentiment_model),
            technicals=TechnicalAnalyzer(),
            notifier=TelegramNotifier(
                token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
                dry_run=settings.dry_run,
            ),
            retriever=retriever,
            fundamentals=fundamentals,
        )

    def run_cycle(self) -> None:
        articles = fetch_recent_articles(self.settings.rss_max_age_hours)
        logging.info("Fetched %s recent articles", len(articles))

        sent_count = 0
        for article in articles:
            article_id = article.stable_id
            if self.processed.contains(article_id):
                continue

            stock = match_stock(article.title, self.watchlist)
            if stock is None:
                self.processed.add(article_id)
                continue

            try:
                sentiment_result = self.sentiment.analyze(article.title)
                indicator_result = self.technicals.analyze(stock.yahoo_symbols)
                fundamental_result = self._analyze_fundamentals(stock, article.title)
                signal = build_signal(
                    stock=stock,
                    article=article,
                    sentiment=sentiment_result,
                    indicators=indicator_result,
                    positive_threshold=self.settings.sentiment_positive_threshold,
                    negative_threshold=self.settings.sentiment_negative_threshold,
                    rsi_buy_threshold=self.settings.rsi_buy_threshold,
                    rsi_sell_threshold=self.settings.rsi_sell_threshold,
                    volume_spike_threshold=self.settings.volume_spike_threshold,
                    fundamentals=fundamental_result,
                )
            except Exception:
                logging.exception("Failed to analyze article: %s", article.title)
                self.processed.add(article_id)
                continue

            logging.info("%s | %s | score=%s", stock.symbol, signal.action, signal.score)
            should_alert = (
                signal.action in self.settings.alert_actions
                and (signal.action == "SELL" or signal.score >= self.settings.min_alert_score)
            )
            if should_alert:
                self.notifier.send_signal(signal)
                sent_count += 1

            self.processed.add(article_id)

        self.processed.save()
        logging.info("Cycle complete. Alerts sent: %s", sent_count)

    def _analyze_fundamentals(self, stock: Stock, headline: str):
        from rag.prompts import build_retrieval_query

        query = build_retrieval_query(stock.symbol, stock.name, headline)
        chunks = self.retriever.retrieve(stock.symbol, query)
        return self.fundamentals.analyze(stock.symbol, headline, chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 RAG stock alert agent")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test Telegram message and exit")
    parser.add_argument("--ingest-documents", action="store_true", help="Ingest PDFs from documents/SYMBOL into Chroma")
    parser.add_argument("--rag-query", help="Test RAG retrieval for a stock symbol and question")
    parser.add_argument("--stock", help="Stock symbol to use with --rag-query")
    args = parser.parse_args()

    settings = load_settings()
    if args.ingest_documents:
        from rag.ingest import ingest_documents

        stats = ingest_documents(
            documents_path=settings.documents_path,
            chroma_path=settings.chroma_path,
            collection_name=settings.rag_collection,
            embedding_model_name=settings.embedding_model,
        )
        logging.info("Document ingest complete. PDFs: %s, chunks: %s", stats.documents, stats.chunks)
        return

    if args.rag_query:
        if not args.stock:
            parser.error("--rag-query requires --stock")
        from rag.retriever import RagRetriever

        retriever = RagRetriever(
            chroma_path=settings.chroma_path,
            collection_name=settings.rag_collection,
            embedding_model_name=settings.embedding_model,
            top_k=settings.rag_top_k,
        )
        chunks = retriever.retrieve(args.stock, args.rag_query)
        for index, chunk in enumerate(chunks, start=1):
            print(f"\n[{index}] {chunk.citation}")
            print(chunk.text[:700])
        return

    agent = StockAgent.create()
    if args.test_telegram:
        agent.notifier.send_text("Stock Agent Telegram test: connection is working.")
        logging.info("Telegram test message sent")
        return

    if args.once:
        agent.run_cycle()
        return

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        agent.run_cycle,
        "interval",
        seconds=settings.run_interval_seconds,
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    logging.info("Stock agent started. Interval: %s seconds", settings.run_interval_seconds)
    scheduler.start()


if __name__ == "__main__":
    main()
