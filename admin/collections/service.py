"""Pure CRUD operations for Collection persistence on MinIO/S3."""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from botocore.exceptions import ClientError

from admin.collections.models import (
    Collection,
    CollectionState,
    CollectionType,
    IngestProfile,
    new_collection_id,
)

logger = logging.getLogger("admin.collections.service")

META_FILENAME = "meta.json"


def _meta_key(prefix: str, collection_id: str) -> str:
    return f"{prefix}/{collection_id}/{META_FILENAME}"


def _collection_prefix(prefix: str, collection_id: str) -> str:
    return f"{prefix}/{collection_id}/"


def _put_meta(client, *, bucket: str, prefix: str, coll: Collection) -> None:
    body = json.dumps(coll.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
    client.put_object(
        Bucket=bucket,
        Key=_meta_key(prefix, coll.id),
        Body=body,
        ContentType="application/json",
    )


def create(
    client,
    *,
    bucket: str,
    prefix: str,
    name: str,
    type: CollectionType,
) -> Collection:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    coll = Collection(
        id=new_collection_id(),
        name=name,
        type=type,
        state=CollectionState.CREATED,
    )
    _put_meta(client, bucket=bucket, prefix=prefix, coll=coll)
    logger.info("collection created id=%s type=%s", coll.id, coll.type.value)
    return coll


def get(client, *, bucket: str, prefix: str, collection_id: str) -> Optional[Collection]:
    try:
        resp = client.get_object(Bucket=bucket, Key=_meta_key(prefix, collection_id))
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NoSuchBucket"):
            return None
        raise
    raw = resp["Body"].read()
    return Collection.from_dict(json.loads(raw.decode("utf-8")))


def update_profile(
    client,
    *,
    bucket: str,
    prefix: str,
    collection_id: str,
    profile: IngestProfile,
) -> Collection:
    """Replace the collection's ingest_profile and bump updated_at.

    Lanza FileNotFoundError si la coleccion no existe (decision distinta
    a `get` que devuelve None — aqui el caller usuallymente viene de un
    POST y queremos un fallo explicito).
    """
    coll = get(client, bucket=bucket, prefix=prefix, collection_id=collection_id)
    if coll is None:
        raise FileNotFoundError(f"collection not found: {collection_id}")
    from datetime import datetime, timezone
    coll.ingest_profile = profile
    coll.updated_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    _put_meta(client, bucket=bucket, prefix=prefix, coll=coll)
    logger.info("collection profile updated id=%s", collection_id)
    return coll


def list_all(client, *, bucket: str, prefix: str) -> List[Collection]:
    paginator = client.get_paginator("list_objects_v2")
    results: List[Collection] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if not key.endswith(f"/{META_FILENAME}"):
                continue
            try:
                resp = client.get_object(Bucket=bucket, Key=key)
                raw = resp["Body"].read()
                results.append(Collection.from_dict(json.loads(raw.decode("utf-8"))))
            except (ClientError, json.JSONDecodeError, KeyError) as exc:
                logger.warning("skip malformed meta key=%s err=%s", key, exc)
                continue
    results.sort(key=lambda c: c.created_at, reverse=True)
    return results


def delete(client, *, bucket: str, prefix: str, collection_id: str) -> None:
    coll_prefix = _collection_prefix(prefix, collection_id)
    paginator = client.get_paginator("list_objects_v2")
    to_delete: List[dict] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=coll_prefix):
        for obj in page.get("Contents", []) or []:
            to_delete.append({"Key": obj["Key"]})
    if not to_delete:
        logger.info("delete idempotent: no keys under %s", coll_prefix)
        return
    for i in range(0, len(to_delete), 1000):
        batch = to_delete[i : i + 1000]
        client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
    logger.info("collection deleted id=%s keys=%d", collection_id, len(to_delete))
