"""Tests for admin.ingest.runner (filter + text.jsonl persistence)."""
from __future__ import annotations

import io
import json
from dataclasses import dataclass

import pytest

from admin.collections import files as files_svc
from admin.collections import service
from admin.collections.files import IngestionStatus
from admin.collections.models import CollectionType
from admin.ingest import service as ingest_svc
from admin.ingest.mineru import MineruResult
from admin.ingest.runner import build_runner, filter_blocks


@pytest.fixture
def coll_id(mock_minio_client, bucket, admin_prefix):
    c = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="Runner", type=CollectionType.PLAYGROUND,
    )
    return c.id


def _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, name="a.pdf"):
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename=name,
        stream=io.BytesIO(b"%PDF-1.4 stub"),
        content_type="application/pdf",
    )


@dataclass
class _FakeMineru:
    content_list: list
    md: str = ""
    last_call: dict | None = None

    def parse(self, pdf_bytes: bytes, filename: str) -> MineruResult:
        self.last_call = {"bytes": pdf_bytes, "filename": filename}
        return MineruResult(markdown=self.md, content_list=self.content_list)


class TestFilterBlocks:
    def test_keeps_text_and_title(self):
        out = filter_blocks([
            {"type": "text", "text": "body", "page_idx": 0},
            {"type": "title", "text": "T", "page_idx": 0},
        ])
        assert [b["type"] for b in out] == ["text", "title"]

    def test_drops_image_table_equation(self):
        out = filter_blocks([
            {"type": "image", "text": "x", "page_idx": 0},
            {"type": "table", "text": "x", "page_idx": 0},
            {"type": "equation", "text": "x", "page_idx": 0},
            {"type": "text", "text": "y", "page_idx": 0},
        ])
        assert [b["type"] for b in out] == ["text"]

    def test_drops_empty_text(self):
        out = filter_blocks([
            {"type": "text", "text": "   ", "page_idx": 0},
            {"type": "text", "text": "ok", "page_idx": 0},
        ])
        assert out == [{"page": 1, "type": "text", "text": "ok"}]

    def test_page_idx_is_normalized_to_1_based(self):
        out = filter_blocks([
            {"type": "text", "text": "p1", "page_idx": 0},
            {"type": "text", "text": "p5", "page_idx": 4},
        ])
        assert [b["page"] for b in out] == [1, 5]

    def test_tolerates_missing_page_idx(self):
        out = filter_blocks([{"type": "text", "text": "a"}])
        assert out[0]["page"] == 1

    def test_ignores_non_dict_entries(self):
        out = filter_blocks(["nope", None, {"type": "text", "text": "ok"}])
        assert len(out) == 1

    def test_preserves_bbox_when_present(self):
        out = filter_blocks([
            {"type": "text", "text": "body", "page_idx": 0,
             "bbox": [10.0, 20.0, 100.0, 40.0]},
        ])
        assert out[0]["bbox"] == [10.0, 20.0, 100.0, 40.0]

    def test_preserves_text_level_when_present(self):
        out = filter_blocks([
            {"type": "title", "text": "Heading", "page_idx": 0, "text_level": 1},
        ])
        assert out[0]["text_level"] == 1

    def test_omits_optional_fields_when_absent(self):
        out = filter_blocks([{"type": "text", "text": "ok", "page_idx": 0}])
        # No spurious keys when MinerU no las emite.
        assert out[0] == {"page": 1, "type": "text", "text": "ok"}


