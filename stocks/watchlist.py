from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz


@dataclass(frozen=True)
class Stock:
    symbol: str
    yahoo_symbols: tuple[str, ...]
    name: str
    aliases: tuple[str, ...]

    @property
    def yahoo_symbol(self) -> str:
        return self.yahoo_symbols[0]


def load_watchlist(path: Path) -> list[Stock]:
    stocks: list[Stock] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            aliases = tuple(
                value.strip().lower()
                for value in row.get("aliases", "").split("|")
                if value.strip()
            )
            stocks.append(
                Stock(
                    symbol=row["symbol"].strip(),
                    yahoo_symbols=tuple(
                        value.strip()
                        for value in row["yahoo_symbol"].replace(",", "|").split("|")
                        if value.strip()
                    ),
                    name=row["name"].strip(),
                    aliases=(row["name"].strip().lower(), row["symbol"].strip().lower(), *aliases),
                )
            )
    return stocks


def match_stock(headline: str, watchlist: list[Stock], min_score: int = 90) -> Stock | None:
    normalized = headline.lower()
    exact_stock: Stock | None = None
    exact_alias_length = 0
    best_stock: Stock | None = None
    best_score = 0

    for stock in watchlist:
        for alias in stock.aliases:
            if alias and _contains_alias(normalized, alias):
                if len(alias) > exact_alias_length:
                    exact_alias_length = len(alias)
                    exact_stock = stock
                continue
            if len(alias) < 5:
                continue
            score = fuzz.partial_ratio(alias, normalized)
            if score > best_score:
                best_score = score
                best_stock = stock

    if exact_stock is not None:
        return exact_stock
    if best_score >= min_score:
        return best_stock
    return None


def _contains_alias(headline: str, alias: str) -> bool:
    if len(alias) < 5:
        return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", headline) is not None
    return alias in headline
