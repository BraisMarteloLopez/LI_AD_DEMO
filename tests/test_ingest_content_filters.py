"""Tests for admin.ingest.content_filters (pre/post-chunker filters)."""
from __future__ import annotations

from admin.collections.models import IngestProfile
from admin.ingest.chunker import Chunk
from admin.ingest.content_filters import (
    apply_default_chunk_filters,
    apply_default_filters,
    apply_profile_chunk_filters,
    apply_profile_filters,
    drop_blank_markers,
    drop_short_blocks,
    drop_small_chunks,
    drop_toc_entries,
)


def _b(text, type_="text", page=1, **extra):
    return {"page": page, "type": type_, "text": text, **extra}


def _ch(idx, tokens, text="x"):
    return Chunk(
        chunk_id=f"doc:{idx:05d}",
        collection_id="c", source_file="doc.pdf",
        page_start=1, page_end=1,
        block_types=["text"], text=text, token_count=tokens,
    )


# --- drop_blank_markers ---


class TestDropBlankMarkers:
    def test_drops_es_pagina_en_blanco_intencionadamente(self):
        blocks = [_b("Página en blanco intencionadamente")]
        assert drop_blank_markers(blocks) == []

    def test_drops_es_pagina_en_blanco_lowercase(self):
        blocks = [_b("página en blanco")]
        assert drop_blank_markers(blocks) == []

    def test_drops_es_without_accent(self):
        blocks = [_b("pagina en blanco")]
        assert drop_blank_markers(blocks) == []

    def test_drops_es_esta_pagina_dejada(self):
        blocks = [_b("Esta página ha sido dejada en blanco intencionadamente")]
        assert drop_blank_markers(blocks) == []

    def test_drops_en_intentionally_left_blank(self):
        blocks = [_b("This page intentionally left blank")]
        assert drop_blank_markers(blocks) == []

    def test_drops_en_this_page_blank(self):
        blocks = [_b("THIS PAGE IS BLANK")]
        assert drop_blank_markers(blocks) == []

    def test_keeps_prose_mentioning_pagina_web(self):
        blocks = [_b("Visita nuestra página web para más información sobre el tema")]
        assert len(drop_blank_markers(blocks)) == 1

    def test_keeps_block_without_marker(self):
        blocks = [_b("El helicóptero AH-64 Apache es un caza ataque biplaza")]
        assert len(drop_blank_markers(blocks)) == 1

    def test_preserves_block_metadata(self):
        blocks = [
            _b("Buen contenido aquí mismo", page=3, bbox=[1, 2, 3, 4], text_level=2),
            _b("Página en blanco"),
        ]
        out = drop_blank_markers(blocks)
        assert len(out) == 1
        assert out[0]["page"] == 3
        assert out[0]["bbox"] == [1, 2, 3, 4]
        assert out[0]["text_level"] == 2


# --- drop_toc_entries ---


class TestDropTocEntries:
    def test_drops_es_with_spaced_dots(self):
        blocks = [_b("SIGLAS Y ABREVIATURAS . . 18")]
        assert drop_toc_entries(blocks) == []

    def test_drops_es_with_many_consecutive_dots(self):
        blocks = [_b("Bibliografía .............. 45")]
        assert drop_toc_entries(blocks) == []

    def test_drops_with_middle_dot_leader(self):
        blocks = [_b("Capítulo 3 · · · · 45")]
        assert drop_toc_entries(blocks) == []

    def test_drops_with_dash_leader(self):
        blocks = [_b("Sección A - - - - 12")]
        assert drop_toc_entries(blocks) == []

    def test_drops_with_chapter_number_prefix(self):
        blocks = [_b("3.1 Análisis de resultados . . . . 45")]
        assert drop_toc_entries(blocks) == []

    def test_keeps_prose_ending_in_year(self):
        # "Reino Unido tiene previsto ... 2030" — no leaders, no drop.
        blocks = [_b("Reino Unido tiene previsto reemplazar sus helicópteros en 2030")]
        assert len(drop_toc_entries(blocks)) == 1

    def test_keeps_text_with_only_one_dot(self):
        # Abreviaturas o frases con un solo punto no deben matchear.
        blocks = [_b("Sr. González escribió un informe sobre el tema 1234")]
        assert len(drop_toc_entries(blocks)) == 1

    def test_keeps_text_with_ellipsis_but_no_trailing_number(self):
        blocks = [_b("Esto es un texto que termina con puntos suspensivos...")]
        assert len(drop_toc_entries(blocks)) == 1

    def test_keeps_text_with_dots_but_no_trailing_digits(self):
        blocks = [_b("a . . . . . sin número")]
        assert len(drop_toc_entries(blocks)) == 1

    def test_keeps_block_that_is_pure_number(self):
        # "18" solo no es TOC entry (le falta titulo + leaders).
        blocks = [_b("18")]
        assert len(drop_toc_entries(blocks)) == 1

    def test_preserves_normal_blocks_when_dropping_toc(self):
        blocks = [
            _b("BIBLIOGRAFÍA . . 18"),
            _b("Reino Unido tiene previsto reemplazar helicópteros pronto"),
            _b("3.1 Resumen ejecutivo . . . . 5"),
        ]
        out = drop_toc_entries(blocks)
        assert len(out) == 1
        assert "Reino Unido" in out[0]["text"]


