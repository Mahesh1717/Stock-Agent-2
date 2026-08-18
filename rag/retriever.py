from __future__ import annotations

from pathlib import Path

from rag.embeddings import LocalEmbeddingModel
from rag.models import EvidenceChunk
from rag.store import get_collection


class RagRetriever:
    def __init__(
        self,
        chroma_path: Path,
        collection_name: str,
        embedding_model_name: str,
        top_k: int,
    ) -> None:
        self.collection = get_collection(chroma_path, collection_name)
        self.embeddings = LocalEmbeddingModel(embedding_model_name)
        self.top_k = top_k

    def retrieve(self, stock_symbol: str, query: str) -> tuple[EvidenceChunk, ...]:
        count = self.collection.count()
        if count == 0:
            return ()

        query_embedding = self.embeddings.encode([query])[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(self.top_k, count),
            where={"stock": stock_symbol.upper()},
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks: list[EvidenceChunk] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            chunks.append(
                EvidenceChunk(
                    text=str(text),
                    stock=str(metadata.get("stock", stock_symbol)).upper(),
                    document=str(metadata.get("document", "unknown")),
                    page=_optional_int(metadata.get("page")),
                    source_path=str(metadata.get("source_path", "")),
                    distance=float(distance) if distance is not None else None,
                )
            )
        return tuple(chunks)


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
