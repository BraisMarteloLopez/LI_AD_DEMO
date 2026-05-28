# TESTS

Estrategia de testing del admin. Tras Fase 1.B son ~102 tests, todos
unit/smoke con mocks de infra.

## Reglas

- **Mocks de infra a nivel de test**, nunca parcheando módulos enteros
  desde `conftest.py`.
- `tests/conftest.py` se reserva para fixtures puras: factory del cliente
  MinIO falso (`mock_minio_client`) con un `_FakeS3Backend` in-memory,
  y configs de prueba.
- Sin red ni infra real. Los tests del cliente MinerU monkeypatchean
  `requests.post`. Los tests del chunker funcionan tanto con `tiktoken`
  como con su fallback word-level (el sandbox cae al fallback).
- Cualquier test que requiera infra real (no hay ninguno aún) iría en
  `tests/integration/` con `pytest.mark.integration`.

## Layout

- `test_collections_service.py` — CRUD puro de `service.py`.
- `test_collections_files_service.py` — `sanitize_filename`, upload, list,
  get, delete.
- `test_routes_collections.py` — endpoints CRUD + lista con resumen de
  ingesta.
- `test_routes_files.py` — upload/download/delete por colección.
- `test_routes_ingest.py` — `POST /ingest`, `POST /files/{name}/ingest`,
  `GET /_status` partial, polling cuando `running > 0`.
- `test_ingest_service.py` — transiciones `PENDING/RUNNING/DONE/FAILED`.
- `test_ingest_mineru.py` — `MineruClient` con `requests.post` mockeado
  (incluye `content_list` como string JSON).
- `test_ingest_runner.py` — filter_blocks + persistencia de
  `text.jsonl` + chunks parquet.
- `test_ingest_chunker.py` — agrupado, title abre chunk, bloque gigante
  con overlap, determinismo.
- `test_ingest_chunks_io.py` — round-trip parquet con pyarrow.

## Comando

```bash
python -m pytest -q
```
