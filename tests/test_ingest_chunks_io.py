"""Round-trip tests for the chunks parquet writer."""
from __future__ import annotations

import io

import pyarrow.parquet as pq

from admin.ingest.chunker import Chunk
from admin.ingest.chunks_io import (
    CHUNKS_SCHEMA,
    PARQUET_CONTENT_TYPE,
    chunks_key,
    write_chunks,
)


def _sample_chunks():
    return [
        Chunk(
            chunk_id="Libro:00000",
            collection_id="col_x",
            source_file="Libro.pdf",
            page_start=1, page_end=2,
            block_types=["title", "text"],
            text="Intro\n\nbody",
            token_count=4,
        ),
        Chunk(
            chunk_id="Libro:00001",
            collection_id="col_x",
            source_file="Libro.pdf",
            page_start=3, page_end=3,
            block_types=["text"],
            text="segundo",
            token_count=2,
        ),
    ]


def test_write_chunks_persists_parquet_under_chunks_prefix(
    mock_minio_client, bucket,
):
    key = write_chunks(
        mock_minio_client,
        bucket=bucket, prefix="admin/collections",
        collection_id="col_x", filename_stem="Libro",
        chunks=_sample_chunks(),
    )
    assert key == "admin/collections/col_x/chunks/Libro.parquet"
    rec = mock_minio_client._backend.objects[(bucket, key)]
    assert rec["content_type"] == PARQUET_CONTENT_TYPE


def test_parquet_roundtrip_preserves_all_fields(mock_minio_client, bucket):
    chunks = _sample_chunks()
    key = write_chunks(
        mock_minio_client,
        bucket=bucket, prefix="admin/collections",
        collection_id="col_x", filename_stem="Libro",
        chunks=chunks,
    )
    raw = mock_minio_client._backend.objects[(bucket, key)]["body"]
    table = pq.read_table(io.BytesIO(raw))

    assert table.schema.equals(CHUNKS_SCHEMA, check_metadata=False)
    rows = table.to_pylist()
    assert len(rows) == 2
    assert rows[0] == {
        "chunk_id": "Libro:00000",
        "collection_id": "col_x",
        "source_file": "Libro.pdf",
        "page_start": 1,
        "page_end": 2,
        "block_types": ["title", "text"],
        "text": "Intro\n\nbody",
        "token_count": 4,
    }
    assert rows[1]["chunk_id"] == "Libro:00001"
    assert rows[1]["block_types"] == ["text"]


def test_write_chunks_on_empty_list_still_writes_valid_parquet(
    mock_minio_client, bucket,
):
    key = write_chunks(
        mock_minio_client,
        bucket=bucket, prefix="admin/collections",
        collection_id="col_x", filename_stem="Empty",
        chunks=[],
    )
    raw = mock_minio_client._backend.objects[(bucket, key)]["body"]
    table = pq.read_table(io.BytesIO(raw))
    assert table.num_rows == 0
    assert table.schema.equals(CHUNKS_SCHEMA, check_metadata=False)


def test_chunks_key_format():
    assert (
        chunks_key("admin/collections", "col_x", "Libro")
        == "admin/collections/col_x/chunks/Libro.parquet"
    )
