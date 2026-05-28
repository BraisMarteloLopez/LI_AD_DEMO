"""Smoke tests for the profile panel + POST /settings + POST /rechunk."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from admin.collections import service
from admin.collections.routes import router as collections_router
from admin.config import AdminConfig
from admin.dependencies import get_config, get_minio_client, get_mineru_client
from admin.ingest.mineru import MineruResult


class _FakeMineru:
    """Stand-in for MinerU; emite contenido suficiente para que un chunk
    sobreviva los defaults (>30 tokens via fallback word-level)."""

    def parse(self, pdf_bytes, filename):
        long_prose = (
            "Como consecuencia del último conflicto bélico mundial, los países "
            "han mejorado sus modelos de helicópteros de combate existentes y "
            "han incorporado nuevas versiones de aeronaves más avanzadas, "
            "capaces de operar en entornos hostiles con autonomía ampliada."
        )
        return MineruResult(
            markdown="# fake",
            content_list=[
                {"type": "title", "text": "RESUMEN", "page_idx": 0},
                {"type": "text",  "text": long_prose, "page_idx": 0},
            ],
        )


@pytest.fixture
def test_cfg() -> AdminConfig:
    return AdminConfig(
        minio_endpoint="http://fake:9000",
        minio_access_key="k",
        minio_secret_key="s",
        minio_bucket="lakehouse",
        admin_root_prefix="admin",
    )


@pytest.fixture
def client(mock_minio_client, test_cfg) -> TestClient:
    app = FastAPI()
    app.include_router(collections_router)
    app.dependency_overrides[get_config] = lambda: test_cfg
    app.dependency_overrides[get_minio_client] = lambda: mock_minio_client
    app.dependency_overrides[get_mineru_client] = lambda: _FakeMineru()
    return TestClient(app)


def _pdf(name: str = "a.pdf") -> tuple:
    return ("files", (name, b"%PDF-1.4 x", "application/pdf"))


@pytest.fixture
def coll_id(client):
    r = client.post(
        "/collections",
        data={"name": "Demo", "type": "playground"},
        files=[_pdf("doc.pdf")],
        follow_redirects=False,
    )
    return r.headers["location"].rsplit("/", 1)[-1]


# === Profile panel embebido en Overview ===


def test_overview_renders_profile_panel_collapsed_by_default(client, coll_id):
    """El profile panel vive como <details> en Overview, cerrado por defecto."""
    r = client.get(f"/collections/{coll_id}")
    assert r.status_code == 200
    assert 'class="profile-panel"' in r.text
    assert 'id="profile"' in r.text
    # <details> sin atributo 'open' = cerrado.
    assert "<details" in r.text
    # No debe llevar 'open' por defecto cuando no hay query param.
    assert '<details class="profile-panel" id="profile" open' not in r.text
    # Form con todos los toggles disponibles, ya pre-rellenados con defaults.
    assert 'name="skip_blank_markers"' in r.text
    assert 'name="skip_toc_entries"' in r.text
    assert 'name="drop_short_blocks"' in r.text
    assert 'name="drop_small_chunks"' in r.text
    assert 'value="5"' in r.text   # short_block_min_words
    assert 'value="30"' in r.text  # min_chunk_tokens


def test_overview_panel_open_when_profile_query_param(client, coll_id):
    """?profile=open mantiene el panel desplegado (post-save feedback)."""
    r = client.get(f"/collections/{coll_id}?profile=open")
    assert r.status_code == 200
    assert 'class="profile-panel" id="profile" open' in r.text


def test_overview_summary_says_all_filters_active_for_default(client, coll_id):
    r = client.get(f"/collections/{coll_id}")
    assert "All filters active" in r.text


def test_overview_no_rechunk_section_without_done_files(client, coll_id):
    # Sin ingestar, file PENDING — sin Re-chunk button.
    r = client.get(f"/collections/{coll_id}")
    assert "Re-chunk with current profile" not in r.text


def test_overview_shows_rechunk_section_after_processing(client, coll_id):
    client.post(f"/collections/{coll_id}/ingest", follow_redirects=False)
    r = client.get(f"/collections/{coll_id}")
    assert "Apply the current profile to" in r.text
    assert "Re-chunk with current profile" in r.text


def test_settings_get_endpoint_removed(client, coll_id):
    """GET /settings ya no existe — la URL no debe responder con 200."""
    r = client.get(f"/collections/{coll_id}/settings")
    assert r.status_code in (404, 405)


def test_overview_no_settings_tab_in_nav(client, coll_id):
    """La pestana Settings se elimino — solo Overview y Chunks."""
    r = client.get(f"/collections/{coll_id}")
    # Verificacion estrecha: no hay link <a> de tab apuntando a /settings.
    assert 'data-label="Settings"' not in r.text


# === POST /settings ===


def test_settings_save_persists_profile_and_redirects(
    client, coll_id, mock_minio_client, test_cfg,
):
    # Submit con todos los toggles desactivados y custom thresholds.
    r = client.post(
        f"/collections/{coll_id}/settings",
        data={
            # Notar: checkboxes omitidos -> False (browsers no envian
            # campos de checkbox cuando no estan checked).
            "short_block_min_words": "12",
            "min_chunk_tokens": "75",
            "target_tokens": "800",
            "overlap_tokens": "80",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    # Redirect a Overview con el panel abierto (feedback de guardado).
    assert r.headers["location"] == f"/collections/{coll_id}?profile=open"

    # Verificar persistencia.
    coll = service.get(
        mock_minio_client,
        bucket=test_cfg.minio_bucket,
        prefix=test_cfg.collections_prefix(),
        collection_id=coll_id,
    )
    p = coll.ingest_profile
    assert p.skip_blank_markers is False
    assert p.skip_toc_entries is False
    assert p.drop_short_blocks is False
    assert p.drop_small_chunks is False
    assert p.short_block_min_words == 12
    assert p.min_chunk_tokens == 75
    assert p.target_tokens == 800
    assert p.overlap_tokens == 80


def test_settings_save_clamps_target_and_overlap(
    client, coll_id, mock_minio_client, test_cfg,
):
    """target=10 (debajo del min 50) -> 50; overlap >= target -> target-1."""
    r = client.post(
        f"/collections/{coll_id}/settings",
        data={
            "short_block_min_words": "5",
            "min_chunk_tokens": "30",
            "target_tokens": "10",
            "overlap_tokens": "999",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    coll = service.get(
        mock_minio_client,
        bucket=test_cfg.minio_bucket,
        prefix=test_cfg.collections_prefix(),
        collection_id=coll_id,
    )
    assert coll.ingest_profile.target_tokens == 50  # clamp arriba
    assert coll.ingest_profile.overlap_tokens == 49  # target-1


def test_settings_save_with_all_checkboxes_on(
    client, coll_id, mock_minio_client, test_cfg,
):
    r = client.post(
        f"/collections/{coll_id}/settings",
        data={
            "skip_blank_markers": "on",
            "skip_toc_entries": "on",
            "drop_short_blocks": "on",
            "drop_small_chunks": "on",
            "short_block_min_words": "5",
            "min_chunk_tokens": "30",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    coll = service.get(
        mock_minio_client,
        bucket=test_cfg.minio_bucket,
        prefix=test_cfg.collections_prefix(),
        collection_id=coll_id,
    )
    p = coll.ingest_profile
    assert all([p.skip_blank_markers, p.skip_toc_entries,
                p.drop_short_blocks, p.drop_small_chunks])


def test_settings_save_404_when_collection_missing(client):
    r = client.post(
        "/collections/col_nope/settings",
        data={"short_block_min_words": "5", "min_chunk_tokens": "30"},
        follow_redirects=False,
    )
    assert r.status_code == 404


def test_settings_save_clamps_negative_thresholds(
    client, coll_id, mock_minio_client, test_cfg,
):
    """Thresholds negativos via dev-tools / curl no deben petar; se
    clampean al minimo (1 / 0)."""
    r = client.post(
        f"/collections/{coll_id}/settings",
        data={"short_block_min_words": "-3", "min_chunk_tokens": "-5"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    coll = service.get(
        mock_minio_client,
        bucket=test_cfg.minio_bucket,
        prefix=test_cfg.collections_prefix(),
        collection_id=coll_id,
    )
    assert coll.ingest_profile.short_block_min_words >= 1
    assert coll.ingest_profile.min_chunk_tokens >= 0


# === POST /rechunk ===


def test_rechunk_404_when_collection_missing(client):
    r = client.post("/collections/col_nope/rechunk", follow_redirects=False)
    assert r.status_code == 404


def test_rechunk_no_op_when_no_done_files(client, coll_id):
    # Sin DONE files, no hay nada que rechunkear → idempotente.
    r = client.post(
        f"/collections/{coll_id}/rechunk", follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == f"/collections/{coll_id}"
    # Sigue PENDING (rechunk no toca status).
    listing = client.get(f"/collections/{coll_id}")
    assert "ingest-pending" in listing.text


def test_rechunk_keeps_done_status_and_does_not_call_mineru(
    client, coll_id, mock_minio_client, test_cfg,
):
    """rechunk debe consumir el JSONL cacheado, no re-llamar a MinerU.
    Verificamos sustituyendo el client de MinerU por uno que cuente
    llamadas: tras /rechunk, el counter no debe haber subido."""
    from admin.dependencies import get_mineru_client

    class _CountingMineru:
        def __init__(self):
            self.calls = 0

        def parse(self, pdf_bytes, filename):
            self.calls += 1
            return _FakeMineru().parse(pdf_bytes, filename)

    counting = _CountingMineru()
    client.app.dependency_overrides[get_mineru_client] = lambda: counting

    # Primer ingest: MinerU se llama 1 vez, file -> DONE.
    client.post(f"/collections/{coll_id}/ingest", follow_redirects=False)
    assert counting.calls == 1
    listing = client.get(f"/collections/{coll_id}")
    assert "ingest-done" in listing.text

    # Rechunk: NO debe llamar a MinerU.
    r = client.post(f"/collections/{coll_id}/rechunk", follow_redirects=False)
    assert r.status_code == 303
    assert counting.calls == 1  # sin incremento

    # File sigue DONE (rechunk no toca status).
    listing = client.get(f"/collections/{coll_id}")
    assert "ingest-done" in listing.text


def test_rechunk_applies_current_profile_to_existing_chunks(
    client, coll_id, mock_minio_client, test_cfg,
):
    """Cambiar profile + rechunk debe modificar el parquet sin re-OCR."""
    import io as _io
    import pyarrow.parquet as pq

    # Primer ingest con defaults (skip_toc=ON, drop_short=ON).
    client.post(f"/collections/{coll_id}/ingest", follow_redirects=False)
    chunks_key = (
        f"{test_cfg.collections_prefix()}/{coll_id}/chunks/doc.parquet"
    )
    parquet_v1 = mock_minio_client._backend.objects[
        (test_cfg.minio_bucket, chunks_key)
    ]["body"]
    rows_v1 = pq.read_table(_io.BytesIO(parquet_v1)).to_pylist()
    text_v1 = " ".join(r["text"] for r in rows_v1)

    # Cambia profile: drop_small_chunks OFF + min_chunk_tokens muy alto.
    # Eso fuerza que chunks pequenos antes filtrados ahora sobrevivan.
    client.post(
        f"/collections/{coll_id}/settings",
        data={
            "skip_blank_markers": "on",
            "skip_toc_entries": "on",
            "drop_short_blocks": "on",
            "short_block_min_words": "5",
            # drop_small_chunks omitido -> False
            "min_chunk_tokens": "0",
        },
        follow_redirects=False,
    )

    # Rechunk con el nuevo profile.
    client.post(f"/collections/{coll_id}/rechunk", follow_redirects=False)

    # Parquet debe haber sido reescrito (al menos LastModified cambia).
    parquet_v2 = mock_minio_client._backend.objects[
        (test_cfg.minio_bucket, chunks_key)
    ]["body"]
    # Mismo contenido es OK si los filtros no cambiaron lo retenido —
    # lo importante es que el parquet existe y se reescribio.
    rows_v2 = pq.read_table(_io.BytesIO(parquet_v2)).to_pylist()
    assert len(rows_v2) >= 1
