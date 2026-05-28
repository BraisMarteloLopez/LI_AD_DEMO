"""Collection domain model."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict


class CollectionType(str, Enum):
    PLAYGROUND = "playground"


class CollectionState(str, Enum):
    CREATED = "created"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def new_collection_id(now: datetime | None = None) -> str:
    when = (now or datetime.now(tz=timezone.utc)).strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"col_{when}_{short}"


@dataclass
class IngestProfile:
    """Per-collection ingest tuning. Persistido en meta.json.

    Defaults = lo que aplica PR A automaticamente. El usuario puede
    desactivar individualmente desde la seccion Ingestion profile en
    el detalle de la coleccion.
    """
    skip_blank_markers: bool = True
    skip_toc_entries: bool = True
    drop_short_blocks: bool = True
    short_block_min_words: int = 5
    drop_small_chunks: bool = True
    min_chunk_tokens: int = 30
    # Chunker: tamano objetivo y solape entre chunks consecutivos.
    # Defaults coinciden con CHUNK_TARGET_TOKENS/CHUNK_OVERLAP_TOKENS
    # en admin/ingest/chunker.py. Caben con holgura en el cap interno
    # de CH_LIRAG (max_text_chars=3000, ~700-1000 tokens).
    target_tokens: int = 500
    overlap_tokens: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_default(self) -> bool:
        return self == IngestProfile()

    def summary(self) -> str:
        """One-line summary para el header colapsado del panel.

        Ejemplos:
          'All filters active'                                  (default)
          '3 of 4 filters active'                               (toggle off)
          'All filters active · min words 10'                   (custom thr)
          'All filters active · target 800 / overlap 100'       (custom chunker)
          '3 of 4 filters active · min chunk tokens 50 · target 800 / overlap 100'
        """
        active = sum([
            self.skip_blank_markers,
            self.skip_toc_entries,
            self.drop_short_blocks,
            self.drop_small_chunks,
        ])
        defaults = IngestProfile()
        parts = []
        if active == 4:
            parts.append("All filters active")
        else:
            parts.append(f"{active} of 4 filters active")
        if self.short_block_min_words != defaults.short_block_min_words:
            parts.append(f"min words {self.short_block_min_words}")
        if self.min_chunk_tokens != defaults.min_chunk_tokens:
            parts.append(f"min chunk tokens {self.min_chunk_tokens}")
        # Chunker: cuando ambos coinciden con default, no se muestra.
        # Cuando alguno difiere, mostramos el par para que la relacion
        # target/overlap quede explicita.
        if (self.target_tokens != defaults.target_tokens
                or self.overlap_tokens != defaults.overlap_tokens):
            parts.append(f"target {self.target_tokens} / overlap {self.overlap_tokens}")
        return " · ".join(parts)

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "IngestProfile":
        """Tolerante: si meta.json no trae profile (colecciones pre-PR-B),
        devuelve defaults. Si trae solo algunos campos, los demas defaults.
        Tipos malformados caen al default del campo correspondiente.

        Para el par chunker (target_tokens / overlap_tokens), si la
        relacion `overlap < target` se rompe (p.ej. ambos personalizados
        pero con valores invalidos), ambos caen al default — el chunker
        hace `raise ValueError` si recibe valores invalidos.
        """
        if not data:
            return cls()
        defaults = cls()

        def _bool(key: str) -> bool:
            v = data.get(key)
            return getattr(defaults, key) if not isinstance(v, bool) else v

        def _int(key: str, *, min_value: int = 0) -> int:
            v = data.get(key)
            try:
                iv = int(v)
                return iv if iv >= min_value else getattr(defaults, key)
            except (TypeError, ValueError):
                return getattr(defaults, key)

        target = _int("target_tokens", min_value=1)
        overlap = _int("overlap_tokens", min_value=0)
        if overlap >= target:
            target = defaults.target_tokens
            overlap = defaults.overlap_tokens

        return cls(
            skip_blank_markers=_bool("skip_blank_markers"),
            skip_toc_entries=_bool("skip_toc_entries"),
            drop_short_blocks=_bool("drop_short_blocks"),
            short_block_min_words=_int("short_block_min_words", min_value=1),
            drop_small_chunks=_bool("drop_small_chunks"),
            min_chunk_tokens=_int("min_chunk_tokens", min_value=0),
            target_tokens=target,
            overlap_tokens=overlap,
        )


@dataclass
class Collection:
    id: str
    name: str
    type: CollectionType
    state: CollectionState = CollectionState.CREATED
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    schema_version: int = 1
    ingest_profile: IngestProfile = field(default_factory=IngestProfile)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        d["state"] = self.state.value
        # asdict() ya convierte ingest_profile (dataclass) a dict, no hace
        # falta tocarlo. Solo dejamos los enums como string.
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collection":
        return cls(
            id=data["id"],
            name=data["name"],
            type=CollectionType(data["type"]),
            state=CollectionState(data["state"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            schema_version=int(data.get("schema_version", 1)),
            ingest_profile=IngestProfile.from_dict(data.get("ingest_profile")),
        )
