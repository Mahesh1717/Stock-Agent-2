from __future__ import annotations

from pathlib import Path

import chromadb


def get_collection(chroma_path: Path, collection_name: str):
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    return client.get_or_create_collection(name=collection_name)

