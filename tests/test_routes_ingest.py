"""Smoke tests for the ingestion route (POST /collections/{id}/ingest).

The ingest stub is a no-op runner that flips PENDING -> RUNNING -> DONE.
BackgroundTasks run synchronously under TestClient, so the final state is
observable immediately after the redirect response returns.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from admin.collections.routes import router as collections_router
from admin.config import AdminConfig
from admin.dependencies import get_config, get_minio_client, get_mineru_client
from admin.ingest.mineru import MineruResult


class _FakeMineru:
    """Stand-in for the real MinerU client in route tests.

    Returns a fixed content_list so the runner writes a non-empty jsonl.
    """

    def parse(self, pdf_bytes, filename):
        return MineruResult(
            markdown="# fake",
            content_list=[{"type": "text", "text": "hello", "page_idx": 0}],
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


def test_detail_shows_pending_badge_after_upload(client, coll_id):
    r = client.get(f"/collections/{coll_id}")
    assert r.status_code == 200
    assert 'ingest-pending' in r.text
    # Panel de ingesta visible y con CTA
    assert "Ingestion" in r.text
    assert "Ingest 1 pending" in r.text


def test_ingest_endpoint_marks_file_done(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/ingest", follow_redirects=False,
    )
    assert r.status_code == 303
    detail = client.get(f"/collections/{coll_id}")
    assert 'ingest-done' in detail.text
    # No queda nada que ingestar: no hay CTA de ingest pendientes
    assert "All files processed" in detail.text
    assert "pending" not in detail.text.lower().split("files")[-1]


def test_ingest_endpoint_404_for_unknown_collection(client):
    r = client.post("/collections/col_nope/ingest", follow_redirects=False)
    assert r.status_code == 404


def test_status_partial_returns_panel_and_table_oob(client, coll_id):
    r = client.get(f"/collections/{coll_id}/_status")
    assert r.status_code == 200
    # El panel se incluye sin OOB (es el target de la swap principal).
    assert 'id="ingest-panel"' in r.text
    # La tabla viene marcada para OOB swap.
    assert 'id="files-table-wrap"' in r.text
    assert 'hx-swap-oob="true"' in r.text


def test_status_partial_404_for_unknown_collection(client):
    r = client.get("/collections/col_nope/_status")
    assert r.status_code == 404


def test_panel_has_polling_when_running(client, coll_id, mock_minio_client, test_cfg):
    # Forzamos un fichero a RUNNING manualmente (el runner sincrono
    # del TestClient no nos deja "verlo" RUNNING durante ejecucion).
    from admin.collections.files import IngestionStatus, set_ingest_status
    set_ingest_status(
        mock_minio_client,
        bucket=test_cfg.minio_bucket,
        prefix=test_cfg.collections_prefix(),
        collection_id=coll_id, filename="doc.pdf",
        status=IngestionStatus.RUNNING,
    )
    r = client.get(f"/collections/{coll_id}")
    panel = r.text.split('id="ingest-panel"')[1].split("</section>")[0]
    assert 'hx-trigger="load delay:3s"' in panel
    assert f'/collections/{coll_id}/_status' in panel


def test_panel_polls_only_while_running_present(client, coll_id):
    # Tras el upload, todo PENDING -> NO debe haber hx-trigger en el panel.
    r1 = client.get(f"/collections/{coll_id}")
    assert "hx-trigger" not in r1.text.split("ingest-panel")[1].split("</section>")[0]
    # Tras ingest -> todo DONE -> tampoco debe haber hx-trigger.
    client.post(f"/collections/{coll_id}/ingest")
    r2 = client.get(f"/collections/{coll_id}")
    assert "hx-trigger" not in r2.text.split("ingest-panel")[1].split("</section>")[0]


def test_per_file_ingest_404_unknown_collection(client):
    r = client.post(
        "/collections/col_nope/files/x.pdf/ingest", follow_redirects=False,
    )
    assert r.status_code == 404


def test_per_file_ingest_404_unknown_file(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files/ghost.pdf/ingest", follow_redirects=False,
    )
    assert r.status_code == 404


def test_per_file_ingest_runs_only_that_file(client, coll_id, mock_minio_client, test_cfg):
    # Subimos un segundo fichero pendiente.
    client.post(
        f"/collections/{coll_id}/files",
        files=[("files", ("other.pdf", b"%PDF-1.4 x", "application/pdf"))],
    )
    # Ingestamos solo "doc.pdf"
    r = client.post(
        f"/collections/{coll_id}/files/doc.pdf/ingest", follow_redirects=False,
    )
    assert r.status_code == 303
    # En el detalle, solo doc.pdf debe estar done; el otro sigue pending.
    detail = client.get(f"/collections/{coll_id}").text
    rows = detail.split("<tr>")
    doc_row = next(r for r in rows if ">doc<" in r)
    other_row = next(r for r in rows if ">other<" in r)
    assert "ingest-done" in doc_row
    assert "ingest-pending" in other_row


def test_per_file_ingest_idempotent_when_done(client, coll_id):
    client.post(f"/collections/{coll_id}/ingest")
    # Re-disparar sobre un done devuelve 303 sin error y no cambia nada.
    r = client.post(
        f"/collections/{coll_id}/files/doc.pdf/ingest", follow_redirects=False,
    )
    assert r.status_code == 303


def test_ingest_endpoint_is_noop_when_nothing_pending(client, coll_id):
    client.post(f"/collections/{coll_id}/ingest")
    r = client.post(
        f"/collections/{coll_id}/ingest", follow_redirects=False,
    )
    assert r.status_code == 303
    detail = client.get(f"/collections/{coll_id}")
    assert 'ingest-done' in detail.text
