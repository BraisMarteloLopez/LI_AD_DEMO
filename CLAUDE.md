# LI_AD — Admin del sistema RAG (CH_LIRAG)

Este repo es el **admin** de un sistema RAG. El motor vive en
[CH_LIRAG](https://github.com/BraisMarteloLopez/CH_LIRAG) y ejecuta retrieval +
generación. El admin **gestiona** (CRUD de colecciones, ingesta de PDFs,
lifecycle de Knowledge Graphs, orquestación de evaluaciones) pero **no
ejecuta**. Dependencia unidireccional: admin importa motor; motor no sabe del
admin. Contrato entre ambos: MinIO/Parquet.

## Stack

- Python 3.10+
- FastAPI + Jinja2 + HTMX (UI server-rendered)
- boto3 contra MinIO (S3-compatible)
- NVIDIA NIM (embedding + LLM, vía el motor)

## Arrancar local

```bash
cp .env.example .env  # ajustar valores si procede
pip install -r requirements.txt
uvicorn admin.app:app --reload --port 8080
```

## Layout

```
admin/
  app.py              FastAPI entrypoint + /health + lifespan
  config.py           AdminConfig dataclass + from_env() + validate()
  dependencies.py     get_config() / get_minio_client() / get_mineru_client() (lru_cache)
  logging_setup.py    JSONL formatter
  templates/
    base.html         Layout, paleta, dropzone CSS, busy-button JS
    _dropzone.html    Partial reusable de drag-and-drop (PDF only)
    collections/
      list.html       Tabla con resumen de ingesta por fila
      create.html     Form de creacion + dropzone obligatorio
      detail.html     Cabecera + panel + dropzone + tabla de ficheros
      _ingest_panel.html  Panel de estado con polling HTMX cuando running > 0
      _files_table.html   Tabla de ficheros (OOB-swappable)
      _status.html        Combinado para el endpoint /_status
  collections/
    models.py         CollectionType / CollectionState / Collection dataclass
    service.py        CRUD puro contra MinIO (create/get/list/delete)
    files.py          PDF storage + IngestionStatus + sanitize/upload/list/get/delete
    routes.py         HTTP routes (CRUD, upload, ingest, partial _status)
  ingest/
    service.py        ingest_file(client, ..., runner=...) con transiciones de estado
    mineru.py         MineruClient HTTP contra /file_parse + MineruResult
    runner.py         build_runner(mineru): download -> mineru -> filtro -> jsonl -> chunks
    chunker.py        chunk_text_blocks() determinista + tiktoken con fallback offline
    chunks_io.py      pyarrow Schema + write_chunks (provisional, ver D4)
tests/                pytest, mocks de infra a nivel de test
```

## Convenciones

- **Config** vía `.env` + dataclass validada (`AdminConfig.from_env().validate()`).
  No side-effects globales: las dependencias se construyen vía `lru_cache` en
  `admin/dependencies.py`.
- **Logging** JSONL estructurado (`admin/logging_setup.py`). Configurado en el
  `lifespan` de la app.
- **Mocks** de infra a nivel de función/test, **nunca módulos enteros**. Las
  fixtures de `tests/conftest.py` devuelven un `MagicMock` del cliente MinIO,
  no parchean `boto3` globalmente.
- **Comentarios**: por defecto, ninguno. Solo cuando el WHY no es obvio (un
  workaround, una invariante sutil, una restricción no expresable en código).
- **Idioma**: variables, nombres y docstrings en inglés. Comentarios y prosa
  pueden mezclar inglés y español (histórico del motor).
- **Estructura de bucket**: el admin reserva el prefijo `ADMIN_ROOT_PREFIX`
  (default `admin/`) dentro del bucket compartido con el motor (`lakehouse`).
  Decisión D1: convivir en el mismo bucket con namespace propio (ver más abajo).

## Estructura en MinIO

```
{MINIO_BUCKET_NAME}/
  {ADMIN_ROOT_PREFIX}/
    collections/
      {collection_id}/
        meta.json
        raw/{filename}.pdf           (PDFs subidos; user metadata: pages,
                                       ingest-status, ingest-error)
        ocr/{filename_stem}/
          text.jsonl                 (texto trivial filtrado; text+title;
                                       una linea por bloque
                                       {page,type,text})
        chunks/{filename_stem}.parquet
                                     (chunks producidos por el admin;
                                       schema en admin/ingest/chunks_io.py
                                       — provisional hasta D4)
        kg/                          (exportado por el motor cuando llegue)
  datasets/evaluation/...    (motor — el admin no toca este prefijo)
```

`collection_id` = `col_{YYYYMMDDHHMMSS}_{shortuuid}`.

## Decisiones registradas

- **D1 — Bucket compartido con namespace.** Admin y motor comparten
  `lakehouse`; el admin escribe sólo bajo `ADMIN_ROOT_PREFIX/`. Si en algún
  momento conviene aislar, migrar a un bucket dedicado es un `mc cp -r` y un
  cambio de variable.
- **D2 — `custom_ground_truth` (pendiente).** El tipo de colección
  `custom_ground_truth` está fuera de Fase 0; añadir a `CollectionType` cuando
  esté decidido el flujo de upload de ground truth propio.
- **D3 — Colecciones ≠ datasets del motor.** Una **colección** es un
  contenedor de ficheros **subidos por el usuario desde la UI web del admin**
  (PDFs en Fase 1). Objetivo exclusivo: demo/simulación; no se usan ni se
  adaptan para benchmarking, de ahí que `CollectionType` sólo exponga
  `PLAYGROUND`. Los **datasets** que ya maneja el motor (p. ej. HotpotQA)
  son otra entidad completamente distinta — origen, estructura, ciclo de
  vida y prefijo en MinIO diferentes (`datasets/evaluation/...`, propiedad
  del motor). Si en algún momento la UI admin expone datasets del motor,
  será bajo una ruta y modelo propios (p. ej. `/datasets`), nunca
  mezclándolos con `/collections`.
- **D4 — Chunker en el admin + schema provisional (Fase 1.B.3).** La
  ingesta es responsabilidad exclusiva del admin: OCR con MinerU, filtro
  a `text`/`title`, y chunking. El motor solo lee/escribe. Outputs por
  fichero:
  - `ocr/{stem}/text.jsonl` — una línea por bloque
    `{"page": int, "type": "text"|"title", "text": str}`. Filtro: se
    descartan `image`, `table`, `equation`. Se conserva como artefacto
    intermedio para poder re-chunkear sin volver a llamar a MinerU.
  - `chunks/{stem}.parquet` — schema en `admin/ingest/chunks_io.py`:
    `chunk_id, collection_id, source_file, page_start, page_end,
    block_types, text, token_count`. Tokenizer: `tiktoken cl100k_base`
    con fallback word-level si no hay red. Target/overlap: 500/50.
    Title abre chunk nuevo; bloque gigante se parte con overlap.
  El schema es provisional: cuando el motor publique el contrato
  definitivo, se ajusta un único módulo (`chunks_io.py`) sin tocar el
  resto del pipeline.
- **D5 — Jobs de ingesta in-process (Fase 1.B).** Usamos `BackgroundTasks`
  de FastAPI. Trade-off aceptado: la respuesta HTTP se entrega de
  inmediato (303) pero el job bloquea un worker del servidor mientras
  dura. Para PDFs típicos + MinerU remoto (hasta ~15 min con
  `timeout=900`) es aceptable en Fase 1. Cuando haya concurrencia real o
  documentos grandes se migra a un worker externo (RQ / proceso propio).
- **D6 — OCR vía MinerU directo.** Endpoint HTTP de MinerU en
  `MINERU_URL` (default `http://172.30.79.104:8000/file_parse`).
  Preferido sobre el broker porque devuelve `content_list` (bloques
  tipados con página), lo que nos permitirá chunking estructural cuando
  llegue D4.

## Fases

- **Fase 0** (cerrada): CRUD mínimo de colecciones (`PLAYGROUND`), estado
  único `CREATED`, persistencia en MinIO, `/health`.
- **Fase 0.5** (aparcada): exponer los datasets que ya maneja el motor
  (p. ej. HotpotQA) en la UI admin como **entidad separada** (ruta y
  prefijo propios). Fuera del dominio de colecciones (ver D3).
- **Fase 1.A** (cerrada): upload de PDFs con drag-and-drop, MIME tag,
  nº de páginas, detalle compacto.
- **Fase 1.B** (cerrada): ingesta de PDFs vía MinerU directo (ver D6).
  - 1.B.1 (cerrada): estados + endpoint + UI badges + stub.
  - 1.B.2 (cerrada): adapter real de MinerU + `text.jsonl`.
  - 1.B.3 (cerrada): chunker + `chunks/{stem}.parquet` (schema
    provisional, ver D4).
  - 1.B.4 (aparcada): polish de orquestación (throttling si hace
    falta — `BackgroundTasks` aguanta hasta que aparezca concurrencia
    real).
  - 1.B.5 (cerrada): UI completa — panel con progress bar y animación
    `running` dinámica, badges, polling HTMX vía OOB swap mientras
    `running > 0`, Retry por fila, spinner en submits multipart,
    resumen de ingesta por fila en `/collections`.
- **Fase 2** (siguiente): Knowledge Graphs — depende de cerrar el
  contrato de chunks/KG con CH_LIRAG (ver "Integración con CH_LIRAG (Fase 2)" abajo).
- **Fase 3**: runs, playground.

## Integración con CH_LIRAG (Fase 2)

> Estado tras inspeccionar `BraisMarteloLopez/CH_LIRAG@main`:
> `shared/retrieval/lightrag/{knowledge_graph,triplet_extractor,retriever}.py`.
> El motor adapta HKUDS/LightRAG (EMNLP 2025) y NO chunkea: sólo
> consume chunks que escribe el admin. Dependencia unidireccional:
> admin importa motor.

### Contrato verificado (lo que el extractor del motor espera)

```python
# shared/retrieval/lightrag/triplet_extractor.py
extract_batch_async(documents: List[Dict[str, Any]],
                    batch_docs_per_call: int = 5)
# Cada document es: {"doc_id": str, "content": str}
```

- **Hard cap interno**: `max_text_chars = 3000` por chunk antes del
  prompt LLM. Equivale a ~700–1000 tokens según idioma. Chunks > este
  cap se truncan silenciosamente y el LLM pierde el final del chunk.
- **Provenance dual**: `KGEntity.source_doc_ids: Set[str]` (multi-chunk),
  `KGRelation.source_doc_id: str` (chunk único). Ambos guardan el
  `doc_id` que el admin emite.
- **Map natural** desde nuestro parquet: `doc_id ← chunk_id`,
  `content ← text`. Las demás columnas (`source_file`, `page_start`,
  `page_end`, `block_types`, `token_count`) son metadata que el motor
  no consume — quedan para la UI del admin (drill-down chunk → página).

### Lo que el admin **ya cumple**

- ✅ Chunker emite parquet bajo `admin/collections/{id}/chunks/`.
- ✅ Schema incluye `chunk_id` y `text` (los dos campos que el motor
  necesita).
- ✅ `chunk_id` es string opaco estable: `f"{stem}:{i:05d}"`. Sirve
  como `doc_id` sin transformación.
- ✅ Defaults `target=500 / overlap=50` caben con holgura en el cap
  de 3000 chars del extractor (~50% de margen). 500 está más cerca del
  óptimo de CH_LIRAG que el default upstream de LightRAG (1200).
- ✅ JSONL como cache crudo permite re-chunkear (con otro profile o
  con otro `target_tokens`) sin re-OCR.
- ✅ `IngestProfile` per-collection permite tunear filtros pre/post
  chunker desde la UI.

### Pendiente del admin (LI_AD) para Fase 2

| # | Item | Coste estimado | Bloqueado por |
|---|---|---|---|
| A | **Adapter parquet → `List[Dict]`**. Función `chunks_for_engine(client, *, bucket, prefix, collection_id) -> List[dict]` en `admin/chunks/service.py` que mapea `chunk_id`→`doc_id`, `text`→`content`. | ~10 LOC + tests | nada |
| B | **Trigger de build de KG**. POST `/collections/{id}/kg/build` (análogo a `/ingest`) que importa el extractor de CH_LIRAG, le pasa los chunks adaptados, y persiste el resultado. `BackgroundTasks` (D5). | ~80 LOC + tests | A |
| C | **Persistencia del KG**. Escribir nodes/edges en `admin/collections/{id}/kg/`. Schema TBD (ver "Pendiente del motor" abajo). | ~50 LOC | schema KG |
| D | **Reader del KG**. `admin/kg/service.py::read_kg(client, ...) -> (nodes, edges)`. Para que la UI lo dibuje. | ~30 LOC + tests | C |
| E | **Estado per-colección**. Campo `kg_status` en `meta.json`: `none / building / done / failed`. Se muestra como badge en `/collections` y como sección en Overview. | ~40 LOC | nada |
| F | **UI: pestaña Knowledge Graph**. Tabla de entities (nombre, tipo, count de chunks que la mencionan) + tabla de relations (source, target, type, chunk de origen). Drill-down: click en entity → chunks que la mencionan, vía nuestra columna `chunk_id`. | ~250 LOC + tests | D, schema KG |
| G | **Tokenizer alignment**. Hoy `tiktoken cl100k_base` (con fallback word-level). Confirmar con CH_LIRAG si el embedder espera otro; si difiere, exponer ENV var `CHUNK_TOKENIZER`. | ~20 LOC | confirmación motor |

### Pendiente del motor (CH_LIRAG)

1. **Confirmar schema del KG output**. Hoy `KGEntity` y `KGRelation`
   son dataclasses en memoria (igraph). Para que el admin persista,
   necesita schema parquet canónico — propuesta:
   ```
   nodes.parquet: entity_id, name, type, source_doc_ids (list<str>), description?
   edges.parquet: source, target, type, source_doc_id, weight?, description?
   ```
2. **Helper de invocación de alto nivel**. Hoy hay
   `extract_batch_async`. Para Fase 2 conviene un wrapper más opinado:
   `build_kg_from_chunks(chunks: List[Dict]) -> (List[KGEntity], List[KGRelation])`
   que el admin llame en una sola línea. (O documentar oficialmente que
   el admin orqueste batches con `extract_batch_async` directamente —
   cualquiera de las dos vale, hay que elegir.)
3. **Tokenizer canónico**. Confirmar si el embedder de CH_LIRAG espera
   `cl100k_base` o algo distinto. Si distinto, indicar cuál.
4. **¿`doc_id` necesita prefijo de colección?** Si CH_LIRAG mantiene
   un KG global multi-colección, el admin debería emitir
   `f"{collection_id}:{stem}:{i:05d}"` para evitar colisiones. Si cada
   colección tiene su KG aislado, el actual `f"{stem}:{i:05d}"` basta.
5. **Embeddings**: confirmar que el motor los calcula y persiste él
   (path propio, schema propio). El admin no debería tocar embeddings.

### Decisiones del admin (cerradas, revisar si motor pide otra cosa)

- **Path KG**: `{ADMIN_ROOT_PREFIX}/collections/{id}/kg/{nodes,edges}.parquet`.
- **`doc_id` granularidad**: chunk-level (`chunk_id`), no PDF-level
  (`source_file`). Permite a la UI surfacear el chunk concreto al
  mostrar evidencia.
- **Defaults tamaño chunk**: 500 tokens / overlap 50. Conservador
  respecto al cap de 3000 chars del motor; deja margen para que el
  extractor vea el chunk íntegro.
- **Provenance dual**: el admin no lo construye — viene del motor.
  El admin solo persiste y lee.

## Pendiente del motor (CH_LIRAG) para desbloquear Fase 2

> *(Sección legacy — la información actualizada y verificada vive en
> "Integración con CH_LIRAG (Fase 2)" arriba. Se conserva el bloque
> original durante una iteración para no romper referencias externas.)*

Hoy el admin escribe chunks bajo un schema provisional definido en
`admin/ingest/chunks_io.py` (D4). Para arrancar Fase 2 (KGs) el motor
tiene que publicar de su lado:

1. **Schema parquet de chunks** que va a leer. Si coincide con el
   provisional, ajuste cero. Si difiere, alineamos un único módulo
   (`chunks_io.py`) — no toca el chunker ni el runner.
2. **Helper de lectura** `read_chunks(s3, *, bucket, collection_id) -> list[Chunk]`
   que itere los parquets bajo `admin/collections/{id}/chunks/`.
3. **Path canónico y schema del KG exportado**. Propuesta del admin
   (cambia si el KG real del motor pide otra forma):
   `admin/collections/{id}/kg/nodes.parquet` + `edges.parquet`.
4. **Helper de escritura** `write_kg(s3, *, bucket, collection_id, kg) -> list[str]`
   y su `read_kg` complementario para que la UI del admin pueda
   mostrar nodos/aristas.
5. **Tokenizer canónico**: hoy el chunker usa `tiktoken cl100k_base`
   con fallback word-level si no hay red. Si el embedder del motor
   espera otro, lo cambiamos en `admin/ingest/chunker.py` (env-vareable
   ya está cómodo de añadir).

Embeddings: NO van en este contrato. Si el motor los necesita, los
calcula y persiste él (path propio, schema propio); el admin no los toca.

## Fuera de scope (producto completo)

- Autenticación.
