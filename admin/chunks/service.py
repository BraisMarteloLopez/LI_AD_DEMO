"""Read-side service for chunks parquet files in MinIO.

Independiente del writer (`admin/ingest/chunks_io.py`) — el writer
decide schema, este modulo lo consume con tolerancia: si una columna
desaparece o cambia de tipo, los chunks afectados se ignoran y se
loguea, en lugar de petar la pagina.
"""
from __future__ import annotations

import io
import logging
from typing import List, Optional

import pyarrow.parquet as pq
from botocore.exceptions import ClientError

from admin.chunks.models import Chunk

logger = logging.getLogger("admin.chunks.service")

CHUNKS_SUBPREFIX = "chunks"
PARQUET_SUFFIX = ".parquet"


def _chunks_prefix(prefix: str, collection_id: str) -> str:
    return f"{prefix}/{collection_id}/{CHUNKS_SUBPREFIX}/"


def _list_parquet_keys(client, *, bucket: str, prefix: str, collection_id: str) -> List[str]:
    paginator = client.get_paginator("list_objects_v2")
    keys: List[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=_chunks_prefix(prefix, collection_id)):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if key.endswith(PARQUET_SUFFIX):
                keys.append(key)
    keys.sort()
    return keys


def list_source_files(
    client, *, bucket: str, prefix: str, collection_id: str,
) -> List[str]:
    """Return the source_file values discovered under chunks/, sorted.

    Discovery por nombre de fichero parquet — el writer usa
    `{filename_stem}.parquet`, asi que el stem corresponde al PDF
    original sin extension. Mas barato que abrir cada parquet.
    """
    keys = _list_parquet_keys(client, bucket=bucket, prefix=prefix, collection_id=collection_id)
    stems = []
    for key in keys:
        name = key.rsplit("/", 1)[-1]
        if name.endswith(PARQUET_SUFFIX):
            stems.append(name[: -len(PARQUET_SUFFIX)])
    return sorted(set(stems))


def _row_to_chunk(row: dict) -> Optional[Chunk]:
    try:
        block_types = row.get("block_types") or []
        return Chunk(
            chunk_id=str(row["chunk_id"]),
            collection_id=str(row["collection_id"]),
            source_file=str(row["source_file"]),
            page_start=int(row["page_start"]),
            page_end=int(row["page_end"]),
            block_types=tuple(str(t) for t in block_types),
            text=str(row.get("text") or ""),
            token_count=int(row.get("token_count") or 0),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("skip malformed chunk row: %s", exc)
        return None


def _read_parquet_chunks(client, *, bucket: str, key: str) -> List[Chunk]:
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        logger.warning("skip unreadable parquet key=%s err=%s", key, exc)
        return []
    body = resp["Body"].read()
    try:
        table = pq.read_table(io.BytesIO(body))
    except Exception as exc:  # pyarrow throws diversos OSError/ArrowInvalid
        logger.warning("skip malformed parquet key=%s err=%s", key, exc)
        return []
    rows = table.to_pylist()
    chunks: List[Chunk] = []
    for row in rows:
        c = _row_to_chunk(row)
        if c is not None:
            chunks.append(c)
    return chunks


def read_chunks(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    source_file: Optional[str] = None,
) -> List[Chunk]:
    """Read all chunks of a collection, optionally filtered by source_file.

    Orden estable: por source_file ASC, luego page_start ASC, luego
    chunk_id ASC. Es la forma natural de leer un documento.
    """
    keys = _list_parquet_keys(
        client, bucket=bucket, prefix=prefix, collection_id=collection_id,
    )
    if source_file is not None:
        target = f"/{source_file}{PARQUET_SUFFIX}"
        keys = [k for k in keys if k.endswith(target)]
    chunks: List[Chunk] = []
    for key in keys:
        chunks.extend(_read_parquet_chunks(client, bucket=bucket, key=key))
    chunks.sort(key=lambda c: (c.source_file, c.page_start, c.chunk_id))
    return chunks
