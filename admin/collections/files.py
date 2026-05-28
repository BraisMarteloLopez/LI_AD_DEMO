"""Per-collection file storage on MinIO/S3. Source of truth: MinIO listing."""
from __future__ import annotations

import enum
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, List, Optional

from botocore.exceptions import ClientError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger("admin.collections.files")

RAW_SUBPREFIX = "raw"
PDF_CONTENT_TYPE = "application/pdf"
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class InvalidFilenameError(ValueError):
    """Raised when a filename cannot be sanitized into a valid S3 object name."""


class InvalidContentTypeError(ValueError):
    """Raised when the upload is not an accepted MIME type."""


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class StoredFile:
    name: str
    size: int
    last_modified: datetime
    content_type: str = PDF_CONTENT_TYPE
    pages: Optional[int] = None
    ingest_status: IngestionStatus = IngestionStatus.PENDING
    ingest_error: Optional[str] = None


def sanitize_filename(name: str) -> str:
    if not name:
        raise InvalidFilenameError("filename is empty")
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    normalized = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"\s+", "_", normalized)
    safe = _SAFE_CHARS.sub("_", collapsed).strip("._")
    if not safe:
        raise InvalidFilenameError(f"filename has no valid characters: {name!r}")
    return safe


def _raw_prefix(prefix: str, collection_id: str) -> str:
    return f"{prefix}/{collection_id}/{RAW_SUBPREFIX}/"


def _file_key(prefix: str, collection_id: str, filename: str) -> str:
    return f"{_raw_prefix(prefix, collection_id)}{filename}"


def _count_pdf_pages(stream: BinaryIO) -> Optional[int]:
    try:
        reader = PdfReader(stream)
        return len(reader.pages)
    except (PdfReadError, ValueError, OSError) as exc:
        logger.warning("pdf page count failed: %s", exc)
        return None


def upload(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    filename: str,
    stream: BinaryIO,
    content_type: str,
) -> StoredFile:
    if content_type != PDF_CONTENT_TYPE:
        raise InvalidContentTypeError(
            f"only {PDF_CONTENT_TYPE} accepted, got {content_type!r}",
        )
    safe = sanitize_filename(filename)
    key = _file_key(prefix, collection_id, safe)

    pages: Optional[int] = None
    if hasattr(stream, "seek"):
        try:
            stream.seek(0)
            pages = _count_pdf_pages(stream)
        finally:
            stream.seek(0)

    metadata: dict = {}
    if pages is not None:
        metadata["pages"] = str(pages)

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=stream,
        ContentType=PDF_CONTENT_TYPE,
        Metadata=metadata,
    )
    logger.info(
        "file uploaded collection=%s key=%s pages=%s", collection_id, key, pages,
    )
    head = client.head_object(Bucket=bucket, Key=key)
    head_meta = head.get("Metadata")
    return StoredFile(
        name=safe,
        size=int(head.get("ContentLength", 0)),
        last_modified=head["LastModified"],
        content_type=head.get("ContentType", PDF_CONTENT_TYPE),
        pages=_parse_pages(head_meta),
        ingest_status=_parse_ingest_status(head_meta),
        ingest_error=(head_meta or {}).get("ingest-error"),
    )


def _parse_pages(meta: Optional[dict]) -> Optional[int]:
    if not meta:
        return None
    raw = meta.get("pages")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_ingest_status(meta: Optional[dict]) -> IngestionStatus:
    if not meta:
        return IngestionStatus.PENDING
    raw = (meta.get("ingest-status") or "").lower()
    if not raw:
        return IngestionStatus.PENDING
    try:
        return IngestionStatus(raw)
    except ValueError:
        return IngestionStatus.PENDING


def set_ingest_status(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    filename: str,
    status: IngestionStatus,
    error: Optional[str] = None,
) -> None:
    """Update the ingestion status stored in the object's user metadata.

    S3/MinIO requires a copy-in-place with MetadataDirective=REPLACE to change
    user metadata, so we preserve existing fields (e.g. pages) explicitly.
    """
    key = _file_key(prefix, collection_id, sanitize_filename(filename))
    head = client.head_object(Bucket=bucket, Key=key)
    meta = dict(head.get("Metadata") or {})
    meta["ingest-status"] = status.value
    if error:
        meta["ingest-error"] = error[:1024]
    else:
        meta.pop("ingest-error", None)
    client.copy_object(
        Bucket=bucket,
        Key=key,
        CopySource={"Bucket": bucket, "Key": key},
        Metadata=meta,
        MetadataDirective="REPLACE",
        ContentType=head.get("ContentType", PDF_CONTENT_TYPE),
    )


def list_files(
    client, *, bucket: str, prefix: str, collection_id: str,
) -> List[StoredFile]:
    paginator = client.get_paginator("list_objects_v2")
    raw_prefix = _raw_prefix(prefix, collection_id)
    files: List[StoredFile] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=raw_prefix):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if not key.startswith(raw_prefix) or key == raw_prefix:
                continue
            name = key[len(raw_prefix):]
            if "/" in name:
                continue
            head = client.head_object(Bucket=bucket, Key=key)
            head_meta = head.get("Metadata")
            files.append(
                StoredFile(
                    name=name,
                    size=int(obj.get("Size", 0)),
                    last_modified=obj["LastModified"],
                    content_type=head.get("ContentType", PDF_CONTENT_TYPE),
                    pages=_parse_pages(head_meta),
                    ingest_status=_parse_ingest_status(head_meta),
                    ingest_error=(head_meta or {}).get("ingest-error"),
                )
            )
    files.sort(key=lambda f: f.last_modified, reverse=True)
    return files


def get_file(
    client, *, bucket: str, prefix: str, collection_id: str, filename: str,
) -> Optional[dict]:
    safe = sanitize_filename(filename)
    key = _file_key(prefix, collection_id, safe)
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NoSuchBucket"):
            return None
        raise
    return resp


def delete_file(
    client, *, bucket: str, prefix: str, collection_id: str, filename: str,
) -> bool:
    safe = sanitize_filename(filename)
    key = _file_key(prefix, collection_id, safe)
    try:
        client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NotFound"):
            return False
        raise
    client.delete_object(Bucket=bucket, Key=key)
    logger.info("file deleted collection=%s key=%s", collection_id, key)
    return True
