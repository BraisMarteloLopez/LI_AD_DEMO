"""Tests for admin.ingest.service.rechunk_file (re-chunking from JSONL cache)."""
from __future__ import annotations

import io as _io
import json

import pyarrow.parquet as pq

from admin.collections import service as coll_service
from admin.collections.files import IngestionStatus
from admin.collections.models import CollectionType, IngestProfile
from admin.ingest import service as ingest_svc


def _seed_collection(client, bucket, prefix, name="C"):
    return coll_service.create(
        client, bucket=bucket, prefix=prefix,
        name=name, type=CollectionType.PLAYGROUND,
    )


def _seed_jsonl(client, bucket, prefix, collection_id, filename, blocks):
    # Escribe text.jsonl directamente bajo ocr/{stem}/.
    stem = filename.rsplit(".", 1)[0]
    body = "\n".join(json.dumps(b, ensure_ascii=False) for b in blocks)
    key = f"{prefix}/{collection_id}/ocr/{stem}/text.jsonl"
    client.put_object(
        Bucket=bucket, Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )


def _read_chunks(client, bucket, prefix, collection_id, stem):
    key = f"{prefix}/{collection_id}/chunks/{stem}.parquet"
    raw = client._backend.objects[(bucket, key)]["body"]
    return pq.read_table(_io.BytesIO(raw)).to_pylist()


def test_rechunk_returns_false_when_collection_missing(
    mock_minio_client, bucket, admin_prefix,
):
    out = ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id="col_nope", filename="doc.pdf",
    )
    assert out is False


def test_rechunk_returns_false_when_jsonl_missing(
    mock_minio_client, bucket, admin_prefix,
):
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)
    out = ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    assert out is False
    # No parquet escrito.
    chunks_prefix = f"{admin_prefix}/{coll.id}/chunks/"
    assert not any(
        k.startswith(chunks_prefix)
        for (b, k) in mock_minio_client._backend.objects
    )


def test_rechunk_writes_parquet_from_jsonl_cache(
    mock_minio_client, bucket, admin_prefix,
):
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)
    long_prose = (
        "Como consecuencia del último conflicto bélico, los países "
        "han mejorado sus modelos de helicópteros existentes y han "
        "incorporado nuevas versiones de combate más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía ampliada."
    )
    _seed_jsonl(mock_minio_client, bucket, admin_prefix, coll.id, "doc.pdf", [
        {"page": 1, "type": "title", "text": "RESUMEN"},
        {"page": 1, "type": "text",  "text": long_prose},
    ])

    out = ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    assert out is True

    rows = _read_chunks(mock_minio_client, bucket, admin_prefix, coll.id, "doc")
    assert len(rows) >= 1
    chunk_text = " ".join(r["text"] for r in rows)
    assert "RESUMEN" in chunk_text
    assert "Como consecuencia" in chunk_text


def test_rechunk_honors_collection_profile(
    mock_minio_client, bucket, admin_prefix,
):
    """Cambia profile: skip_toc=False, drop_short=False, drop_small=False.
    Tras rechunk, los bloques que defaults filtrarian sobreviven."""
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)
    coll_service.update_profile(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id,
        profile=IngestProfile(
            skip_blank_markers=True,
            skip_toc_entries=False,
            drop_short_blocks=False,
            drop_small_chunks=False,
        ),
    )
    _seed_jsonl(mock_minio_client, bucket, admin_prefix, coll.id, "doc.pdf", [
        {"page": 1, "type": "text", "text": "BIBLIOGRAFÍA . . 18"},
    ])

    ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )

    rows = _read_chunks(mock_minio_client, bucket, admin_prefix, coll.id, "doc")
    chunk_text = " ".join(r["text"] for r in rows)
    assert "BIBLIOGRAFÍA" in chunk_text


def test_rechunk_default_profile_filters_toc_and_blank(
    mock_minio_client, bucket, admin_prefix,
):
    """Profile default (todo ON) filtra TOC y blank markers."""
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)
    long_prose = (
        "Como consecuencia del último conflicto bélico mundial, los países "
        "han mejorado sus modelos de helicópteros de combate existentes y "
        "han incorporado nuevas versiones de aeronaves más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía ampliada y "
        "sistemas de protección activos contra misiles antiaéreos."
    )
    _seed_jsonl(mock_minio_client, bucket, admin_prefix, coll.id, "doc.pdf", [
        {"page": 1, "type": "text", "text": "Página en blanco"},
        {"page": 1, "type": "text", "text": "BIBLIOGRAFÍA . . 18"},
        {"page": 2, "type": "title", "text": "RESUMEN"},
        {"page": 2, "type": "text", "text": long_prose},
    ])
    ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    rows = _read_chunks(mock_minio_client, bucket, admin_prefix, coll.id, "doc")
    chunk_text = " ".join(r["text"] for r in rows)
    assert "Página en blanco" not in chunk_text
    assert "BIBLIOGRAFÍA" not in chunk_text
    assert "RESUMEN" in chunk_text


