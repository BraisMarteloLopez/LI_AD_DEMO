"""Pre/post-chunker content filters.

Funciones puras sobre la lista de bloques que produce
`admin.ingest.runner.filter_blocks` (texto + tipo + pagina + opcional
bbox/text_level). Cada filtro toma una lista y devuelve una lista
nueva — no mutan, no llaman a IO.

Composicion:
  - `apply_profile_filters(blocks, profile)` aplica los filtros
    block-level segun los flags del IngestProfile.
  - `apply_profile_chunk_filters(chunks, profile)` idem para
    chunk-level.
  - `apply_default_filters` / `apply_default_chunk_filters` son
    aliases que usan IngestProfile() (todos los defaults).

Diseno: regex y umbrales son **conservadores** para minimizar falsos
positivos. Mejor dejar pasar algo de ruido que descartar contenido
util por accidente.
"""
from __future__ import annotations

import re
from typing import Iterable, List

from admin.collections.models import IngestProfile

# --- Heuristic constants ---

# Blank-page markers en ES + EN. Match dentro del texto del bloque
# (case-insensitive). MinerU suele emitir estos marcadores como un
# bloque aislado en la pagina vacia.
_BLANK_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"p[áa]gina\s+en\s+blanco", re.IGNORECASE),
    re.compile(r"intentionally\s+left\s+blank", re.IGNORECASE),
    re.compile(r"esta\s+p[áa]gina.{0,40}?(?:dejada|blanco)", re.IGNORECASE),
    re.compile(r"this\s+page.{0,40}?blank", re.IGNORECASE),
)

# TOC entry: <title> <2+ dot-like separators> <page number>.
# Acepta ".", "·" (middle dot, U+00B7) y guion "-" como leader.
# Requiere min 2 leaders para evitar falsos positivos como abreviaturas
# ("Sr. Gonzalez 1234"). Usa `.+?` non-greedy para que `\s*` antes de
# los leaders pueda comer cualquier whitespace residual.
_TOC_PATTERN = re.compile(
    r"^\s*.+?\s*(?:[\.·\-]\s*){2,}\s*\d+\s*$",
)

# Default umbrales — alineados con valores razonables; ajustables en
# Ola 2 via IngestProfile.
DEFAULT_MIN_BLOCK_WORDS = 5
DEFAULT_MIN_CHUNK_TOKENS = 30


# --- Filters ---


def drop_blank_markers(blocks: Iterable[dict]) -> List[dict]:
    """Drop blocks whose text contains a blank-page marker (ES/EN)."""
    out: List[dict] = []
    for b in blocks:
        text = (b.get("text") or "")
        if any(p.search(text) for p in _BLANK_PATTERNS):
            continue
        out.append(b)
    return out


def drop_toc_entries(blocks: Iterable[dict]) -> List[dict]:
    """Drop blocks matching the TOC dot-leader pattern.

    Empareja `"<titulo> . . . . <pagina>"` y variantes con punto
    medio (`·`) o guion (`-`). Requiere minimo 2 separadores para
    no descartar abreviaturas o referencias.
    """
    out: List[dict] = []
    for b in blocks:
        text = (b.get("text") or "").strip()
        if _TOC_PATTERN.match(text):
            continue
        out.append(b)
    return out


def drop_short_blocks(
    blocks: Iterable[dict], *, min_words: int = DEFAULT_MIN_BLOCK_WORDS,
) -> List[dict]:
    """Drop text blocks with fewer than `min_words` whitespace-tokens.

    Los bloques `type=title` se conservan **siempre** — son
    estructurales y casi siempre cortos por naturaleza ("RESUMEN",
    "1 INTRODUCCION").
    """
    out: List[dict] = []
    for b in blocks:
        if b.get("type") == "title":
            out.append(b)
            continue
        text = (b.get("text") or "").strip()
        if len(text.split()) >= min_words:
            out.append(b)
    return out


# --- Composition ---


def apply_profile_filters(
    blocks: Iterable[dict], profile: IngestProfile,
) -> List[dict]:
    """Compose block-level filters segun los flags del profile.

    Orden estable: blank → TOC → short. Cada paso es opt-out via
    el flag correspondiente.
    """
    out = list(blocks)
    if profile.skip_blank_markers:
        out = drop_blank_markers(out)
    if profile.skip_toc_entries:
        out = drop_toc_entries(out)
    if profile.drop_short_blocks:
        out = drop_short_blocks(out, min_words=profile.short_block_min_words)
    return out


def apply_default_filters(blocks: Iterable[dict]) -> List[dict]:
    """Alias historico — equivale a apply_profile_filters con
    IngestProfile() (todos los defaults). Mantenido por callers que
    no tienen un profile a mano."""
    return apply_profile_filters(blocks, IngestProfile())


# --- Chunk-level filters ---


def drop_small_chunks(chunks, *, min_tokens: int = DEFAULT_MIN_CHUNK_TOKENS):
    """Drop chunks con token_count debajo del umbral.

    Safety net: el chunker acumula bloques para llegar a target_tokens.
    Si los pre-chunk filters dejaron un grupo de bloques que totalizan
    poco (ej. solo un title sin body, o el ultimo chunk de un fichero
    con pocos bloques sobrevivientes), puede quedar un chunk
    fragmentario que no aporta retrieval semantico.

    **No renumera `chunk_id`s tras el drop**. Los IDs son secuenciales
    al chunking original; el parquet se lee por iteracion, no por
    enumeracion, asi que dispersion en IDs es contractualmente
    aceptable y mas simple.
    """
    return [c for c in chunks if c.token_count >= min_tokens]


def apply_profile_chunk_filters(chunks, profile: IngestProfile):
    """Compose chunk-level filters segun los flags del profile."""
    out = list(chunks)
    if profile.drop_small_chunks:
        out = drop_small_chunks(out, min_tokens=profile.min_chunk_tokens)
    return out


def apply_default_chunk_filters(chunks):
    """Alias historico — equivale a apply_profile_chunk_filters con
    IngestProfile() (todos los defaults)."""
    return apply_profile_chunk_filters(chunks, IngestProfile())
