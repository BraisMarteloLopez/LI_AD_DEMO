"""Ingestion runner: download PDF, call MinerU, persist `text.jsonl`.

Fase 1.B.2: se filtran bloques del `content_list` a `text` y `title`
(decisión D4). Se descartan imágenes, tablas y ecuaciones. La salida
canónica es un JSON-lines bajo `{prefix}/{collection_id}/ocr/{stem}/text.jsonl`
con `{"page": int, "type": "text"|"title", "text": str, ...}` por bloque.

Pre-chunker content filters (Ola 1): después de persistir `text.jsonl`
(que mantiene la salida cruda de MinerU como cache), se aplican los
filtros default-on de `content_filters` para limpiar TOC dot-leaders,
marcadores de página en blanco y bloques muy cortos antes de
chunkear. El JSONL se conserva intacto para poder re-chunkear con
otro perfil sin re-llamar a MinerU.
"""
from __future__ import annotations

import io
import json
import logging
import os
from typing import Callable, Iterable

from admin.collections import service as coll_service
from admin.collections.files import RAW_SUBPREFIX, sanitize_filename
from admin.collections.models import IngestProfile
from admin.ingest.chunker import chunk_text_blocks
from admin.ingest.chunks_io import write_chunks
from admin.ingest.content_filters import (
    apply_profile_chunk_filters,
    apply_profile_filters,
)
from admin.ingest.mineru import MineruResult, OcrClient

logger = logging.getLogger("admin.ingest.runner")

OCR_SUBPREFIX = "ocr"
TEXT_JSONL = "text.jsonl"

KEEP_TYPES = {"text", "title"}


def _stem(filename: str) -> str:
    base = os.path.basename(filename)
    stem, _, _ = base.rpartition(".")
    return stem or base


def _raw_key(prefix: str, collection_id: str, filename: str) -> str:
    return f"{prefix}/{collection_id}/{RAW_SUBPREFIX}/{filename}"


def _jsonl_key(prefix: str, collection_id: str, filename: str) -> str:
    stem = _stem(sanitize_filename(filename))
    return f"{prefix}/{collection_id}/{OCR_SUBPREFIX}/{stem}/{TEXT_JSONL}"


def filter_blocks(content_list: Iterable[dict]) -> list[dict]:
    """Keep only text/title blocks with non-empty text.

    Page indices in MinerU's content_list are 0-based (`page_idx`); we
    expose them as 1-based so they match what a human sees in a PDF reader.

    Optional metadata (`bbox`, `text_level`) is preserved when MinerU
    emits it, descartado en silencio si no. Lo necesitamos para
    heuristicas posteriores (header/footer auto-detect via bbox; heading
    depth via text_level). Mantener estos campos en `text.jsonl` evita
    re-llamar a MinerU para chunkear distinto.
    """
    out: list[dict] = []
    for block in content_list:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype not in KEEP_TYPES:
            continue
        text = (block.get("text") or "").strip()
        if not text:
            continue
        page_idx = block.get("page_idx")
        page = int(page_idx) + 1 if isinstance(page_idx, int) else 1
        kept: dict = {"page": page, "type": btype, "text": text}
        bbox = block.get("bbox")
        if bbox is not None:
            kept["bbox"] = bbox
        text_level = block.get("text_level")
        if text_level is not None:
            kept["text_level"] = text_level
        out.append(kept)
    return out


def _serialize_jsonl(blocks: list[dict]) -> bytes:
    buf = io.StringIO()
    for b in blocks:
        buf.write(json.dumps(b, ensure_ascii=False))
        buf.write("\n")
    return buf.getvalue().encode("utf-8")


def build_runner(mineru: OcrClient) -> Callable[[object, str, str, str, str], None]:
    """Return an ingest runner bound to a MinerU client.

    Runner signature matches `admin.ingest.service.ingest_file`'s contract:
    `(client, bucket, prefix, collection_id, filename) -> None`.
    """

    def _run(client, bucket: str, prefix: str, collection_id: str, filename: str) -> None:
        raw_key = _raw_key(prefix, collection_id, filename)
        obj = client.get_object(Bucket=bucket, Key=raw_key)
        pdf_bytes = obj["Body"].read()

        result: MineruResult = mineru.parse(pdf_bytes, filename)
        blocks = filter_blocks(result.content_list)
        logger.info(
            "ingest filtered collection=%s file=%s kept=%d raw=%d",
            collection_id, filename, len(blocks), len(result.content_list),
        )

        out_key = _jsonl_key(prefix, collection_id, filename)
        client.put_object(
            Bucket=bucket,
            Key=out_key,
            Body=_serialize_jsonl(blocks),
            ContentType="application/x-ndjson",
        )
        logger.info(
            "ingest wrote collection=%s key=%s blocks=%d",
            collection_id, out_key, len(blocks),
        )

        # Pre-chunker filters segun el IngestProfile de la coleccion.
        # JSONL ya esta escrito con los bloques crudos: si manana cambia
        # el perfil, se re-chunkea desde JSONL sin volver a llamar a MinerU.
        coll = coll_service.get(
            client, bucket=bucket, prefix=prefix, collection_id=collection_id,
        )
        profile = coll.ingest_profile if coll is not None else IngestProfile()
        filtered = apply_profile_filters(blocks, profile)
        logger.info(
            "ingest content-filtered collection=%s file=%s kept=%d before=%d",
            collection_id, filename, len(filtered), len(blocks),
        )

        stem = _stem(sanitize_filename(filename))
        raw_chunks = chunk_text_blocks(
            filtered,
            collection_id=collection_id,
            source_file=sanitize_filename(filename),
            target_tokens=profile.target_tokens,
            overlap_tokens=profile.overlap_tokens,
        )
        # Post-chunker filter segun profile (safety net contra chunks
        # fragmentarios tras el filtrado de bloques).
        chunks = apply_profile_chunk_filters(raw_chunks, profile)
        if len(chunks) != len(raw_chunks):
            logger.info(
                "ingest chunk-filtered collection=%s file=%s kept=%d before=%d",
                collection_id, filename, len(chunks), len(raw_chunks),
            )
        chunks_written = write_chunks(
            client,
            bucket=bucket, prefix=prefix, collection_id=collection_id,
            filename_stem=stem, chunks=chunks,
        )
        logger.info(
            "ingest chunked collection=%s key=%s chunks=%d",
            collection_id, chunks_written, len(chunks),
        )

    return _run
