from __future__ import annotations

import json
from pathlib import Path


class ProcessedNewsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._items = self._load()

    def contains(self, article_id: str) -> bool:
        return article_id in self._items

    def add(self, article_id: str) -> None:
        self._items.add(article_id)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(sorted(self._items), indent=2),
            encoding="utf-8",
        )

    def _load(self) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            values = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return set()
        if not isinstance(values, list):
            return set()
        return {str(value) for value in values}