# --- drop_short_blocks ---


class TestDropShortBlocks:
    def test_drops_text_below_threshold(self):
        blocks = [_b("solo cuatro palabras aqui")]
        assert drop_short_blocks(blocks, min_words=5) == []

    def test_keeps_text_at_threshold(self):
        blocks = [_b("una dos tres cuatro cinco")]
        assert len(drop_short_blocks(blocks, min_words=5)) == 1

    def test_keeps_text_above_threshold(self):
        blocks = [_b("una dos tres cuatro cinco seis siete")]
        assert len(drop_short_blocks(blocks, min_words=5)) == 1

    def test_keeps_titles_regardless_of_length(self):
        # Un titulo de 1 palabra ("RESUMEN") es estructural — se conserva.
        blocks = [_b("RESUMEN", type_="title")]
        assert len(drop_short_blocks(blocks, min_words=5)) == 1

    def test_keeps_titles_even_when_text_blocks_dropped(self):
        blocks = [
            _b("RESUMEN", type_="title"),
            _b("solo dos palabras"),
            _b("INTRODUCCIÓN", type_="title"),
        ]
        out = drop_short_blocks(blocks, min_words=5)
        assert len(out) == 2
        assert all(b["type"] == "title" for b in out)

    def test_threshold_is_configurable(self):
        blocks = [_b("una dos tres")]
        assert len(drop_short_blocks(blocks, min_words=2)) == 1
        assert len(drop_short_blocks(blocks, min_words=5)) == 0

    def test_default_threshold_is_five_words(self):
        blocks = [_b("una dos tres cuatro")]  # 4 words
        assert drop_short_blocks(blocks) == []
        blocks = [_b("una dos tres cuatro cinco")]  # 5 words
        assert len(drop_short_blocks(blocks)) == 1

    def test_strips_whitespace_before_counting(self):
        blocks = [_b("   solo  dos   ")]
        assert drop_short_blocks(blocks, min_words=3) == []


# --- apply_default_filters ---


class TestApplyDefaultFilters:
    def test_real_world_mix(self):
        blocks = [
            _b("Página en blanco intencionadamente"),
            _b("BIBLIOGRAFÍA . . 18"),
            _b("solo cuatro palabras aqui"),
            _b("RESUMEN", type_="title"),
            _b("Reino Unido tiene previsto reemplazar sus helicópteros para 2030"),
            _b("Capítulo 1 . . 5"),
            _b("Como consecuencia del último conflicto, los países han mejorado sus modelos"),
        ]
        out = apply_default_filters(blocks)
        # Sobreviven: el title corto, los dos bloques de prosa larga.
        assert len(out) == 3
        texts = [b["text"] for b in out]
        assert "RESUMEN" in texts
        assert any("Reino Unido" in t for t in texts)
        assert any("último conflicto" in t for t in texts)

    def test_idempotent_on_clean_input(self):
        clean = [
            _b("RESUMEN", type_="title"),
            _b("Como consecuencia del último conflicto bélico mundial, los países"),
        ]
        assert apply_default_filters(clean) == clean

    def test_empty_input_returns_empty(self):
        assert apply_default_filters([]) == []

    def test_returns_new_list_does_not_mutate(self):
        blocks = [_b("Página en blanco"), _b("contenido valido y suficientemente largo aqui")]
        original_len = len(blocks)
        out = apply_default_filters(blocks)
        # Input lista intacta.
        assert len(blocks) == original_len
        assert len(out) == 1

    def test_preserves_optional_metadata_through_pipeline(self):
        blocks = [
            _b("contenido valido y suficientemente largo para sobrevivir filtros",
               page=3, bbox=[1.0, 2.0, 3.0, 4.0], text_level=1),
            _b("BIBLIOGRAFÍA . . 18"),
        ]
        out = apply_default_filters(blocks)
        assert len(out) == 1
        assert out[0]["bbox"] == [1.0, 2.0, 3.0, 4.0]
        assert out[0]["text_level"] == 1
        assert out[0]["page"] == 3


# --- drop_small_chunks ---


