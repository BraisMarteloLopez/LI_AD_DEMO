"""HTTP client for the MinerU /file_parse endpoint.

Design notes
------------
- Llamada directa a MinerU (ver decisión D6 en CLAUDE.md). El broker queda
  como alternativa pero no la usamos.
- Devolvemos `content_list` tal cual para que el runner lo filtre. Aquí no
  decidimos qué bloques conservar; solo traducimos la respuesta.
- No persistimos imágenes en Fase 1.B (D4): pedimos `return_images=false`
  para que la respuesta sea más ligera.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, List, Protocol

import requests

logger = logging.getLogger("admin.ingest.mineru")

_DEFAULT_FORM_DATA: List[tuple[str, str]] = [
    ("backend", "hybrid-auto-engine"),
    ("lang_list", "latin"),
    ("return_images", "false"),
    ("formula_enable", "false"),
    ("table_enable", "true"),
    ("return_content_list", "true"),
    ("return_middle_json", "false"),
    ("return_model_output", "false"),
]


class MineruError(RuntimeError):
    """Raised when MinerU returns an error response or an unparseable body."""


@dataclass(frozen=True)
class MineruResult:
    markdown: str
    content_list: List[dict]


class OcrClient(Protocol):
    def parse(self, pdf_bytes: bytes, filename: str) -> MineruResult: ...


class MineruClient:
    """Blocking MinerU client. One `.parse()` call per PDF."""

    def __init__(self, url: str, timeout_secs: int = 900) -> None:
        self._url = url
        self._timeout = timeout_secs

    def parse(self, pdf_bytes: bytes, filename: str) -> MineruResult:
        logger.info(
            "mineru request file=%s bytes=%d url=%s",
            filename, len(pdf_bytes), self._url,
        )
        try:
            resp = requests.post(
                self._url,
                files={"files": (filename, pdf_bytes, "application/pdf")},
                data=list(_DEFAULT_FORM_DATA),
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise MineruError(f"mineru request failed: {exc}") from exc

        if resp.status_code != 200:
            raise MineruError(
                f"mineru returned {resp.status_code}: {resp.text[:500]}",
            )

        try:
            payload: Any = resp.json()
        except ValueError as exc:
            raise MineruError(f"mineru body is not json: {exc}") from exc

        results = (payload or {}).get("results") or {}
        if not isinstance(results, dict) or not results:
            raise MineruError(
                f"mineru response has no 'results': keys={list((payload or {}).keys())}",
            )

        file_key = _pick_file_key(results, filename)
        if file_key is None:
            raise MineruError(
                f"mineru did not return a result for {filename!r}; "
                f"keys={list(results.keys())}",
            )

        file_data = results[file_key] or {}
        md = file_data.get("md_content") or ""
        content_list = _coerce_content_list(file_data.get("content_list"))
        logger.info(
            "mineru response file=%s blocks=%d md_chars=%d",
            filename, len(content_list), len(md),
        )
        return MineruResult(markdown=md, content_list=content_list)


def _coerce_content_list(raw: Any) -> List[dict]:
    """MinerU may return `content_list` already deserialised OR as a JSON
    string (seen in the /file_parse endpoint). Accept both."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, (str, bytes)):
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise MineruError(
                f"mineru content_list is a string but not valid JSON: {exc}",
            ) from exc
        if not isinstance(parsed, list):
            raise MineruError(
                f"mineru content_list JSON decoded to {type(parsed).__name__}, "
                f"expected list",
            )
        return parsed
    raise MineruError(
        f"mineru content_list is {type(raw).__name__}, expected list or JSON string",
    )


def _pick_file_key(results: dict, filename: str) -> str | None:
    """MinerU's result key sometimes matches the filename loosely. Match
    exact first, then substring in either direction (replicates the user's
    reference script)."""
    if filename in results:
        return filename
    for k in results:
        if isinstance(k, str) and (k in filename or filename in k):
            return k
    return None
