# LI_AD

Admin del sistema RAG **CH_LIRAG**. Gestiona colecciones de PDFs (CRUD +
upload por drag-and-drop) y orquesta su ingesta: OCR vía MinerU, filtrado
a texto trivial, chunking y persistencia en MinIO. No ejecuta retrieval ni
generación: de eso se encarga el motor [CH_LIRAG](https://github.com/BraisMarteloLopez/CH_LIRAG).

Ver `CLAUDE.md` para arquitectura, decisiones registradas y roadmap por fases.

## Requisitos

- Python 3.10+
- Un MinIO accesible con el bucket ya creado (`lakehouse` por defecto).
- Para la ingesta: una instancia de MinerU accesible por HTTP
  (`MINERU_URL`, default `http://172.30.79.104:8000/file_parse`).

## Arrancar el servidor

```bash
cd /ruta/a/LI_AD
cp .env.example .env              # ajustar MINIO_* y MINERU_URL si procede
pip install -r requirements.txt
uvicorn admin.app:app --host 0.0.0.0 --port 8080
```

En desarrollo, con auto-reload:

```bash
uvicorn admin.app:app --reload --port 8080
```

UI en `http://localhost:8080/collections`. Salud en `http://localhost:8080/health`.

## Tests

```bash
cd /ruta/a/LI_AD
python -m pytest -q
```

No requieren MinIO ni MinerU reales: las fixtures usan mocks del cliente S3
y los tests del adapter monkeypatchean `requests.post`.
