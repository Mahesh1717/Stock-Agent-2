from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser


RSS_FEEDS = [
    {
        "name": "Moneycontrol Business",
        "url": "https://www.moneycontrol.com/rss/business.xml",
        "weight": 8,
    },
    {
        "name": "Moneycontrol Markets",
        "url": "https://www.moneycontrol.com/rss/marketreports.xml",
        "weight": 8,
    },
    {
        "name": "Economic Times Markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "weight": 8,
    },
    {
        "name": "LiveMint Markets",
        "url": "https://www.livemint.com/rss/markets",
        "weight": 7,
    },
]


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    source: str
    source_weight: int
    published_at: datetime | None

    @property
    def stable_id(self) -> str:
        raw = self.link or f"{self.source}:{self.title}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_recent(published_at: datetime | None, max_age_hours: int) -> bool:
    if published_at is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return published_at >= cutoff


def fetch_recent_articles(max_age_hours: int) -> list[Article]:
    articles: list[Article] = []
    seen: set[str] = set()

    for feed in RSS_FEEDS:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue

            published = (
                getattr(entry, "published", None)
                or getattr(entry, "updated", None)
                or getattr(entry, "created", None)
            )
            article = Article(
                title=title,
                link=getattr(entry, "link", ""),
                source=feed["name"],
                source_weight=int(feed["weight"]),
                published_at=_parse_datetime(published),
            )
            if article.stable_id in seen or not _is_recent(article.published_at, max_age_hours):
                continue
            seen.add(article.stable_id)
            articles.append(article)

    return articles

