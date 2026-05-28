"""Unit tests for admin.collections.service against an in-memory MinIO mock."""
from __future__ import annotations

import json

import pytest

from admin.collections import service
from admin.collections.models import (
    Collection,
    CollectionState,
    CollectionType,
    IngestProfile,
)


def test_create_persists_meta_json(mock_minio_client, bucket, admin_prefix):
    coll = service.create(
        mock_minio_client,
        bucket=bucket,
        prefix=admin_prefix,
        name="Demo One",
        type=CollectionType.PLAYGROUND,
    )
    assert coll.id.startswith("col_")
    assert coll.name == "Demo One"
    assert coll.type is CollectionType.PLAYGROUND
    assert coll.state is CollectionState.CREATED

    key = f"{admin_prefix}/{coll.id}/meta.json"
    raw = mock_minio_client._backend.objects[(bucket, key)]["body"]
    payload = json.loads(raw.decode("utf-8"))
    assert payload["id"] == coll.id
    assert payload["type"] == "playground"
    assert payload["state"] == "created"
    assert payload["schema_version"] == 1


def test_create_rejects_empty_name(mock_minio_client, bucket, admin_prefix):
    with pytest.raises(ValueError):
        service.create(
            mock_minio_client,
            bucket=bucket,
            prefix=admin_prefix,
            name="   ",
            type=CollectionType.PLAYGROUND,
        )


def test_get_returns_collection(mock_minio_client, bucket, admin_prefix):
    created = service.create(
        mock_minio_client,
        bucket=bucket,
        prefix=admin_prefix,
        name="A",
        type=CollectionType.PLAYGROUND,
    )
    fetched = service.get(
        mock_minio_client,
        bucket=bucket,
        prefix=admin_prefix,
        collection_id=created.id,
    )
    assert isinstance(fetched, Collection)
    assert fetched.id == created.id
    assert fetched.type is CollectionType.PLAYGROUND


def test_get_missing_returns_none(mock_minio_client, bucket, admin_prefix):
    assert (
        service.get(
            mock_minio_client,
            bucket=bucket,
            prefix=admin_prefix,
            collection_id="col_does_not_exist",
        )
        is None
    )


def test_list_all_empty(mock_minio_client, bucket, admin_prefix):
    assert service.list_all(mock_minio_client, bucket=bucket, prefix=admin_prefix) == []


def test_list_all_returns_sorted_desc(mock_minio_client, bucket, admin_prefix):
    a = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="A", type=CollectionType.PLAYGROUND,
    )
    b = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="B", type=CollectionType.PLAYGROUND,
    )
    items = service.list_all(mock_minio_client, bucket=bucket, prefix=admin_prefix)
    assert {c.id for c in items} == {a.id, b.id}
    assert items[0].created_at >= items[1].created_at


def test_list_all_skips_non_meta_keys(mock_minio_client, bucket, admin_prefix):
    coll = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="A", type=CollectionType.PLAYGROUND,
    )
    mock_minio_client.put_object(
        Bucket=bucket,
        Key=f"{admin_prefix}/{coll.id}/raw/foo.txt",
        Body=b"x",
    )
    items = service.list_all(mock_minio_client, bucket=bucket, prefix=admin_prefix)
    assert len(items) == 1
    assert items[0].id == coll.id


def test_delete_removes_all_keys_under_prefix(mock_minio_client, bucket, admin_prefix):
    coll = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="A", type=CollectionType.PLAYGROUND,
    )
    extra = f"{admin_prefix}/{coll.id}/raw/foo.txt"
    mock_minio_client.put_object(Bucket=bucket, Key=extra, Body=b"hello")

    service.delete(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll.id,
    )
    backend_keys = [k for (_, k) in mock_minio_client._backend.objects]
    assert all(coll.id not in k for k in backend_keys)
    assert service.get(
        mock_minio_client, bucket=bucket, prefix=admin_prefix, collection_id=coll.id,
    ) is None


def test_delete_idempotent_on_unknown_id(mock_minio_client, bucket, admin_prefix):
    service.delete(
        mock_minio_client,
        bucket=bucket,
        prefix=admin_prefix,
        collection_id="col_nope",
    )
    mock_minio_client.delete_objects.assert_not_called()


# === IngestProfile / update_profile ===


def test_create_persists_default_ingest_profile(mock_minio_client, bucket, admin_prefix):
    coll = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="X", type=CollectionType.PLAYGROUND,
    )
    assert coll.ingest_profile == IngestProfile()  # all defaults

    key = f"{admin_prefix}/{coll.id}/meta.json"
    payload = json.loads(mock_minio_client._backend.objects[(bucket, key)]["body"])
    assert payload["ingest_profile"]["skip_blank_markers"] is True
    assert payload["ingest_profile"]["skip_toc_entries"] is True
    assert payload["ingest_profile"]["drop_short_blocks"] is True
    assert payload["ingest_profile"]["short_block_min_words"] == 5
    assert payload["ingest_profile"]["drop_small_chunks"] is True
    assert payload["ingest_profile"]["min_chunk_tokens"] == 30


def test_get_loads_collection_without_ingest_profile_with_defaults(
    mock_minio_client, bucket, admin_prefix,
):
    """Backward compat: una meta.json pre-PR-B (sin ingest_profile) carga
    con defaults — no rompe la lectura."""
    legacy = {
        "id": "col_legacy",
        "name": "Legacy",
        "type": "playground",
        "state": "created",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "schema_version": 1,
    }
    mock_minio_client.put_object(
        Bucket=bucket,
        Key=f"{admin_prefix}/col_legacy/meta.json",
        Body=json.dumps(legacy).encode("utf-8"),
        ContentType="application/json",
    )
    coll = service.get(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id="col_legacy",
    )
    assert coll is not None
    assert coll.ingest_profile == IngestProfile()


