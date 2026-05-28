"""Tests for admin.ingest.chunker (pure algorithm, no MinIO)."""
from __future__ import annotations

import pytest

from admin.ingest.chunker import (
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TARGET_TOKENS,
    Chunk,
    _count_tokens,
    _split_giant_text,
    chunk_text_blocks,
)


def _blocks(*items):
    """Shortcut: _blocks(('text', 1, 'hello'), ('title', 2, 'H')) -> list of dicts."""
    return [{"type": t, "page": p, "text": x} for (t, p, x) in items]


def _call(blocks, *, target=20, overlap=5):
    return chunk_text_blocks(
        blocks,
        collection_id="col_x",
        source_file="Libro.pdf",
        target_tokens=target,
        overlap_tokens=overlap,
    )


def test_empty_input_returns_empty():
    assert _call([]) == []


def test_single_small_block_yields_one_chunk():
    [c] = _call(_blocks(("text", 1, "hola mundo")))
    assert c.chunk_id == "Libro:00000"
    assert c.collection_id == "col_x"
    assert c.source_file == "Libro.pdf"
    assert c.page_start == 1 and c.page_end == 1
    assert c.block_types == ["text"]
    assert c.text == "hola mundo"
    assert c.token_count == _count_tokens("hola mundo")


def test_consecutive_text_blocks_group_into_one_chunk():
    chunks = _call(_blocks(
        ("text", 1, "una frase"),
        ("text", 2, "otra frase"),
    ), target=50, overlap=5)
    assert len(chunks) == 1
    assert chunks[0].text == "una frase\n\notra frase"
    assert chunks[0].block_types == ["text", "text"]
    assert chunks[0].page_start == 1 and chunks[0].page_end == 2


def test_title_closes_current_chunk_and_opens_new_one():
    chunks = _call(_blocks(
        ("text",  1, "body a"),
        ("title", 2, "Section"),
        ("text",  2, "body b"),
    ), target=50, overlap=5)
    assert len(chunks) == 2
    assert chunks[0].block_types == ["text"]
    assert chunks[0].text == "body a"
    assert chunks[1].block_types == ["title", "text"]
    assert chunks[1].text.startswith("Section")


def test_chunk_flushes_when_target_tokens_would_be_exceeded():
    long = "palabra " * 15   # ~15 tokens
    chunks = _call(_blocks(
        ("text", 1, long),
        ("text", 1, long),
        ("text", 1, long),
    ), target=20, overlap=5)
    assert len(chunks) == 3
    for c in chunks:
        assert c.token_count <= 20 + 3  # margen por tokens de whitespace


def test_giant_text_block_splits_with_overlap():
    big = "alpha beta gamma delta " * 30  # ~90 tokens
    chunks = _call(_blocks(("text", 4, big)), target=20, overlap=5)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.page_start == 4 and c.page_end == 4
        assert c.block_types == ["text"]
        assert c.token_count <= 20 + 3
    # IDs correlativos
    assert [c.chunk_id for c in chunks] == [
        f"Libro:{i:05d}" for i in range(len(chunks))
    ]


def test_page_range_spans_blocks_in_chunk():
    chunks = _call(_blocks(
        ("text", 1, "p1 short"),
        ("text", 3, "p3 short"),
    ), target=50, overlap=5)
    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 3


def test_ignores_unknown_block_types_and_empty_text():
    chunks = _call([
        {"type": "image", "page": 1, "text": "desc"},
        {"type": "table", "page": 1, "text": "cells"},
        {"type": "text",  "page": 1, "text": "   "},
        {"type": "text",  "page": 1, "text": "valido"},
    ], target=50, overlap=5)
    assert [c.text for c in chunks] == ["valido"]


def test_chunker_is_deterministic():
    blocks = _blocks(
        ("title", 1, "Intro"),
        ("text",  1, "body one"),
        ("text",  2, "body two"),
        ("title", 3, "Conclusion"),
        ("text",  3, "end"),
    )
    a = _call(blocks, target=30, overlap=5)
    b = _call(blocks, target=30, overlap=5)
    assert a == b


def test_giant_title_is_split_like_text():
    chunks = _call(_blocks(
        ("title", 2, "alpha beta gamma " * 30),
    ), target=20, overlap=5)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.block_types == ["title"]
        assert c.page_start == 2 and c.page_end == 2


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        _call(_blocks(("text", 1, "x")), target=10, overlap=10)


def test_defaults_use_module_constants():
    # sanity: no cambiamos los defaults sin querer
    assert CHUNK_TARGET_TOKENS == 500
    assert CHUNK_OVERLAP_TOKENS == 50


def test_split_helper_respects_overlap():
    # 100 tokens, target 20, overlap 5 -> step=15 -> ventanas en 0,15,30,...
    text = " ".join(str(i) for i in range(100))
    pieces = _split_giant_text(text, target_tokens=20, overlap_tokens=5)
    # cada pieza <= 20 tokens y hay al menos 5
    assert all(_count_tokens(p) <= 20 for p in pieces)
    assert len(pieces) >= 5