class TestDropSmallChunks:
    def test_drops_below_threshold(self):
        chunks = [_ch(0, 10), _ch(1, 50)]
        out = drop_small_chunks(chunks, min_tokens=30)
        assert len(out) == 1
        assert out[0].token_count == 50

    def test_keeps_at_threshold(self):
        out = drop_small_chunks([_ch(0, 30)], min_tokens=30)
        assert len(out) == 1

    def test_empty_list(self):
        assert drop_small_chunks([]) == []

    def test_does_not_renumber_chunk_ids_preserves_gaps(self):
        # IDs originales: 0,1,2,3. Tras drop de los chicos, sobreviven
        # 1 y 3 — los IDs NO se compactan (gap aceptado).
        chunks = [_ch(0, 5), _ch(1, 50), _ch(2, 5), _ch(3, 50)]
        out = drop_small_chunks(chunks, min_tokens=30)
        assert [c.chunk_id for c in out] == ["doc:00001", "doc:00003"]

    def test_threshold_configurable(self):
        chunks = [_ch(0, 5)]
        assert drop_small_chunks(chunks, min_tokens=10) == []
        assert drop_small_chunks(chunks, min_tokens=3) == chunks

    def test_default_threshold_is_30_tokens(self):
        # 25 cae, 35 sobrevive con default.
        chunks = [_ch(0, 25), _ch(1, 35)]
        out = drop_small_chunks(chunks)
        assert len(out) == 1
        assert out[0].token_count == 35


class TestApplyDefaultChunkFilters:
    def test_drops_small_chunks(self):
        chunks = [_ch(0, 10), _ch(1, 50)]
        out = apply_default_chunk_filters(chunks)
        assert len(out) == 1

    def test_returns_new_list_does_not_mutate(self):
        chunks = [_ch(0, 10), _ch(1, 50)]
        original_len = len(chunks)
        out = apply_default_chunk_filters(chunks)
        assert len(chunks) == original_len
        assert len(out) == 1


# --- apply_profile_filters / apply_profile_chunk_filters ---


def _mixed_blocks():
    return [
        _b("Página en blanco intencionadamente"),
        _b("BIBLIOGRAFÍA . . 18"),
        _b("solo cuatro palabras aqui"),
        _b("RESUMEN", type_="title"),
        _b("Como consecuencia del último conflicto, los países han mejorado sus modelos de helicópteros existentes y han incorporado nuevas versiones más capaces de combate."),
    ]


class TestApplyProfileFilters:
    def test_all_flags_on_matches_default_filters(self):
        # Profile() = todos los defaults, equivale a apply_default_filters.
        blocks = _mixed_blocks()
        assert apply_profile_filters(blocks, IngestProfile()) == apply_default_filters(blocks)

    def test_all_flags_off_returns_input_unchanged(self):
        profile = IngestProfile(
            skip_blank_markers=False, skip_toc_entries=False, drop_short_blocks=False,
        )
        blocks = _mixed_blocks()
        assert apply_profile_filters(blocks, profile) == blocks

    def test_only_blank_markers_active(self):
        profile = IngestProfile(
            skip_blank_markers=True, skip_toc_entries=False, drop_short_blocks=False,
        )
        out = apply_profile_filters(_mixed_blocks(), profile)
        # blank desaparece; TOC y short sobreviven.
        texts = [b["text"] for b in out]
        assert "Página en blanco intencionadamente" not in texts
        assert "BIBLIOGRAFÍA . . 18" in texts
        assert "solo cuatro palabras aqui" in texts

    def test_only_toc_active(self):
        profile = IngestProfile(
            skip_blank_markers=False, skip_toc_entries=True, drop_short_blocks=False,
        )
        out = apply_profile_filters(_mixed_blocks(), profile)
        texts = [b["text"] for b in out]
        assert "BIBLIOGRAFÍA . . 18" not in texts
        assert "Página en blanco intencionadamente" in texts

    def test_short_blocks_uses_profile_threshold(self):
        # min_words=3 -> "solo cuatro palabras aqui" (4) sobrevive.
        profile = IngestProfile(
            skip_blank_markers=False, skip_toc_entries=False,
            drop_short_blocks=True, short_block_min_words=3,
        )
        out = apply_profile_filters([_b("solo cuatro palabras aqui")], profile)
        assert len(out) == 1
        # min_words=10 -> mismo bloque ya no.
        profile = IngestProfile(
            skip_blank_markers=False, skip_toc_entries=False,
            drop_short_blocks=True, short_block_min_words=10,
        )
        out = apply_profile_filters([_b("solo cuatro palabras aqui")], profile)
        assert out == []


class TestApplyProfileChunkFilters:
    def test_all_flags_on_matches_default(self):
        chunks = [_ch(0, 10), _ch(1, 50)]
        assert apply_profile_chunk_filters(chunks, IngestProfile()) == apply_default_chunk_filters(chunks)

    def test_drop_small_chunks_off_returns_all(self):
        profile = IngestProfile(drop_small_chunks=False)
        chunks = [_ch(0, 5), _ch(1, 50)]
        assert apply_profile_chunk_filters(chunks, profile) == chunks

    def test_threshold_from_profile(self):
        chunks = [_ch(0, 40), _ch(1, 80)]
        # umbral 50 -> solo el de 80 sobrevive
        profile = IngestProfile(drop_small_chunks=True, min_chunk_tokens=50)
        out = apply_profile_chunk_filters(chunks, profile)
        assert len(out) == 1
        assert out[0].token_count == 80
        # umbral 10 -> ambos
        profile = IngestProfile(drop_small_chunks=True, min_chunk_tokens=10)
        out = apply_profile_chunk_filters(chunks, profile)
        assert len(out) == 2
