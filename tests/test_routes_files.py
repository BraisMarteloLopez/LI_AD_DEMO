"""Smoke tests for per-collection file routes."""
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


@pytest.fixture
def coll_id(client):
    r = client.post(
        "/collections",
        data={"name": "Demo", "type": "playground"},
        files=[_pdf("seed.pdf")],
        follow_redirects=False,
    )
    assert r.status_code == 303
    return r.headers["location"].rsplit("/", 1)[-1]


def test_upload_redirects_to_detail(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("more.pdf")],
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == f"/collections/{coll_id}"


def test_upload_multiple_files_in_one_request(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("one.pdf"), _pdf("two.pdf"), _pdf("three.pdf")],
        follow_redirects=False,
    )
    assert r.status_code == 303
    detail = client.get(f"/collections/{coll_id}")
    for n in ("one.pdf", "two.pdf", "three.pdf"):
        assert n in detail.text


def test_upload_rejects_non_pdf_content_type(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files",
        files=[("files", ("a.txt", b"hi", "text/plain"))],
        follow_redirects=False,
    )
    assert r.status_code == 415


def test_upload_requires_at_least_one_file(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files",
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_upload_404_unknown_collection(client):
    r = client.post(
        "/collections/col_nope/files",
        files=[_pdf()],
        follow_redirects=False,
    )
    assert r.status_code == 404


def test_upload_overwrites_same_name(client, coll_id):
    client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("a.pdf", b"first")],
    )
    client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("a.pdf", b"second-longer")],
    )
    r = client.get(f"/collections/{coll_id}")
    assert r.text.count("a.pdf") >= 1
    dl = client.get(f"/collections/{coll_id}/files/a.pdf")
    assert dl.status_code == 200
    assert dl.content == b"second-longer"


def test_upload_bad_filename_returns_400(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files",
        files=[("files", ("!!!", b"x", "application/pdf"))],
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_download_returns_bytes_with_attachment_header(client, coll_id):
    client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("x.pdf", b"hello")],
    )
    r = client.get(f"/collections/{coll_id}/files/x.pdf")
    assert r.status_code == 200
    assert r.content == b"hello"
    assert r.headers["content-type"].startswith("application/pdf")
    assert 'attachment; filename="x.pdf"' in r.headers["content-disposition"]


def test_download_404_when_missing(client, coll_id):
    r = client.get(f"/collections/{coll_id}/files/ghost.pdf")
    assert r.status_code == 404


def test_delete_file_redirects_to_detail(client, coll_id):
    client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("y.pdf")],
    )
    r = client.post(
        f"/collections/{coll_id}/files/y.pdf/delete", follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == f"/collections/{coll_id}"
    assert client.get(f"/collections/{coll_id}/files/y.pdf").status_code == 404


def test_delete_file_idempotent_unknown(client, coll_id):
    r = client.post(
        f"/collections/{coll_id}/files/never.pdf/delete", follow_redirects=False,
    )
    assert r.status_code == 303


def test_collection_delete_cascades_raw_files(client, coll_id, mock_minio_client):
    client.post(
        f"/collections/{coll_id}/files",
        files=[_pdf("a.pdf"), _pdf("b.pdf")],
    )
    client.post(f"/collections/{coll_id}/delete", follow_redirects=False)
    remaining = [
        k for (_, k) in mock_minio_client._backend.objects.keys() if coll_id in k
    ]
    assert remaining == []
