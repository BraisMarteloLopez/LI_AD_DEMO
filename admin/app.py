"""FastAPI app entrypoint. Run: `uvicorn admin.app:app --reload`."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from admin.collections.routes import router as collections_router
from admin.config import AdminConfig
from admin.dependencies import get_config, get_minio_client
from admin.logging_setup import setup_logging

logger = logging.getLogger("admin.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    setup_logging(cfg.log_level)
    errors = cfg.validate()
    if errors:
        for err in errors:
            logger.error("config error: %s", err)
        raise RuntimeError(f"AdminConfig invalido: {errors}")
    logger.info("admin starting on %s:%s", cfg.host, cfg.port)
    yield
    logger.info("admin shutting down")


app = FastAPI(title="LI_AD - Admin RAG", lifespan=lifespan)
app.include_router(collections_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/collections", status_code=303)


@app.get("/health")
def health(
    cfg: AdminConfig = Depends(get_config),
    client=Depends(get_minio_client),
):
    minio_ok = True
    detail: str | None = None
    try:
        client.head_bucket(Bucket=cfg.minio_bucket)
    except (ClientError, BotoCoreError) as exc:
        minio_ok = False
        detail = str(exc)
        logger.warning("health: minio head_bucket failed: %s", exc)
    status = "ok" if minio_ok else "error"
    body = {"status": status, "minio": minio_ok, "bucket": cfg.minio_bucket}
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=200 if minio_ok else 503)
