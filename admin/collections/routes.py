"""HTTP routes for the Collection CRUD + per-collection file uploads."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from admin.chunks import service as chunks_svc
from admin.collections import files as files_svc
from admin.collections import service
from admin.collections.files import (
    IngestionStatus,
    InvalidContentTypeError,
    InvalidFilenameError,
    PDF_CONTENT_TYPE,
)
from admin.collections.models import CollectionType, IngestProfile
from admin.ingest import service as ingest_svc
from admin.ingest.mineru import MineruClient
from admin.ingest.runner import build_runner
from admin.config import AdminConfig
from admin.dependencies import get_config, get_minio_client, get_mineru_client

logger = logging.getLogger("admin.collections.routes")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _humansize(n: int | None) -> str:
    if not n:
        return "0 B"
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < step:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= step
    return f"{n:.1f} PB"


def _shortdate(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    text = str(value)
    return text[:16].replace("T", " ")


_MIME_STYLES = {
    "application/pdf": {"label": "PDF", "bg": "var(--surface-2)", "fg": "var(--text-muted)"},
}


def _mime_style(ct: str | None) -> dict:
    style = _MIME_STYLES.get((ct or "").lower())
    if style:
        return style
    return {"label": (ct or "FILE").split("/")[-1][:6].upper(),
            "bg": "var(--surface-2)", "fg": "var(--text-muted)"}


def _stripext(name: str) -> str:
    if not name or "." not in name:
        return name
    stem, _, _ = name.rpartition(".")
    return stem or name


templates.env.filters["humansize"] = _humansize
templates.env.filters["shortdate"] = _shortdate
templates.env.filters["mimestyle"] = _mime_style
templates.env.filters["stripext"] = _stripext

router = APIRouter(prefix="/collections", tags=["collections"])


def _prefix(cfg: AdminConfig) -> str:
    return cfg.collections_prefix()


@router.get("", name="collections.list")
def list_view(
    request: Request,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    items = service.list_all(client, bucket=cfg.minio_bucket, prefix=_prefix(cfg))
    rows = []
    for c in items:
        files = files_svc.list_files(
            client, bucket=cfg.minio_bucket, prefix=_prefix(cfg), collection_id=c.id,
        )
        counts = {"total": len(files), "pending": 0, "running": 0, "done": 0, "failed": 0}
        for f in files:
            counts[f.ingest_status.value] = counts.get(f.ingest_status.value, 0) + 1
        rows.append({"c": c, "counts": counts})
    return templates.TemplateResponse(
        request, "collections/list.html", {"rows": rows},
    )


@router.get("/new", name="collections.new")
def new_view(request: Request):
    return templates.TemplateResponse(
        request, "collections/create.html",
        {"types": [t.value for t in CollectionType]},
    )


def _validate_pdf_uploads(uploads: List[UploadFile]) -> None:
    if not uploads:
        raise HTTPException(
            status_code=400, detail="at least one PDF is required",
        )
    for u in uploads:
        ct = (u.content_type or "").lower()
        if ct != PDF_CONTENT_TYPE:
            raise HTTPException(
                status_code=415,
                detail=f"only {PDF_CONTENT_TYPE} accepted ({u.filename!r} is {ct!r})",
            )
        if not u.filename:
            raise HTTPException(status_code=400, detail="missing filename")
        try:
            files_svc.sanitize_filename(u.filename)
        except InvalidFilenameError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post("", name="collections.create")
async def create_view(
    name: str = Form(...),
    type: str = Form(...),
    files: List[UploadFile] = File(default=[]),
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    try:
        ctype = CollectionType(type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"invalid type: {type}")

    _validate_pdf_uploads(files)

    try:
        coll = service.create(
            client,
            bucket=cfg.minio_bucket,
            prefix=_prefix(cfg),
            name=name,
            type=ctype,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    for u in files:
        files_svc.upload(
            client,
            bucket=cfg.minio_bucket,
            prefix=_prefix(cfg),
            collection_id=coll.id,
            filename=u.filename or "",
            stream=u.file,
            content_type=PDF_CONTENT_TYPE,
        )
    return RedirectResponse(url=f"/collections/{coll.id}", status_code=303)


@router.get("/{collection_id}", name="collections.detail")
def detail_view(
    collection_id: str,
    request: Request,
    profile: str | None = Query(default=None),
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    ctx = _collect_status_context(client, cfg, collection_id)
    # ?profile=open mantiene el panel desplegado tras un POST /settings
    # (mejor feedback de "guardado" sin necesitar JS).
    ctx["profile_open"] = profile == "open"
    return templates.TemplateResponse(request, "collections/detail.html", ctx)


@router.post("/{collection_id}/settings", name="collections.settings.save")
def settings_save_view(
    collection_id: str,
    skip_blank_markers: bool = Form(default=False),
    skip_toc_entries: bool = Form(default=False),
    drop_short_blocks: bool = Form(default=False),
    short_block_min_words: int = Form(default=5),
    drop_small_chunks: bool = Form(default=False),
    min_chunk_tokens: int = Form(default=30),
    target_tokens: int = Form(default=500),
    overlap_tokens: int = Form(default=50),
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    # Clamp target/overlap a rangos sanos. El chunker eleva ValueError si
    # `overlap >= target` — preferimos atrapar aqui y caer a defaults.
    target = max(50, min(2000, target_tokens))
    overlap = max(0, min(target - 1, overlap_tokens))

    profile = IngestProfile(
        skip_blank_markers=skip_blank_markers,
        skip_toc_entries=skip_toc_entries,
        drop_short_blocks=drop_short_blocks,
        short_block_min_words=max(1, short_block_min_words),
        drop_small_chunks=drop_small_chunks,
        min_chunk_tokens=max(0, min_chunk_tokens),
        target_tokens=target,
        overlap_tokens=overlap,
    )
    try:
        service.update_profile(
            client, bucket=cfg.minio_bucket, prefix=_prefix(cfg),
            collection_id=collection_id, profile=profile,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="collection not found")
    # Vuelve a Overview con el panel abierto para que el usuario vea
    # los nuevos valores reflejados (feedback implicito de "guardado").
    return RedirectResponse(
        url=f"/collections/{collection_id}?profile=open",
        status_code=303,
    )


@router.post("/{collection_id}/rechunk", name="collections.rechunk")
def rechunk_view(
    collection_id: str,
    background: BackgroundTasks,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    """Aplica el IngestProfile actual a los ficheros DONE re-corriendo
    solo filter+chunker desde el text.jsonl cacheado. Sin MinerU.

    No resetea `ingest_status` — el OCR no cambia. Skipea PENDING,
    RUNNING y FAILED:
      - PENDING: aun no ingestado, no hay cache.
      - RUNNING: en flight, race risk si reescribimos su parquet.
      - FAILED: probablemente no tiene JSONL (MinerU fallo). Para
        rehabilitar, usar Retry/Re-ingest per-file desde la fila.
    """
    coll = service.get(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg),
        collection_id=collection_id,
    )
    if coll is None:
        raise HTTPException(status_code=404, detail="collection not found")
    files = files_svc.list_files(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg),
        collection_id=collection_id,
    )
    targets = [f for f in files if f.ingest_status == IngestionStatus.DONE]
    for f in targets:
        background.add_task(
            ingest_svc.rechunk_file,
            client,
            bucket=cfg.minio_bucket,
            prefix=_prefix(cfg),
            collection_id=collection_id,
            filename=f.name,
        )
    logger.info(
        "rechunk scheduled collection=%s files=%d",
        collection_id, len(targets),
    )
    return RedirectResponse(
        url=f"/collections/{collection_id}", status_code=303,
    )


@router.get("/{collection_id}/chunks", name="collections.chunks")
def chunks_view(
    collection_id: str,
    request: Request,
    source_file: str | None = Query(default=None),
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    coll = service.get(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg),
        collection_id=collection_id,
    )
    if coll is None:
        raise HTTPException(status_code=404, detail="collection not found")
    sources = chunks_svc.list_source_files(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg),
        collection_id=collection_id,
    )
    selected = source_file if source_file in sources else None
    chunks = chunks_svc.read_chunks(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg),
        collection_id=collection_id, source_file=selected,
    )
    return templates.TemplateResponse(
        request, "collections/chunks.html",
        {
            "c": coll,
            "sources": sources,
            "selected_source": selected,
            "chunks": chunks,
            "tokens_total": sum(ch.token_count for ch in chunks),
        },
    )


@router.post("/{collection_id}/delete", name="collections.delete")
def delete_view(
    collection_id: str,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    service.delete(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg), collection_id=collection_id,
    )
    return RedirectResponse(url="/collections", status_code=303)


@router.post("/{collection_id}/files", name="collections.files.upload")
async def upload_file_view(
    collection_id: str,
    files: List[UploadFile] = File(default=[]),
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    coll = service.get(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg), collection_id=collection_id,
    )
    if coll is None:
        raise HTTPException(status_code=404, detail="collection not found")

    _validate_pdf_uploads(files)

    for u in files:
        try:
            files_svc.upload(
                client,
                bucket=cfg.minio_bucket,
                prefix=_prefix(cfg),
                collection_id=collection_id,
                filename=u.filename or "",
                stream=u.file,
                content_type=PDF_CONTENT_TYPE,
            )
        except InvalidFilenameError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except InvalidContentTypeError as exc:
            raise HTTPException(status_code=415, detail=str(exc))
    return RedirectResponse(url=f"/collections/{collection_id}", status_code=303)


@router.get("/{collection_id}/files/{filename}", name="collections.files.download")
def download_file_view(
    collection_id: str,
    filename: str,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    try:
        resp = files_svc.get_file(
            client,
            bucket=cfg.minio_bucket,
            prefix=_prefix(cfg),
            collection_id=collection_id,
            filename=filename,
        )
    except InvalidFilenameError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if resp is None:
        raise HTTPException(status_code=404, detail="file not found")
    safe = files_svc.sanitize_filename(filename)
    return StreamingResponse(
        resp["Body"],
        media_type=PDF_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{safe}"'},
    )


@router.post(
    "/{collection_id}/files/{filename}/delete",
    name="collections.files.delete",
)
def delete_file_view(
    collection_id: str,
    filename: str,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    try:
        files_svc.delete_file(
            client,
            bucket=cfg.minio_bucket,
            prefix=_prefix(cfg),
            collection_id=collection_id,
            filename=filename,
        )
    except InvalidFilenameError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url=f"/collections/{collection_id}", status_code=303)


_INGESTABLE = {IngestionStatus.PENDING, IngestionStatus.FAILED}


def _collect_status_context(client, cfg: AdminConfig, collection_id: str) -> dict:
    coll = service.get(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg), collection_id=collection_id,
    )
    if coll is None:
        raise HTTPException(status_code=404, detail="collection not found")
    stored = files_svc.list_files(
        client, bucket=cfg.minio_bucket, prefix=_prefix(cfg), collection_id=collection_id,
    )
    counts = {"total": len(stored), "pending": 0, "running": 0, "done": 0, "failed": 0}
    for f in stored:
        counts[f.ingest_status.value] = counts.get(f.ingest_status.value, 0) + 1
    counts["ingestable"] = counts["pending"] + counts["failed"]
    return {
        "c": coll,
        "files": stored,
        "ingest": counts,
        "total_bytes": sum(f.size for f in stored),
    }


@router.post("/{collection_id}/ingest", name="collections.ingest")
def ingest_view(
    collection_id: str,
    background: BackgroundTasks,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
    mineru: MineruClient = Depends(get_mineru_client),
):
    ctx = _collect_status_context(client, cfg, collection_id)
    targets = [f.name for f in ctx["files"] if f.ingest_status in _INGESTABLE]
    runner = build_runner(mineru)
    for name in targets:
        background.add_task(
            ingest_svc.ingest_file,
            client,
            bucket=cfg.minio_bucket,
            prefix=_prefix(cfg),
            collection_id=collection_id,
            filename=name,
            runner=runner,
        )
    logger.info(
        "ingest scheduled collection=%s files=%d", collection_id, len(targets),
    )
    return RedirectResponse(url=f"/collections/{collection_id}", status_code=303)


@router.post(
    "/{collection_id}/files/{filename}/ingest",
    name="collections.files.ingest",
)
def ingest_file_view(
    collection_id: str,
    filename: str,
    background: BackgroundTasks,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
    mineru: MineruClient = Depends(get_mineru_client),
):
    ctx = _collect_status_context(client, cfg, collection_id)
    target = next(
        (f for f in ctx["files"] if f.name == filename), None,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="file not found")
    if target.ingest_status not in _INGESTABLE:
        # Idempotente: ya esta done/running, no encolamos otra vez.
        return RedirectResponse(url=f"/collections/{collection_id}", status_code=303)
    background.add_task(
        ingest_svc.ingest_file,
        client,
        bucket=cfg.minio_bucket,
        prefix=_prefix(cfg),
        collection_id=collection_id,
        filename=filename,
        runner=build_runner(mineru),
    )
    logger.info(
        "ingest scheduled (single) collection=%s file=%s",
        collection_id, filename,
    )
    return RedirectResponse(url=f"/collections/{collection_id}", status_code=303)


@router.get("/{collection_id}/_status", name="collections.status_partial")
def status_partial_view(
    collection_id: str,
    request: Request,
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    ctx = _collect_status_context(client, cfg, collection_id)
    ctx["oob"] = True
    return templates.TemplateResponse(request, "collections/_status.html", ctx)
