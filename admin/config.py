"""Admin configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return value if value is not None else default


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass
class AdminConfig:
    """Top-level admin config. Built from `.env` via `from_env()`."""

    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = ""
    admin_root_prefix: str = "admin"

    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    mineru_url: str = "http://172.30.79.104:8000/file_parse"
    mineru_timeout_secs: int = 900

    @classmethod
    def from_env(cls, dotenv_path: str | None = None) -> "AdminConfig":
        load_dotenv(dotenv_path)
        return cls(
            minio_endpoint=_env("MINIO_ENDPOINT"),
            minio_access_key=_env("MINIO_ACCESS_KEY"),
            minio_secret_key=_env("MINIO_SECRET_KEY"),
            minio_bucket=_env("MINIO_BUCKET_NAME"),
            admin_root_prefix=_env("ADMIN_ROOT_PREFIX", "admin").strip("/"),
            host=_env("ADMIN_HOST", "0.0.0.0"),
            port=_env_int("ADMIN_PORT", 8080),
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            mineru_url=_env("MINERU_URL", "http://172.30.79.104:8000/file_parse"),
            mineru_timeout_secs=_env_int("MINERU_TIMEOUT_SECS", 900),
        )

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.minio_endpoint:
            errors.append("MINIO_ENDPOINT no configurado")
        if not self.minio_bucket:
            errors.append("MINIO_BUCKET_NAME no configurado")
        if not self.minio_access_key or not self.minio_secret_key:
            errors.append("MINIO_ACCESS_KEY/MINIO_SECRET_KEY no configurados")
        if not self.admin_root_prefix:
            errors.append("ADMIN_ROOT_PREFIX vacio")
        if not self.mineru_url:
            errors.append("MINERU_URL no configurado")
        if self.mineru_timeout_secs <= 0:
            errors.append("MINERU_TIMEOUT_SECS debe ser > 0")
        return errors

    def collections_prefix(self) -> str:
        return f"{self.admin_root_prefix}/collections"
