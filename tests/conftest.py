"""Shared test fixtures.

Mocks de infra a nivel de fixture, nunca parcheando modulos enteros.
La fixture `mock_minio_client` devuelve un MagicMock con un backend
in-memory que se comporta como S3 para los metodos que usa el admin.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Dict
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError


def _not_found(op: str, key: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": f"no key {key}"}},
        op,
    )


class _FakeS3Backend:
    """In-memory store used by the MagicMock-based fake client.

    Stores bytes plus per-object metadata (size, last_modified, content_type)
    so head_object y list_objects_v2 devuelvan algo util en tests.
    """

    def __init__(self) -> None:
        self.objects: Dict[tuple, dict] = {}
        self._clock = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def _tick(self) -> datetime:
        from datetime import timedelta
        self._clock = self._clock + timedelta(seconds=1)
        return self._clock

    def _read_body(self, body) -> bytes:
        if isinstance(body, bytes):
            return body
        if hasattr(body, "read"):
            data = body.read()
            return data if isinstance(data, bytes) else data.encode("utf-8")
        return bytes(body)

    def put_object(self, *, Bucket, Key, Body, ContentType=None, Metadata=None, **_):
        data = self._read_body(Body)
        self.objects[(Bucket, Key)] = {
            "body": data,
            "size": len(data),
            "last_modified": self._tick(),
            "content_type": ContentType or "application/octet-stream",
            "metadata": dict(Metadata) if Metadata else {},
        }
        return {}

    def get_object(self, *, Bucket, Key, **_):
        if (Bucket, Key) not in self.objects:
            raise _not_found("GetObject", Key)
        rec = self.objects[(Bucket, Key)]
        return {
            "Body": io.BytesIO(rec["body"]),
            "ContentLength": rec["size"],
            "ContentType": rec["content_type"],
            "LastModified": rec["last_modified"],
            "Metadata": dict(rec.get("metadata", {})),
        }

    def head_object(self, *, Bucket, Key, **_):
        if (Bucket, Key) not in self.objects:
            raise _not_found("HeadObject", Key)
        rec = self.objects[(Bucket, Key)]
        return {
            "ContentLength": rec["size"],
            "ContentType": rec["content_type"],
            "LastModified": rec["last_modified"],
            "Metadata": dict(rec.get("metadata", {})),
        }

    def head_bucket(self, *, Bucket, **_):
        return {}

    def copy_object(
        self, *, Bucket, Key, CopySource,
        Metadata=None, MetadataDirective=None, ContentType=None, **_,
    ):
        src_b = CopySource["Bucket"]
        src_k = CopySource["Key"]
        if (src_b, src_k) not in self.objects:
            raise _not_found("CopyObject", src_k)
        src = self.objects[(src_b, src_k)]
        if (MetadataDirective or "COPY").upper() == "REPLACE":
            new_meta = dict(Metadata) if Metadata else {}
        else:
            new_meta = dict(src.get("metadata", {}))
        self.objects[(Bucket, Key)] = {
            "body": src["body"],
            "size": src["size"],
            "last_modified": self._tick(),
            "content_type": ContentType or src["content_type"],
            "metadata": new_meta,
        }
        return {}

    def delete_object(self, *, Bucket, Key, **_):
        self.objects.pop((Bucket, Key), None)
        return {}

    def delete_objects(self, *, Bucket, Delete, **_):
        for obj in Delete.get("Objects", []):
            self.objects.pop((Bucket, obj["Key"]), None)
        return {}

    def get_paginator(self, op):
        assert op == "list_objects_v2"
        backend = self

        class _Paginator:
            def paginate(self, *, Bucket, Prefix=""):
                contents = [
                    {
                        "Key": key,
                        "Size": rec["size"],
                        "LastModified": rec["last_modified"],
                    }
                    for (b, key), rec in backend.objects.items()
                    if b == Bucket and key.startswith(Prefix)
                ]
                yield {"Contents": contents}

        return _Paginator()


@pytest.fixture
def mock_minio_client():
    backend = _FakeS3Backend()
    client = MagicMock(spec_set=[
        "put_object", "get_object", "head_object", "head_bucket",
        "copy_object", "delete_object", "delete_objects",
        "get_paginator", "_backend",
    ])
    client.put_object.side_effect = backend.put_object
    client.get_object.side_effect = backend.get_object
    client.head_object.side_effect = backend.head_object
    client.head_bucket.side_effect = backend.head_bucket
    client.copy_object.side_effect = backend.copy_object
    client.delete_object.side_effect = backend.delete_object
    client.delete_objects.side_effect = backend.delete_objects
    client.get_paginator.side_effect = backend.get_paginator
    client._backend = backend
    return client


@pytest.fixture
def bucket() -> str:
    return "lakehouse"


@pytest.fixture
def admin_prefix() -> str:
    return "admin/collections"
