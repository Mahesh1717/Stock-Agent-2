from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None or value == "" else float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None or value == "" else int(value)


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    dry_run: bool
    run_interval_seconds: int
    rss_max_age_hours: int
    watchlist_path: Path
    processed_store_path: Path
    sentiment_model: str
    sentiment_positive_threshold: float
    sentiment_negative_threshold: float
    rsi_buy_threshold: float
    rsi_sell_threshold: float
    volume_spike_threshold: float
    min_alert_score: int
    alert_actions: tuple[str, ...]


def load_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        dry_run=_bool_env("DRY_RUN", True),
        run_interval_seconds=_int_env("RUN_INTERVAL_SECONDS", 60),
        rss_max_age_hours=_int_env("RSS_MAX_AGE_HOURS", 24),
        watchlist_path=Path(os.getenv("WATCHLIST_PATH", "data/nifty_watchlist.csv")),
        processed_store_path=Path(os.getenv("PROCESSED_STORE_PATH", "data/processed_news.json")),
        sentiment_model=os.getenv("SENTIMENT_MODEL", "ProsusAI/finbert"),
        sentiment_positive_threshold=_float_env("SENTIMENT_POSITIVE_THRESHOLD", 0.80),
        sentiment_negative_threshold=_float_env("SENTIMENT_NEGATIVE_THRESHOLD", 0.80),
        rsi_buy_threshold=_float_env("RSI_BUY_THRESHOLD", 35.0),
        rsi_sell_threshold=_float_env("RSI_SELL_THRESHOLD", 70.0),
        volume_spike_threshold=_float_env("VOLUME_SPIKE_THRESHOLD", 1.5),
        min_alert_score=_int_env("MIN_ALERT_SCORE", 3),
        alert_actions=_csv_env("ALERT_ACTIONS", ("BUY", "HOLD", "SELL")),
    )
