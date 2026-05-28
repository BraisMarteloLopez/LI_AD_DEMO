"""Ingestion pipeline for uploaded PDFs.

Dos verbos:
  - `ingest_file`: pipeline completo (MinerU OCR -> JSONL -> filter -> chunker -> parquet).
    Lo dispara la subida o la UI para PENDING/FAILED.
  - `rechunk_file`: salta MinerU, lee el JSONL cacheado y vuelve a
    correr filtros + chunker con el profile actual de la coleccion.
    Lo dispara la UI tras cambiar Settings, para aplicar el profile
    nuevo a ficheros ya ingestados sin re-OCR.

Solo `ingest_file` toca ingest_status. `rechunk_file` deja el
fichero en su estado (tipicamente DONE) — el OCR no ha cambiado.
"""
from __future__ import annotations

import io
import json
import logging
import os
from typing import Callable

from botocore.exceptions import ClientError

from admin.collections import files as files_svc
from admin.collections import service as coll_service
from admin.collections.files import IngestionStatus, sanitize_filename
from admin.collections.models import IngestProfile
from admin.ingest.chunker import chunk_text_blocks
from admin.ingest.chunks_io import write_chunks
from admin.ingest.content_filters import (
    apply_profile_chunk_filters,
    apply_profile_filters,
)

logger = logging.getLogger("admin.ingest.service")

OCR_SUBPREFIX = "ocr"
TEXT_JSONL = "text.jsonl"

# Tipo del runner: recibe (client, bucket, prefix, collection_id, filename)
# y produce los outputs en MinIO. En 1.B.1 es un no-op.
RunnerFn = Callable[[object, str, str, str, str], None]


def _noop_runner(client, bucket: str, prefix: str, collection_id: str, filename: str) -> None:
    logger.info("ingest stub run collection=%s file=%s", collection_id, filename)


def _stem(filename: str) -> str:
    base = os.path.basename(filename)
    stem, _, _ = base.rpartition(".")
    return stem or base


def _jsonl_key(prefix: str, collection_id: str, filename: str) -> str:
    stem = _stem(sanitize_filename(filename))
    return f"{prefix}/{collection_id}/{OCR_SUBPREFIX}/{stem}/{TEXT_JSONL}"


def ingest_file(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    filename: str,
    runner: RunnerFn = _noop_runner,
) -> IngestionStatus:
    """Run the ingestion pipeline for a single file.

    Transitions its metadata through RUNNING and terminates in DONE or FAILED.
    `runner` is the actual work; injected so tests and 1.B.2 can swap it.
    """
    files_svc.set_ingest_status(
        client, bucket=bucket, prefix=prefix,
        collection_id=collection_id, filename=filename,
        status=IngestionStatus.RUNNING,
    )
    try:
        runner(client, bucket, prefix, collection_id, filename)
    except Exception as exc:
        logger.exception(
            "ingest failed collection=%s file=%s", collection_id, filename,
        )
        files_svc.set_ingest_status(
            client, bucket=bucket, prefix=prefix,
            collection_id=collection_id, filename=filename,
            status=IngestionStatus.FAILED,
            error=str(exc),
        )
        return IngestionStatus.FAILED

    files_svc.set_ingest_status(
        client, bucket=bucket, prefix=prefix,
        collection_id=collection_id, filename=filename,
        status=IngestionStatus.DONE,
    )
    return IngestionStatus.DONE


def rechunk_file(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    filename: str,
) -> bool:
    """Re-run filter + chunker desde el text.jsonl cacheado, sin MinerU.

    Lee el profile actual de la coleccion, aplica los filtros block-level
    sobre el JSONL persistido por una ingesta previa, vuelve a chunkear,
    aplica los filtros chunk-level, y sobreescribe el parquet de chunks.

    No toca `ingest_status` — el OCR cacheado no cambia, el fichero
    sigue en su estado actual (tipicamente DONE).

    Idempotente y silencioso ante condiciones que harian no-op:
      - Coleccion no existe -> warning + False.
      - JSONL no existe (fichero nunca ingestado o cache borrado) -> warning + False.
      - Excepciones inesperadas se propagan al caller (background task).

    Devuelve True si se reescribio el parquet, False si fue no-op.
    """
    coll = coll_service.get(
        client, bucket=bucket, prefix=prefix, collection_id=collection_id,
    )
    if coll is None:
        logger.warning(
            "rechunk_file: collection missing id=%s", collection_id,
        )
        return False
    profile = coll.ingest_profile

    sanitized = sanitize_filename(filename)
    jsonl_key = _jsonl_key(prefix, collection_id, sanitized)
    try:
        obj = client.get_object(Bucket=bucket, Key=jsonl_key)
    except ClientError:
        logger.warning(
            "rechunk_file: jsonl cache missing key=%s", jsonl_key,
        )
        return False
    raw_body = obj["Body"].read()
    text = raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray)) else str(raw_body)

    blocks = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            blocks.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            # Linea malformada — se ignora, el JSONL podria tener un final corrupto.
            continue

    filtered = apply_profile_filters(blocks, profile)
    raw_chunks = chunk_text_blocks(
        filtered,
        collection_id=collection_id,
        source_file=sanitized,
        target_tokens=profile.target_tokens,
        overlap_tokens=profile.overlap_tokens,
    )
    chunks = apply_profile_chunk_filters(raw_chunks, profile)

    stem = _stem(sanitized)
    write_chunks(
        client, bucket=bucket, prefix=prefix,
        collection_id=collection_id, filename_stem=stem, chunks=chunks,
    )
    logger.info(
        "rechunked collection=%s file=%s blocks=%d kept=%d chunks=%d",
        collection_id, filename, len(blocks), len(filtered), len(chunks),
    )
    return True
