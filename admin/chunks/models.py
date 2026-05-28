"""Chunk dataclass for the read path (UI consumption).

Estructuralmente igual al `Chunk` que produce el chunker
(`admin/ingest/chunker.py`); separado para no acoplar el modulo de
lectura al de escritura. Cuando CH_LIRAG publique su contrato (D4 en
CLAUDE.md), este modulo + `service.py` se sustituyen sin tocar route
ni template.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    collection_id: str
    source_file: str
    page_start: int
    page_end: int
    block_types: Tuple[str, ...] = field(default_factory=tuple)
    text: str = ""
    token_count: int = 0

    @property
    def page_label(self) -> str:
        if self.page_start == self.page_end:
            return str(self.page_start)
        return f"{self.page_start}–{self.page_end}"

    @property
    def block_types_display(self) -> List[Tuple[str, int]]:
        """Unique block types con su contador, preservando orden first-seen.

        El chunker emite `block_types` en orden de documento: si un chunk
        empieza con un titulo y sigue con N parrafos, llega como
        `("title", "text", "text", ...)`. Mostrar tal cual genera 30
        píldoras "text" apiladas — inutil. Aqui devolvemos
        `[("title", 1), ("text", N)]` para render compacto en la UI.
        """
        counts: dict = {}
        for t in self.block_types:
            counts[t] = counts.get(t, 0) + 1
        return list(counts.items())

    def text_snippet(self, max_chars: int = 200) -> str:
        text = (self.text or "").strip().replace("\n", " ")
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1].rstrip() + "…"
