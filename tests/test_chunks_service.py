"""Tests for the chunks reader service.

Round-trip via the existing writer (admin/ingest/chunks_io.write_chunks)
para no acoplar el test al schema concreto: si manana cambia, el writer
se ajusta y este test solo necesita que ambos coincidan en runtime.
"""
from __future__ import annotations

import io

import pyarrow as pa
import pyarrow.parquet as pq

from admin.chunks import service as chunks_svc
from admin.chunks.models import Chunk as ReadChunk
from admin.ingest.chunker import Chunk as WriterChunk
from admin.ingest.chunks_io import write_chunks


def _seed(client, bucket, prefix, collection_id, filename_stem, chunks):
    write_chunks(
        client,
        bucket=bucket, prefix=prefix,
        collection_id=collection_id, filename_stem=filename_stem,
        chunks=chunks,
    )


def _wc(stem, idx, page_start, page_end, types=("text",), text="t", tokens=10):
    return WriterChunk(
        chunk_id=f"{stem}:{idx:05d}",
        collection_id="col_x",
        source_file=f"{stem}.pdf",
        page_start=page_start, page_end=page_end,
        block_types=list(types), text=text, token_count=tokens,
    )


def test_read_chunks_empty_collection(mock_minio_client, bucket, admin_prefix):
    chunks = chunks_svc.read_chunks(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    assert chunks == []


def test_read_chunks_returns_dataclasses_with_all_fields(
    mock_minio_client, bucket, admin_prefix,
):
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "Libro", [
        _wc("Libro", 0, 1, 2, types=("title", "text"), text="Intro body", tokens=4),
        _wc("Libro", 1, 3, 3, types=("text",), text="segundo", tokens=2),
    ])
    chunks = chunks_svc.read_chunks(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    assert len(chunks) == 2
    assert all(isinstance(c, ReadChunk) for c in chunks)
    first = chunks[0]
    assert first.chunk_id == "Libro:00000"
    assert first.source_file == "Libro.pdf"
    assert first.page_start == 1 and first.page_end == 2
    assert first.block_types == ("title", "text")
    assert first.text == "Intro body"
    assert first.token_count == 4


def test_read_chunks_aggregates_multiple_parquets_sorted(
    mock_minio_client, bucket, admin_prefix,
):
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "Beta", [
        _wc("Beta", 0, 5, 5, text="b5"),
    ])
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "Alpha", [
        _wc("Alpha", 1, 2, 2, text="a2"),
        _wc("Alpha", 0, 1, 1, text="a1"),
    ])
    chunks = chunks_svc.read_chunks(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    # Sort: source_file ASC, page_start ASC, chunk_id ASC
    assert [c.chunk_id for c in chunks] == ["Alpha:00000", "Alpha:00001", "Beta:00000"]


def test_read_chunks_filters_by_source_file(
    mock_minio_client, bucket, admin_prefix,
):
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "A", [
        _wc("A", 0, 1, 1, text="a"),
    ])
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "B", [
        _wc("B", 0, 1, 1, text="b"),
    ])
    chunks = chunks_svc.read_chunks(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
        source_file="A",
    )
    assert len(chunks) == 1
    assert chunks[0].source_file == "A.pdf"


def test_list_source_files_returns_sorted_unique_stems(
    mock_minio_client, bucket, admin_prefix,
):
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "B", [_wc("B", 0, 1, 1)])
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "A", [_wc("A", 0, 1, 1)])
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "A", [_wc("A", 1, 2, 2)])  # overwrite
    files = chunks_svc.list_source_files(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    assert files == ["A", "B"]


def test_list_source_files_empty_when_no_chunks(
    mock_minio_client, bucket, admin_prefix,
):
    files = chunks_svc.list_source_files(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    assert files == []


def test_read_chunks_skips_malformed_parquet(
    mock_minio_client, bucket, admin_prefix,
):
    # Un parquet valido y otro fichero con extension parquet pero contenido invalido.
    _seed(mock_minio_client, bucket, admin_prefix, "col_x", "Good", [
        _wc("Good", 0, 1, 1, text="ok"),
    ])
    bad_key = f"{admin_prefix}/col_x/chunks/Bad.parquet"
    mock_minio_client.put_object(Bucket=bucket, Key=bad_key, Body=b"not a parquet")
    chunks = chunks_svc.read_chunks(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    assert len(chunks) == 1
    assert chunks[0].source_file == "Good.pdf"


def test_read_chunks_skips_rows_with_missing_columns(
    mock_minio_client, bucket, admin_prefix,
):
    # Construir un parquet con schema parcial — falta `text` y `token_count`.
    table = pa.table({
        "chunk_id":      ["X:0"],
        "collection_id": ["col_x"],
        "source_file":   ["X.pdf"],
        "page_start":    pa.array([1], type=pa.int32()),
        "page_end":      pa.array([1], type=pa.int32()),
        "block_types":   [["text"]],
    })
    buf = io.BytesIO()
    pq.write_table(table, buf)
    key = f"{admin_prefix}/col_x/chunks/X.parquet"
    mock_minio_client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())

    chunks = chunks_svc.read_chunks(
        mock_minio_client,
        bucket=bucket, prefix=admin_prefix, collection_id="col_x",
    )
    # text y token_count vienen con defaults — no se descarta la fila.
    assert len(chunks) == 1
    assert chunks[0].text == ""
    assert chunks[0].token_count == 0


def test_chunk_text_snippet_truncates_long_text():
    c = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=1, page_end=1, block_types=("text",),
        text="a" * 500, token_count=100,
    )
    s = c.text_snippet(max_chars=50)
    assert len(s) == 50
    assert s.endswith("…")


def test_chunk_text_snippet_keeps_short_text():
    c = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=1, page_end=1, block_types=("text",),
        text="hola", token_count=1,
    )
    assert c.text_snippet() == "hola"


def test_chunk_page_label_single_vs_range():
    c1 = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=3, page_end=3,
    )
    c2 = ReadChunk(
        chunk_id="X:1", collection_id="col_x", source_file="X.pdf",
        page_start=3, page_end=5,
    )
    assert c1.page_label == "3"
    assert c2.page_label == "3–5"


def test_block_types_display_dedups_and_counts():
    c = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=1, page_end=1,
        block_types=("title", "text", "text"),
    )
    assert c.block_types_display == [("title", 1), ("text", 2)]


def test_block_types_display_preserves_first_seen_order():
    c = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=1, page_end=1,
        block_types=("text", "title", "text", "title"),
    )
    assert c.block_types_display == [("text", 2), ("title", 2)]


def test_block_types_display_single_type():
    c = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=1, page_end=1,
        block_types=("text", "text", "text", "text"),
    )
    assert c.block_types_display == [("text", 4)]


def test_block_types_display_empty():
    c = ReadChunk(
        chunk_id="X:0", collection_id="col_x", source_file="X.pdf",
        page_start=1, page_end=1,
    )
    assert c.block_types_display == []
