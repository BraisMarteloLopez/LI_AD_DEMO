"""Deterministic chunker over text/title blocks produced by the MinerU filter.

Sigue la salida `text.jsonl` del admin: una lista de bloques con
`{"page": int, "type": "text"|"title", "text": str}`. Produce `Chunk`s
que después se persisten como parquet (ver `admin/ingest/chunks_io.py`).

Reglas:
- Se agrupan bloques consecutivos mientras la suma de tokens no supere
  `target_tokens`.
- Un bloque `type="title"` cierra el chunk en curso y abre uno nuevo que
  empieza con ese title.
- Un único bloque que ya supera `target_tokens` se parte en ventanas de
  `target_tokens` con `overlap_tokens` de solape.
- `page_start`/`page_end` = min/max página de los bloques del chunk.
- `block_types` se conserva en orden (no se deduplica).
- `chunk_id` = `f"{stem_of(source_file)}:{i:05d}"` con `i` 0-based.

Tokenizer: `tiktoken` cl100k_base como placeholder sensato. El motor
podrá alinearlo cuando publique su preferencia (hoy no la necesitamos
— ver D4 en CLAUDE.md).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List

import tiktoken

logger = logging.getLogger("admin.ingest.chunker")

CHUNK_TARGET_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50
TOKENIZER_NAME = "cl100k_base"

ALLOWED_BLOCK_TYPES = ("text", "title")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    collection_id: str
    source_file: str
    page_start: int
    page_end: int
    block_types: List[str]
    text: str
    token_count: int


class _FallbackTokenizer:
    """Offline word-level tokenizer.

    Se usa cuando tiktoken no puede descargar su fichero de encoding (p.ej.
    tests sandbox o despliegues sin acceso a openaipublic.blob). Los
    "token_count" serán aproximados (palabras), suficiente para chunkear
    con un target razonable hasta que cerremos D4.
    """

    def encode(self, s: str):
        return s.split()

    def decode(self, tokens):
        return " ".join(tokens)


# Si no hay salida a internet publica, tiktoken hace un GET sin timeout y
# bloquea ~75s antes de fallar. Lo envolvemos en un thread con limite corto.
_TIKTOKEN_LOAD_TIMEOUT_SECS = 5.0


def _try_load_tiktoken():
    import threading
    box: dict = {}

    def _work():
        try:
            box["enc"] = tiktoken.get_encoding(TOKENIZER_NAME)
        except Exception as exc:
            box["err"] = exc

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    t.join(timeout=_TIKTOKEN_LOAD_TIMEOUT_SECS)
    if "enc" in box:
        return box["enc"]
    return None  # timeout o error


@lru_cache(maxsize=1)
def _tokenizer():
    enc = _try_load_tiktoken()
    if enc is not None:
        logger.info("chunker tokenizer: tiktoken %s", TOKENIZER_NAME)
        return enc
    logger.warning(
        "chunker tokenizer: tiktoken %s not available within %.1fs; "
        "using word-level fallback",
        TOKENIZER_NAME, _TIKTOKEN_LOAD_TIMEOUT_SECS,
    )
    return _FallbackTokenizer()


def _count_tokens(s: str) -> int:
    return len(_tokenizer().encode(s))


def stem_of(filename: str) -> str:
    base = os.path.basename(filename)
    stem, _, _ = base.rpartition(".")
    return stem or base


def _split_giant_text(text: str, target_tokens: int, overlap_tokens: int) -> List[str]:
    tok = _tokenizer()
    ids = tok.encode(text)
    step = target_tokens - overlap_tokens
    if step <= 0:
        raise ValueError("overlap_tokens must be < target_tokens")
    pieces: List[str] = []
    start = 0
    while start < len(ids):
        end = start + target_tokens
        pieces.append(tok.decode(ids[start:end]))
        if end >= len(ids):
            break
        start += step
    return pieces


def chunk_text_blocks(
    blocks: Iterable[dict],
    *,
    collection_id: str,
    source_file: str,
    target_tokens: int = CHUNK_TARGET_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> List[Chunk]:
    if target_tokens <= 0:
        raise ValueError("target_tokens must be > 0")
    if overlap_tokens < 0 or overlap_tokens >= target_tokens:
        raise ValueError("overlap_tokens must be in [0, target_tokens)")

    stem = stem_of(source_file)
    chunks: List[Chunk] = []
    buf: List[dict] = []
    buf_tokens = 0

    def _flush_buffer() -> None:
        nonlocal buf, buf_tokens
        if not buf:
            return
        idx = len(chunks)
        text = "\n\n".join(b["text"] for b in buf)
        chunks.append(Chunk(
            chunk_id=f"{stem}:{idx:05d}",
            collection_id=collection_id,
            source_file=source_file,
            page_start=min(b["page"] for b in buf),
            page_end=max(b["page"] for b in buf),
            block_types=[b["type"] for b in buf],
            text=text,
            token_count=_count_tokens(text),
        ))
        buf = []
        buf_tokens = 0

    def _emit_giant(block: dict) -> None:
        for piece in _split_giant_text(block["text"], target_tokens, overlap_tokens):
            idx = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"{stem}:{idx:05d}",
                collection_id=collection_id,
                source_file=source_file,
                page_start=block["page"],
                page_end=block["page"],
                block_types=[block["type"]],
                text=piece,
                token_count=_count_tokens(piece),
            ))

    for raw in blocks:
        if not isinstance(raw, dict):
            continue
        btype = raw.get("type")
        if btype not in ALLOWED_BLOCK_TYPES:
            continue
        text = (raw.get("text") or "").strip()
        if not text:
            continue
        block = {"type": btype, "page": int(raw.get("page", 1)), "text": text}
        tokens = _count_tokens(text)

        if btype == "title":
            _flush_buffer()
            if tokens > target_tokens:
                _emit_giant(block)
            else:
                buf = [block]
                buf_tokens = tokens
            continue

        # text block
        if tokens > target_tokens:
            _flush_buffer()
            _emit_giant(block)
            continue

        if buf_tokens + tokens > target_tokens:
            _flush_buffer()
            buf = [block]
            buf_tokens = tokens
        else:
            buf.append(block)
            buf_tokens += tokens

    _flush_buffer()
    logger.info(
        "chunked collection=%s source=%s chunks=%d",
        collection_id, source_file, len(chunks),
    )
    return chunks
