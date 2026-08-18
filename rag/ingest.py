from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from rag.embeddings import LocalEmbeddingModel
from rag.store import get_collection


@dataclass(frozen=True)
class IngestStats:
    documents: int
    chunks: int


def ingest_documents(
    documents_path: Path,
    chroma_path: Path,
    collection_name: str,
    embedding_model_name: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 180,
) -> IngestStats:
    collection = get_collection(chroma_path, collection_name)
    embeddings = LocalEmbeddingModel(embedding_model_name)

    pdf_paths = sorted(documents_path.glob("*/*.pdf"))
    total_chunks = 0
    for pdf_path in pdf_paths:
        stock = pdf_path.parent.name.upper()
        pages = _extract_pages(pdf_path)
        if not pages:
            logging.warning("No text extracted from %s", pdf_path)
            continue

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str | int]] = []

        for page_number, text in pages:
            for index, chunk in enumerate(_chunk_text(text, chunk_size, chunk_overlap)):
                chunk_id = _chunk_id(stock, pdf_path, page_number, index, chunk)
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(
                    {
                        "stock": stock,
                        "document": pdf_path.stem,
                        "page": page_number,
                        "source_path": str(pdf_path),
                    }
                )

        if not documents:
            continue

        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings.encode(documents),
            metadatas=metadatas,
        )
        total_chunks += len(documents)
        logging.info("Ingested %s chunks from %s", len(documents), pdf_path)

    return IngestStats(documents=len(pdf_paths), chunks=total_chunks)


def _extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = _clean_text(text)
        if text:
            pages.append((index, text))
    return pages


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _chunk_id(stock: str, pdf_path: Path, page_number: int, index: int, chunk: str) -> str:
    digest = hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]
    return f"{stock}:{pdf_path.stem}:p{page_number}:c{index}:{digest}"

