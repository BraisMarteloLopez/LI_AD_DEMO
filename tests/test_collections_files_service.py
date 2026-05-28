"""Unit tests for admin.collections.files service."""
from __future__ import annotations

import io

import pytest

from admin.collections import files as files_svc
from admin.collections import service
from admin.collections.models import CollectionType


@pytest.fixture
def coll_id(mock_minio_client, bucket, admin_prefix):
    c = service.create(
        mock_minio_client,
        bucket=bucket,
        prefix=admin_prefix,
        name="Demo",
        type=CollectionType.PLAYGROUND,
    )
    return c.id


class TestSanitizeFilename:
    def test_strips_path_separators(self):
        assert files_svc.sanitize_filename("a/b/c.pdf") == "c.pdf"
        assert files_svc.sanitize_filename("a\\b\\c.pdf") == "c.pdf"

    def test_normalizes_unicode(self):
        assert files_svc.sanitize_filename("Pingüino.pdf") == "Pinguino.pdf"

    def test_collapses_spaces_to_underscore(self):
        assert files_svc.sanitize_filename("my   file.pdf") == "my_file.pdf"

    def test_replaces_unsafe_chars(self):
        assert files_svc.sanitize_filename("hola!@#.pdf") == "hola_.pdf"

    def test_rejects_empty(self):
        with pytest.raises(files_svc.InvalidFilenameError):
            files_svc.sanitize_filename("")

    def test_rejects_only_unsafe(self):
        with pytest.raises(files_svc.InvalidFilenameError):
            files_svc.sanitize_filename("!!!@@@")


def test_upload_persists_bytes_under_raw(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    body = b"%PDF-1.4 fake content"
    stored = files_svc.upload(
        mock_minio_client,
        bucket=bucket,
        prefix=admin_prefix,
        collection_id=coll_id,
        filename="Report 1.pdf",
        stream=io.BytesIO(body),
        content_type="application/pdf",
    )
    assert stored.name == "Report_1.pdf"
    assert stored.size == len(body)

    key = f"{admin_prefix}/{coll_id}/raw/Report_1.pdf"
    rec = mock_minio_client._backend.objects[(bucket, key)]
    assert rec["body"] == body
    assert rec["content_type"] == "application/pdf"


def _make_real_pdf(num_pages: int) -> bytes:
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(num_pages):
        w.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_upload_extracts_and_persists_page_count(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    pdf = _make_real_pdf(3)
    stored = files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="doc.pdf",
        stream=io.BytesIO(pdf), content_type="application/pdf",
    )
    assert stored.pages == 3
    listed = files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    assert listed[0].pages == 3


def test_upload_tolerates_unreadable_pdf(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    stored = files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="bogus.pdf",
        stream=io.BytesIO(b"not really a pdf"),
        content_type="application/pdf",
    )
    assert stored.pages is None


def test_upload_rejects_non_pdf(mock_minio_client, bucket, admin_prefix, coll_id):
    with pytest.raises(files_svc.InvalidContentTypeError):
        files_svc.upload(
            mock_minio_client,
            bucket=bucket,
            prefix=admin_prefix,
            collection_id=coll_id,
            filename="foo.txt",
            stream=io.BytesIO(b"hello"),
            content_type="text/plain",
        )


def test_list_files_empty(mock_minio_client, bucket, admin_prefix, coll_id):
    assert files_svc.list_files(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    ) == []


def test_get_file_returns_body(mock_minio_client, bucket, admin_prefix, coll_id):
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="x.pdf",
        stream=io.BytesIO(b"hello"), content_type="application/pdf",
    )
    resp = files_svc.get_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="x.pdf",
    )
    assert resp is not None
    assert resp["Body"].read() == b"hello"


def test_get_file_missing_returns_none(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    assert files_svc.get_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="nope.pdf",
    ) is None


def test_delete_file_missing_returns_false(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    assert files_svc.delete_file(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="ghost.pdf",
    ) is False


def test_collection_delete_removes_raw_files_too(
    mock_minio_client, bucket, admin_prefix, coll_id,
):
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="a.pdf",
        stream=io.BytesIO(b"1"), content_type="application/pdf",
    )
    files_svc.upload(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll_id, filename="b.pdf",
        stream=io.BytesIO(b"2"), content_type="application/pdf",
    )
    service.delete(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll_id,
    )
    remaining = [
        k for (_, k) in mock_minio_client._backend.objects.keys() if coll_id in k
    ]
    assert remaining == []
