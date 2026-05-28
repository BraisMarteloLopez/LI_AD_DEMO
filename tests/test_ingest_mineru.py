"""Unit tests for the MinerU HTTP client.

We don't touch the network: `requests.post` is monkeypatched per-test with a
canned response object.
"""
from __future__ import annotations

import pytest

from admin.ingest import mineru as mineru_mod
from admin.ingest.mineru import MineruClient, MineruError


class _FakeResponse:
    def __init__(self, status: int, body: dict | None = None, text: str = "") -> None:
        self.status_code = status
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("no json body")
        return self._body


def _install(monkeypatch, fn):
    monkeypatch.setattr(mineru_mod.requests, "post", fn)


def test_parse_happy_path_returns_md_and_content_list(monkeypatch):
    seen = {}

    def fake_post(url, files=None, data=None, timeout=None):
        seen["url"] = url
        seen["data"] = data
        seen["files"] = files
        return _FakeResponse(200, {
            "results": {
                "doc.pdf": {
                    "md_content": "# hi\n\nbody",
                    "content_list": [
                        {"type": "text", "text": "body", "page_idx": 0},
                    ],
                }
            }
        })
    _install(monkeypatch, fake_post)

    client = MineruClient("http://mineru/parse", timeout_secs=5)
    result = client.parse(b"%PDF-1.4", "doc.pdf")

    assert result.markdown.startswith("# hi")
    assert result.content_list[0]["text"] == "body"
    assert seen["url"] == "http://mineru/parse"
    # Flags que pedimos al servicio: texto+estructura, sin imagenes ni modelos.
    flat = dict(seen["data"])
    assert flat["return_content_list"] == "true"
    assert flat["return_images"] == "false"
    assert flat["return_model_output"] == "false"


def test_parse_fuzzy_matches_file_key(monkeypatch):
    def fake_post(url, files=None, data=None, timeout=None):
        return _FakeResponse(200, {
            "results": {
                "uploaded_doc.pdf": {"md_content": "", "content_list": []},
            }
        })
    _install(monkeypatch, fake_post)

    client = MineruClient("http://x")
    result = client.parse(b"x", "doc.pdf")
    assert result.content_list == []


def test_parse_non_200_raises(monkeypatch):
    def fake_post(url, files=None, data=None, timeout=None):
        return _FakeResponse(500, text="boom")
    _install(monkeypatch, fake_post)

    with pytest.raises(MineruError, match="500"):
        MineruClient("http://x").parse(b"x", "doc.pdf")


def test_parse_missing_results_key_raises(monkeypatch):
    def fake_post(url, files=None, data=None, timeout=None):
        return _FakeResponse(200, {"oops": "no results"})
    _install(monkeypatch, fake_post)

    with pytest.raises(MineruError, match="no 'results'"):
        MineruClient("http://x").parse(b"x", "doc.pdf")


def test_parse_unknown_file_key_raises(monkeypatch):
    def fake_post(url, files=None, data=None, timeout=None):
        return _FakeResponse(200, {"results": {"other.pdf": {}}})
    _install(monkeypatch, fake_post)

    with pytest.raises(MineruError, match="did not return"):
        MineruClient("http://x").parse(b"x", "doc.pdf")


def test_parse_accepts_content_list_as_json_string(monkeypatch):
    # El endpoint /file_parse devuelve content_list como string JSON.
    # Tenemos que deserializarlo transparentemente.
    import json as _json
    payload = {
        "results": {
            "doc.pdf": {
                "md_content": "",
                "content_list": _json.dumps([
                    {"type": "text", "text": "hola", "page_idx": 0},
                    {"type": "title", "text": "H", "page_idx": 1},
                ]),
            }
        }
    }

    def fake_post(url, files=None, data=None, timeout=None):
        return _FakeResponse(200, payload)
    _install(monkeypatch, fake_post)

    result = MineruClient("http://x").parse(b"x", "doc.pdf")
    assert isinstance(result.content_list, list)
    assert result.content_list[0]["text"] == "hola"
    assert result.content_list[1]["type"] == "title"


def test_parse_rejects_content_list_as_unparseable_string(monkeypatch):
    def fake_post(url, files=None, data=None, timeout=None):
        return _FakeResponse(200, {
            "results": {"doc.pdf": {"content_list": "not json"}},
        })
    _install(monkeypatch, fake_post)

    with pytest.raises(MineruError, match="not valid JSON"):
        MineruClient("http://x").parse(b"x", "doc.pdf")


def test_parse_request_exception_raises_mineru_error(monkeypatch):
    import requests as _req

    def fake_post(*_a, **_kw):
        raise _req.exceptions.ConnectionError("nope")
    _install(monkeypatch, fake_post)

    with pytest.raises(MineruError, match="mineru request failed"):
        MineruClient("http://x").parse(b"x", "doc.pdf")
