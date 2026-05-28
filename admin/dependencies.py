"""FastAPI dependency factories: config + MinIO/boto3 client + MinerU."""
from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.client import BaseClient

from admin.config import AdminConfig
from admin.ingest.mineru import MineruClient


@lru_cache(maxsize=1)
def get_config() -> AdminConfig:
    return AdminConfig.from_env()


@lru_cache(maxsize=1)
def get_minio_client() -> BaseClient:
    cfg = get_config()
    return boto3.client(
        "s3",
        endpoint_url=cfg.minio_endpoint,
        aws_access_key_id=cfg.minio_access_key,
        aws_secret_access_key=cfg.minio_secret_key,
    )


@lru_cache(maxsize=1)
def get_mineru_client() -> MineruClient:
    cfg = get_config()
    return MineruClient(url=cfg.mineru_url, timeout_secs=cfg.mineru_timeout_secs)


def reset_dependency_cache() -> None:
    get_config.cache_clear()
    get_minio_client.cache_clear()
    get_mineru_client.cache_clear()
