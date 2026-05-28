"""Parquet schema + writer for chunks produced by admin/ingest/chunker.

El schema es provisional: cuando CH_LIRAG publique su contrato definitivo
se sustituye este módulo (o se alinea). Hasta entonces, este es el único
sitio donde el shape del parquet se decide.
"""
from __future__ import annotations

import io
from typing import List

import pyarrow as pa
import pyarrow.parquet as pq

from admin.ingest.chunker import Chunk

CHUNKS_SUBPREFIX = "chunks"
PARQUET_CONTENT_TYPE = "application/vnd.apache.parquet"

CHUNKS_SCHEMA = pa.schema([
    pa.field("chunk_id",      pa.string()),
    pa.field("collection_id", pa.string()),
    pa.field("source_file",   pa.string()),
    pa.field("page_start",    pa.int32()),
    pa.field("page_end",      pa.int32()),
    pa.field("block_types",   pa.list_(pa.string())),
    pa.field("text",          pa.string()),
    pa.field("token_count",   pa.int32()),
])


def chunks_key(prefix: str, collection_id: str, filename_stem: str) -> str:
    return f"{prefix}/{collection_id}/{CHUNKS_SUBPREFIX}/{filename_stem}.parquet"


def _to_table(chunks: List[Chunk]) -> pa.Table:
    return pa.table(
        {
            "chunk_id":      [c.chunk_id for c in chunks],
            "collection_id": [c.collection_id for c in chunks],
            "source_file":   [c.source_file for c in chunks],
            "page_start":    pa.array([c.page_start for c in chunks], type=pa.int32()),
            "page_end":      pa.array([c.page_end   for c in chunks], type=pa.int32()),
            "block_types":   [c.block_types for c in chunks],
            "text":          [c.text for c in chunks],
            "token_count":   pa.array([c.token_count for c in chunks], type=pa.int32()),
        },
        schema=CHUNKS_SCHEMA,
    )


def write_chunks(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    filename_stem: str,
    chunks: List[Chunk],
) -> str:
    """Write `chunks` as a parquet file to MinIO. Returns the object key."""
    table = _to_table(chunks)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    key = chunks_key(prefix, collection_id, filename_stem)
    client.put_object(
        Bucket=bucket, Key=key, Body=buf.getvalue(),
        ContentType=PARQUET_CONTENT_TYPE,
    )
    return key
