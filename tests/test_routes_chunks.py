"""Smoke tests for the chunks tab route via FastAPI TestClient."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from admin.collections.routes import router as collections_router
from admin.config import AdminConfig
from admin.dependencies import get_config, get_minio_client
from admin.ingest.chunker import Chunk
from admin.ingest.chunks_io import write_chunks


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
    return TestClient(app)


def _pdf(name: str = "a.pdf", body: bytes = b"%PDF-1.4 x") -> tuple:
    return ("files", (name, body, "application/pdf"))


def _create_collection(client) -> str:
    r = client.post(
        "/collections",
        data={"name": "Demo", "type": "playground"},
        files=[_pdf("intro.pdf")],
        follow_redirects=False,
    )
    assert r.status_code == 303
    return r.headers["location"].rsplit("/", 1)[-1]


def _seed_chunks(mock_minio_client, bucket, collection_id, stem, items):
    write_chunks(
        mock_minio_client,
        bucket=bucket, prefix="admin/collections",
        collection_id=collection_id, filename_stem=stem,
        chunks=items,
    )


def _ch(stem, idx, page_start, page_end, types=("text",), text="t", tokens=10):
    return Chunk(
        chunk_id=f"{stem}:{idx:05d}",
        collection_id="x",
        source_file=f"{stem}.pdf",
        page_start=page_start, page_end=page_end,
        block_types=list(types), text=text, token_count=tokens,
    )


def test_chunks_view_404_when_collection_missing(client):
    r = client.get("/collections/col_unknown/chunks")
    assert r.status_code == 404


def test_chunks_view_renders_empty_state_when_no_chunks(client):
    coll_id = _create_collection(client)
    r = client.get(f"/collections/{coll_id}/chunks")
    assert r.status_code == 200
    assert "No chunks yet" in r.text
    # Tab bar renders with Chunks active
    assert 'aria-current="page"' in r.text
    assert "Overview" in r.text
    assert "Chunks" in r.text


def test_chunks_view_renders_chunks_table(client, mock_minio_client):
    coll_id = _create_collection(client)
    _seed_chunks(mock_minio_client, "lakehouse", coll_id, "Libro", [
        _ch("Libro", 0, 1, 2, types=("title", "text"),
            text="Esta es la introduccion del libro " * 3,
            tokens=30),
        _ch("Libro", 1, 3, 5, types=("text",),
            text="Segundo chunk con mas paginas.", tokens=8),
    ])

    r = client.get(f"/collections/{coll_id}/chunks")
    assert r.status_code == 200
    # Table headers
    assert "Source" in r.text and "Pages" in r.text and "Types" in r.text
    # Both chunks present
    assert "Libro" in r.text
    assert "1–2" in r.text  # page label range
    assert "3–5" in r.text
    # Token counts visible
    assert "30" in r.text and "8" in r.text
    # Block types as chips
    assert "title" in r.text and "text" in r.text
    # Total tokens summary
    assert "38 tokens" in r.text
    # Snippet shown (truncated)
    assert "introduccion" in r.text


def test_chunks_view_filter_by_source_file(client, mock_minio_client):
    coll_id = _create_collection(client)
    _seed_chunks(mock_minio_client, "lakehouse", coll_id, "A", [
        _ch("A", 0, 1, 1, text="alpha"),
    ])
    _seed_chunks(mock_minio_client, "lakehouse", coll_id, "B", [
        _ch("B", 0, 1, 1, text="beta"),
    ])

    # Without filter: both files
    r_all = client.get(f"/collections/{coll_id}/chunks")
    assert r_all.status_code == 200
    assert "alpha" in r_all.text and "beta" in r_all.text

    # With filter source_file=A: only A
    r_a = client.get(f"/collections/{coll_id}/chunks?source_file=A")
    assert r_a.status_code == 200
    assert "alpha" in r_a.text
    assert "beta" not in r_a.text


def test_chunks_view_unknown_source_file_falls_back_to_all(client, mock_minio_client):
    coll_id = _create_collection(client)
    _seed_chunks(mock_minio_client, "lakehouse", coll_id, "A", [
        _ch("A", 0, 1, 1, text="alpha"),
    ])
    # ?source_file=Z (no existe) -> tratado como "no filter" (selected=None)
    r = client.get(f"/collections/{coll_id}/chunks?source_file=Z")
    assert r.status_code == 200
    assert "alpha" in r.text


def test_chunks_view_overview_tab_link_back(client):
    coll_id = _create_collection(client)
    r = client.get(f"/collections/{coll_id}/chunks")
    assert r.status_code == 200
    # Tab Overview apunta a /collections/{id}
    assert f'href="/collections/{coll_id}"' in r.text
