"""Smoke tests for collection routes via FastAPI TestClient.

Construye la app sin lifespan (validacion de config no aplica con mocks)
y sustituye las dependencias get_config / get_minio_client por fakes.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from admin.collections.routes import router as collections_router
from admin.config import AdminConfig
from admin.dependencies import get_config, get_minio_client


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


def test_list_empty(client):
    r = client.get("/collections")
    assert r.status_code == 200
    assert "No collections yet" in r.text


def test_list_shows_per_collection_ingest_summary(client):
    # 1) coleccion sin ficheros -> 'no files'
    client.post(
        "/collections",
        data={"name": "Empty", "type": "playground"},
        files=[_pdf("seed.pdf")],
        follow_redirects=False,
    )
    # 2) coleccion con un fichero pendiente
    r = client.post(
        "/collections",
        data={"name": "Pending", "type": "playground"},
        files=[_pdf("a.pdf"), _pdf("b.pdf")],
        follow_redirects=False,
    )
    assert r.status_code == 303

    listing = client.get("/collections")
    assert listing.status_code == 200
    # ambos contadores aparecen (1/1 y 0/2)
    assert "0/2" in listing.text
    assert "1/1" in listing.text or "0/1" in listing.text
    # mini progress bar visible
    assert "progress-mini" in listing.text


def test_new_form_renders(client):
    r = client.get("/collections/new")
    assert r.status_code == 200
    assert "playground" in r.text
    assert "benchmark" not in r.text
    assert "<form" in r.text


def test_create_redirects_to_detail(client):
    r = client.post(
        "/collections",
        data={"name": "Demo One", "type": "playground"},
        files=[_pdf()],
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"].startswith("/collections/col_")


def test_create_then_detail_then_list(client):
    r = client.post(
        "/collections",
        data={"name": "Demo One", "type": "playground"},
        files=[_pdf("intro.pdf")],
        follow_redirects=False,
    )
    new_url = r.headers["location"]
    coll_id = new_url.rsplit("/", 1)[-1]

    r2 = client.get(new_url)
    assert r2.status_code == 200
    assert "Demo One" in r2.text
    assert coll_id in r2.text
    assert "intro.pdf" in r2.text

    r3 = client.get("/collections")
    assert r3.status_code == 200
    assert "Demo One" in r3.text


def test_create_accepts_multiple_files(client):
    r = client.post(
        "/collections",
        data={"name": "Multi", "type": "playground"},
        files=[_pdf("a.pdf"), _pdf("b.pdf"), _pdf("c.pdf")],
        follow_redirects=False,
    )
    assert r.status_code == 303
    detail = client.get(r.headers["location"])
    for n in ("a.pdf", "b.pdf", "c.pdf"):
        assert n in detail.text


def test_create_requires_at_least_one_file(client):
    r = client.post(
        "/collections",
        data={"name": "No files", "type": "playground"},
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_create_rejects_non_pdf_mime(client):
    r = client.post(
        "/collections",
        data={"name": "Bad mime", "type": "playground"},
        files=[("files", ("x.txt", b"hi", "text/plain"))],
        follow_redirects=False,
    )
    assert r.status_code == 415


def test_create_rejects_invalid_type(client):
    r = client.post(
        "/collections",
        data={"name": "X", "type": "not_a_type"},
        files=[_pdf()],
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_create_rejects_blank_name(client):
    r = client.post(
        "/collections",
        data={"name": "   ", "type": "playground"},
        files=[_pdf()],
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_detail_404_when_missing(client):
    r = client.get("/collections/col_unknown")
    assert r.status_code == 404


def test_delete_redirects_and_removes(client):
    created = client.post(
        "/collections",
        data={"name": "X", "type": "playground"},
        files=[_pdf()],
        follow_redirects=False,
    )
    coll_id = created.headers["location"].rsplit("/", 1)[-1]

    r = client.post(f"/collections/{coll_id}/delete", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/collections"

    assert client.get(f"/collections/{coll_id}").status_code == 404


def test_delete_idempotent_unknown_id(client):
    r = client.post("/collections/col_nope/delete", follow_redirects=False)
    assert r.status_code == 303
