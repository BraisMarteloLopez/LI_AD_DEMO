"""Unit tests for the ingestion pipeline (stub level, Fase 1.B.1)."""
from __future__ import annotations

import io

import pytest

from admin.collections import files as files_svc
from admin.collections import service
from admin.collections.files import IngestionStatus
from admin.collections.models import CollectionType
from admin.ingest import service as ingest_svc


@pytest.fixture
def coll_id(mock_minio_client, bucket, admin_prefix):
    c = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="Ingest demo", type=CollectionType.PLAYGROUND,
    )
    return c.id


def _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, name="a.pdf"):
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename=name,
        stream=io.BytesIO(b"%PDF-1.4 stub"),
        content_type="application/pdf",
    )


def test_uploaded_file_defaults_to_pending(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "a.pdf")
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.PENDING
    assert f.ingest_error is None


def test_set_ingest_status_preserves_pages_metadata(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(4):
        w.add_blank_page(width=72, height=72)
    buf = io.BytesIO(); w.write(buf)
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        stream=io.BytesIO(buf.getvalue()), content_type="application/pdf",
    )
    files_svc.set_ingest_status(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        status=IngestionStatus.RUNNING,
    )
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.RUNNING
    assert f.pages == 4


def test_ingest_file_stub_transitions_to_done(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "a.pdf")
    result = ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="a.pdf",
    )
    assert result == IngestionStatus.DONE
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.DONE
    assert f.ingest_error is None


def test_ingest_file_records_failure(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "broken.pdf")

    def boom(*_a, **_k):
        raise RuntimeError("mineru unreachable")

    result = ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="broken.pdf",
        runner=boom,
    )
    assert result == IngestionStatus.FAILED
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.FAILED
    assert f.ingest_error == "mineru unreachable"


def test_ingest_reset_clears_previous_error(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    _seed_pdf(mock_minio_client, bucket, admin_prefix, coll_id, "retry.pdf")
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="retry.pdf",
        runner=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("first try")),
    )
    ingest_svc.ingest_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="retry.pdf",
    )
    [f] = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert f.ingest_status == IngestionStatus.DONE
    assert f.ingest_error is None