def test_rechunk_handles_malformed_jsonl_lines(
    mock_minio_client, bucket, admin_prefix,
):
    """Linea malformada en medio del JSONL no debe romper el rechunk —
    se ignora y siguen las demas."""
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)
    long_prose = (
        "Como consecuencia del último conflicto bélico mundial, los países "
        "han mejorado sus modelos de helicópteros de combate existentes y "
        "han incorporado nuevas versiones de aeronaves más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía ampliada y "
        "sistemas de protección activos contra misiles antiaéreos."
    )
    # JSONL con una linea corrupta entre 2 lineas validas.
    body = "\n".join([
        json.dumps({"page": 1, "type": "title", "text": "RESUMEN"}),
        "this is not valid json {{",
        json.dumps({"page": 1, "type": "text", "text": long_prose}),
    ])
    key = f"{admin_prefix}/{coll.id}/ocr/doc/text.jsonl"
    mock_minio_client.put_object(
        Bucket=bucket, Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )

    out = ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    assert out is True
    rows = _read_chunks(mock_minio_client, bucket, admin_prefix, coll.id, "doc")
    chunk_text = " ".join(r["text"] for r in rows)
    assert "RESUMEN" in chunk_text
    assert "Como consecuencia" in chunk_text


def test_rechunk_uses_profile_target_and_overlap(
    mock_minio_client, bucket, admin_prefix,
):
    """Cambiar target_tokens en el profile y re-chunkear produce mas/menos
    chunks segun el nuevo tamano objetivo. drop_small_chunks OFF para
    que el filtro post-chunker no enmascare el efecto."""
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)
    long_prose = (
        "Como consecuencia del último conflicto bélico mundial, los países "
        "han mejorado sus modelos de helicópteros de combate existentes y "
        "han incorporado nuevas versiones de aeronaves más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía ampliada y "
        "sistemas de protección activos contra misiles antiaéreos."
    )
    _seed_jsonl(mock_minio_client, bucket, admin_prefix, coll.id, "doc.pdf", [
        {"page": 1, "type": "text", "text": long_prose},
    ])

    # Profile target=500 (default) -> el bloque entero cabe en 1 chunk.
    coll_service.update_profile(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id,
        profile=IngestProfile(drop_small_chunks=False),  # default target=500
    )
    ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    rows_target_500 = _read_chunks(mock_minio_client, bucket, admin_prefix, coll.id, "doc")

    # Profile target=20 -> el mismo texto ahora se parte en muchos chunks.
    coll_service.update_profile(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id,
        profile=IngestProfile(
            drop_small_chunks=False,
            target_tokens=20,
            overlap_tokens=5,
        ),
    )
    ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    rows_target_20 = _read_chunks(mock_minio_client, bucket, admin_prefix, coll.id, "doc")

    assert len(rows_target_20) > len(rows_target_500)


def test_rechunk_does_not_change_file_status(
    mock_minio_client, bucket, admin_prefix,
):
    """El status del fichero (DONE, PENDING, etc.) no se toca."""
    from admin.collections import files as files_svc
    import io
    coll = _seed_collection(mock_minio_client, bucket, admin_prefix)

    # Subir el PDF y dejarlo en estado DONE.
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
        stream=io.BytesIO(b"%PDF-1.4 stub"),
        content_type="application/pdf",
    )
    files_svc.set_ingest_status(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
        status=IngestionStatus.DONE,
    )
    long_prose = (
        "Como consecuencia del último conflicto bélico mundial, los países "
        "han mejorado sus modelos de helicópteros de combate existentes y "
        "han incorporado nuevas versiones de aeronaves más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía ampliada y "
        "sistemas de protección activos contra misiles antiaéreos."
    )
    _seed_jsonl(mock_minio_client, bucket, admin_prefix, coll.id, "doc.pdf", [
        {"page": 1, "type": "text", "text": long_prose},
    ])

    ingest_svc.rechunk_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, filename="doc.pdf",
    )
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id,
    )
    assert f.ingest_status == IngestionStatus.DONE