def test_update_profile_replaces_and_bumps_updated_at(
    mock_minio_client, bucket, admin_prefix,
):
    coll = service.create(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        name="X", type=CollectionType.PLAYGROUND,
    )
    original_updated = coll.updated_at

    new_profile = IngestProfile(
        skip_blank_markers=False,
        skip_toc_entries=True,
        drop_short_blocks=True,
        short_block_min_words=8,
        drop_small_chunks=False,
        min_chunk_tokens=50,
    )
    updated = service.update_profile(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id, profile=new_profile,
    )
    assert updated.ingest_profile == new_profile
    assert updated.updated_at >= original_updated  # ISO-8601 sortable

    # Persistido en meta.json.
    reread = service.get(
        mock_minio_client, bucket=bucket, prefix=admin_prefix,
        collection_id=coll.id,
    )
    assert reread.ingest_profile.skip_blank_markers is False
    assert reread.ingest_profile.short_block_min_words == 8
    assert reread.ingest_profile.min_chunk_tokens == 50


def test_update_profile_raises_when_collection_missing(
    mock_minio_client, bucket, admin_prefix,
):
    with pytest.raises(FileNotFoundError):
        service.update_profile(
            mock_minio_client, bucket=bucket, prefix=admin_prefix,
            collection_id="col_nope", profile=IngestProfile(),
        )


def test_ingest_profile_summary_default():
    assert IngestProfile().summary() == "All filters active"


def test_ingest_profile_summary_one_toggle_off():
    p = IngestProfile(skip_toc_entries=False)
    assert p.summary() == "3 of 4 filters active"


def test_ingest_profile_summary_default_with_custom_threshold():
    p = IngestProfile(short_block_min_words=10)
    assert p.summary() == "All filters active · min words 10"


def test_ingest_profile_summary_mixed_off_and_custom_threshold():
    p = IngestProfile(
        drop_short_blocks=False,
        drop_small_chunks=False,
        min_chunk_tokens=80,
    )
    assert p.summary() == "2 of 4 filters active · min chunk tokens 80"


def test_ingest_profile_summary_custom_target_only():
    p = IngestProfile(target_tokens=800)
    assert p.summary() == "All filters active · target 800 / overlap 50"


def test_ingest_profile_summary_custom_overlap_only():
    p = IngestProfile(overlap_tokens=100)
    assert p.summary() == "All filters active · target 500 / overlap 100"


def test_ingest_profile_summary_custom_target_and_overlap():
    p = IngestProfile(target_tokens=800, overlap_tokens=80)
    assert p.summary() == "All filters active · target 800 / overlap 80"


def test_ingest_profile_summary_full_mix():
    p = IngestProfile(
        skip_toc_entries=False,
        short_block_min_words=10,
        min_chunk_tokens=80,
        target_tokens=1000,
        overlap_tokens=100,
    )
    assert p.summary() == (
        "3 of 4 filters active · min words 10 · "
        "min chunk tokens 80 · target 1000 / overlap 100"
    )


def test_ingest_profile_is_default():
    assert IngestProfile().is_default is True
    assert IngestProfile(skip_toc_entries=False).is_default is False
    assert IngestProfile(min_chunk_tokens=20).is_default is False
    assert IngestProfile(target_tokens=800).is_default is False
    assert IngestProfile(overlap_tokens=100).is_default is False


def test_ingest_profile_from_dict_handles_target_overlap():
    p = IngestProfile.from_dict({"target_tokens": 800, "overlap_tokens": 80})
    assert p.target_tokens == 800
    assert p.overlap_tokens == 80


def test_ingest_profile_from_dict_falls_back_when_overlap_geq_target():
    """Si la relacion overlap < target se rompe, ambos caen al default."""
    p = IngestProfile.from_dict({"target_tokens": 100, "overlap_tokens": 200})
    assert p.target_tokens == 500  # default
    assert p.overlap_tokens == 50   # default


def test_ingest_profile_from_dict_target_below_minimum():
    p = IngestProfile.from_dict({"target_tokens": 0})
    assert p.target_tokens == 500  # default (min_value=1 fail -> default)


def test_ingest_profile_from_dict_target_malformed_string():
    p = IngestProfile.from_dict({"target_tokens": "muchos", "overlap_tokens": "poquitos"})
    assert p.target_tokens == 500
    assert p.overlap_tokens == 50


def test_ingest_profile_from_dict_handles_missing_or_malformed_fields():
    # Solo algunos campos -> resto defaults.
    p = IngestProfile.from_dict({"skip_blank_markers": False, "min_chunk_tokens": 100})
    assert p.skip_blank_markers is False
    assert p.min_chunk_tokens == 100
    assert p.skip_toc_entries is True  # default

    # Tipos malformados -> default del campo.
    p = IngestProfile.from_dict({
        "skip_blank_markers": "yes",     # not bool -> default True
        "min_chunk_tokens": "muchos",    # not int -> default 30
        "short_block_min_words": -3,     # negative -> default 5
    })
    assert p.skip_blank_markers is True
    assert p.min_chunk_tokens == 30
    assert p.short_block_min_words == 5

    # None -> all defaults.
    assert IngestProfile.from_dict(None) == IngestProfile()
    assert IngestProfile.from_dict({}) == IngestProfile()