def test_runner_writes_text_jsonl_under_ocr_subprefix(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    fake = _FakeMineru(content_list=[
        {"type": "title", "text": "H1", "page_idx": 0},
        {"type": "text",  "text": "body on page 1", "page_idx": 0},
        {"type": "image", "text": "ignored", "page_idx": 0},
        {"type": "text",  "text": "body on page 3", "page_idx": 2},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )

    key = f"{admin_prefix}/{coll_id}/ocr/doc/text.jsonl"
    rec = mock_minio_client._backend.objects[(bucket, key)]
    assert rec["content_type"] == "application/x-ndjson"
    lines = rec["body"].decode("utf-8").splitlines()
    assert [json.loads(l) for l in lines] == [
        {"page": 1, "type": "title", "text": "H1"},
        {"page": 1, "type": "text",  "text": "body on page 1"},
        {"page": 3, "type": "text",  "text": "body on page 3"},
    ]


def test_runner_also_writes_chunks_parquet(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    import io as _io
    import pyarrow.parquet as pq

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    long_prose = (
        "El helicóptero AH-64 Apache es un caza ataque biplaza "
        "desarrollado por Boeing para el Ejército de los Estados Unidos. "
        "Entró en servicio en 1986 y desde entonces ha participado en "
        "numerosos conflictos a lo largo del mundo. Su principal arma es "
        "el cañón M230 de 30 milímetros y misiles AGM-114 Hellfire."
    )
    fake = _FakeMineru(content_list=[
        {"type": "title", "text": "Intro", "page_idx": 0},
        {"type": "text",  "text": long_prose, "page_idx": 0},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )
    key = f"{admin_prefix}/{coll_id}/chunks/doc.parquet"
    raw = mock_minio_client._backend.objects[(bucket, key)]["body"]
    rows = pq.read_table(_io.BytesIO(raw)).to_pylist()
    assert len(rows) >= 1
    assert rows[0]["collection_id"] == coll_id
    assert rows[0]["source_file"] == "doc.pdf"
    assert rows[0]["chunk_id"].startswith("doc:0000")


def test_runner_e2e_marks_file_done(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    fake = _FakeMineru(content_list=[
        {"type": "text", "text": "hello", "page_idx": 0},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.DONE
    assert fake.last_call is not None
    assert fake.last_call["filename"] == "doc.pdf"


def test_runner_mineru_error_marks_failed(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    from admin.ingest.mineru import MineruError

    class _Boom:
        def parse(self, *_a, **_kw):
            raise MineruError("service down")

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(_Boom()),
    )
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.FAILED
    assert f.ingest_error == "service down"


def test_runner_handles_empty_content_list(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "empty.pdf")
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="empty.pdf",
        runner=build_runner(_FakeMineru(content_list=[])),
    )
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.DONE
    key = f"{admin_prefix}/{coll_id}/ocr/empty/text.jsonl"
    assert mock_minio_client._backend.objects[(bucket, key)]["body"] == b""


def test_runner_keeps_raw_blocks_in_jsonl_but_filters_chunks(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    """JSONL = cache crudo de MinerU; chunks = filtrado.

    Si manana cambia el perfil, se re-chunkea desde JSONL sin re-llamar
    al OCR. Por eso JSONL debe contener los bloques que los filtros van
    a tirar (TOC, blank markers).
    """
    import io as _io
    import pyarrow.parquet as pq

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    long_prose = (
        "Como consecuencia del último conflicto bélico, los países "
        "han mejorado sus modelos de helicópteros existentes y han "
        "incorporado nuevas versiones de combate más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía "
        "ampliada y sistemas de protección activos contra misiles."
    )
    fake = _FakeMineru(content_list=[
        {"type": "text",  "text": "Página en blanco intencionadamente", "page_idx": 0},
        {"type": "text",  "text": "BIBLIOGRAFÍA . . 18", "page_idx": 1},
        {"type": "title", "text": "RESUMEN", "page_idx": 2},
        {"type": "text",  "text": long_prose, "page_idx": 2},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )

    # JSONL: los 4 bloques crudos siguen ahi.
    jsonl_key = f"{admin_prefix}/{coll_id}/ocr/doc/text.jsonl"
    lines = mock_minio_client._backend.objects[(bucket, jsonl_key)]["body"].decode().splitlines()
    assert len(lines) == 4
    texts_jsonl = [json.loads(l)["text"] for l in lines]
    assert "Página en blanco intencionadamente" in texts_jsonl
    assert "BIBLIOGRAFÍA . . 18" in texts_jsonl

    # Chunks: blank-marker y TOC desaparecen; queda solo title + prosa larga.
    chunks_key = f"{admin_prefix}/{coll_id}/chunks/doc.parquet"
    raw = mock_minio_client._backend.objects[(bucket, chunks_key)]["body"]
    rows = pq.read_table(_io.BytesIO(raw)).to_pylist()
    chunk_text = " ".join(r["text"] for r in rows)
    assert "Página en blanco" not in chunk_text
    assert "BIBLIOGRAFÍA" not in chunk_text
    assert "Como consecuencia" in chunk_text
    assert "RESUMEN" in chunk_text
    # Tras filtrar 2 bloques noise + chunk size suficiente, el chunk superviviente
    # debe quedar por encima del umbral default_min_chunk_tokens (30).


def test_runner_drops_short_text_blocks_from_chunks_keeps_titles(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    """drop_short_blocks: bloques `text` < 5 palabras fuera; titles dentro."""
    import io as _io
    import pyarrow.parquet as pq

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    long_prose = (
        "Como consecuencia del último conflicto bélico, los países "
        "han mejorado sus modelos de helicópteros existentes y han "
        "incorporado nuevas versiones de combate más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía "
        "ampliada y sistemas de protección activos contra misiles."
    )
    fake = _FakeMineru(content_list=[
        {"type": "title", "text": "1 RESUMEN", "page_idx": 0},
        {"type": "text",  "text": "solo tres palabras", "page_idx": 0},  # 3 -> drop
        {"type": "text",  "text": long_prose, "page_idx": 0},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )
    chunks_key = f"{admin_prefix}/{coll_id}/chunks/doc.parquet"
    raw = mock_minio_client._backend.objects[(bucket, chunks_key)]["body"]
    rows = pq.read_table(_io.BytesIO(raw)).to_pylist()
    chunk_text = " ".join(r["text"] for r in rows)
    assert "RESUMEN" in chunk_text
    assert "solo tres palabras" not in chunk_text
    assert "Como consecuencia" in chunk_text


def test_runner_honors_collection_ingest_profile(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    """Si el profile de la coleccion desactiva un filtro, el bloque
    correspondiente debe llegar al chunk.
    """
    import io as _io
    import pyarrow.parquet as pq

    from admin.collections import service as coll_service_local
    from admin.collections.models import IngestProfile

    # Profile que NO filtra TOC entries y NO descarta chunks pequenos —
    # asi una entrada tipo "BIBLIOGRAFÍA . . 18" sobrevive aunque el
    # chunk resultante sea diminuto.
    coll_service_local.update_profile(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id,
        profile=IngestProfile(
            skip_blank_markers=True,
            skip_toc_entries=False,           # OFF
            drop_short_blocks=False,          # OFF (no umbral de palabras)
            drop_small_chunks=False,          # OFF (no umbral de tokens)
        ),
    )

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    fake = _FakeMineru(content_list=[
        {"type": "text", "text": "BIBLIOGRAFÍA . . 18", "page_idx": 0},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )
    chunks_key = f"{admin_prefix}/{coll_id}/chunks/doc.parquet"
    raw = mock_minio_client._backend.objects[(bucket, chunks_key)]["body"]
    rows = pq.read_table(_io.BytesIO(raw)).to_pylist()
    chunk_text = " ".join(r["text"] for r in rows)
    assert "BIBLIOGRAFÍA" in chunk_text  # llego al chunk porque skip_toc=OFF


def test_runner_uses_profile_target_and_overlap_for_chunker(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    """Profile.target_tokens=10 fuerza chunks pequenos. drop_small_chunks
    y drop_short_blocks OFF para que sobrevivan al filtro post-chunk.
    Resultado: muchos chunks de tamanos cercanos al target.
    """
    import io as _io
    import pyarrow.parquet as pq

    from admin.collections import service as coll_service_local
    from admin.collections.models import IngestProfile

    coll_service_local.update_profile(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id,
        profile=IngestProfile(
            skip_blank_markers=True,
            skip_toc_entries=True,
            drop_short_blocks=False,    # OFF
            drop_small_chunks=False,    # OFF
            target_tokens=20,           # muy pequeno
            overlap_tokens=5,
        ),
    )

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    long_prose = (
        "Como consecuencia del último conflicto bélico mundial, los países "
        "han mejorado sus modelos de helicópteros de combate existentes y "
        "han incorporado nuevas versiones de aeronaves más avanzadas, "
        "capaces de operar en entornos hostiles con autonomía ampliada y "
        "sistemas de protección activos contra misiles antiaéreos."
    )
    fake = _FakeMineru(content_list=[
        {"type": "text", "text": long_prose, "page_idx": 0},
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )
    chunks_key = f"{admin_prefix}/{coll_id}/chunks/doc.parquet"
    raw = mock_minio_client._backend.objects[(bucket, chunks_key)]["body"]
    rows = pq.read_table(_io.BytesIO(raw)).to_pylist()
    # Con target_tokens=20 y un texto de ~40 palabras esperamos al menos
    # 2 chunks (mas con overlap pequeno).
    assert len(rows) >= 2


def test_runner_drops_chunk_when_only_title_remains_after_filter(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    """Safety net post-chunker: si tras filtrar bloques solo queda un
    title corto, el chunk fragmentario (`token_count < 30`) se descarta.
    """
    import io as _io
    import pyarrow.parquet as pq

    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "doc.pdf")
    fake = _FakeMineru(content_list=[
        # Solo un title corto + bloques que el block-filter va a tirar.
        {"type": "title", "text": "RESUMEN", "page_idx": 0},
        {"type": "text",  "text": "muy corto", "page_idx": 0},  # 2 words -> drop
        {"type": "text",  "text": "Página en blanco", "page_idx": 0},  # blank -> drop
    ])
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        runner=build_runner(fake),
    )
    chunks_key = f"{admin_prefix}/{coll_id}/chunks/doc.parquet"
    raw = mock_minio_client._backend.objects[(bucket, chunks_key)]["body"]
    rows = pq.read_table(_io.BytesIO(raw)).to_pylist()
    # El unico chunk era "RESUMEN" solo (~1 token), debajo del umbral 30.
    assert rows == []
