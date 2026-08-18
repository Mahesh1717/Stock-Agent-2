from __future__ import annotations

import csv
from pathlib import Path


WATCHLIST_PATH = Path("data/nifty_watchlist.csv")
DOCUMENTS_PATH = Path("documents")


def main() -> None:
    DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
    with WATCHLIST_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            symbol = row["symbol"].strip().upper()
            if not symbol:
                continue
            folder = DOCUMENTS_PATH / symbol
            folder.mkdir(parents=True, exist_ok=True)
            (folder / ".gitkeep").touch()


if __name__ == "__main__":
    main()
