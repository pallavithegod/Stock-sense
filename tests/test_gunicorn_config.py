from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

CONFIG_PATH = Path(__file__).resolve().parents[1] / "gunicorn.conf.py"


@pytest.fixture(scope="module")
def gunicorn_conf():
    spec = importlib.util.spec_from_file_location("stocksense_gunicorn_conf", CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({}, "0.0.0.0:5000"),
        ({"FLASK_PORT": "8080"}, "0.0.0.0:8080"),
        ({"PORT": "10000"}, "0.0.0.0:10000"),
        # Render's PORT wins over a FLASK_PORT baked into an image.
        ({"PORT": "10000", "FLASK_PORT": "5000"}, "0.0.0.0:10000"),
        ({"PORT": "", "FLASK_PORT": "5001"}, "0.0.0.0:5001"),
        ({"PORT": "10000", "FLASK_HOST": "127.0.0.1"}, "127.0.0.1:10000"),
        ({"PORT": " 10000 ", "FLASK_HOST": " "}, "0.0.0.0:10000"),
    ],
)
def test_bind_prefers_platform_port(gunicorn_conf, environ, expected):
    assert gunicorn_conf.resolve_bind(environ) == expected


@pytest.mark.parametrize("port", ["abc", "0", "65536", "-1", "80.5"])
def test_bind_rejects_invalid_port(gunicorn_conf, port):
    with pytest.raises(ValueError, match="PORT"):
        gunicorn_conf.resolve_bind({"PORT": port})


def test_module_level_bind_uses_process_environment(monkeypatch):
    monkeypatch.setenv("PORT", "12345")
    monkeypatch.delenv("FLASK_HOST", raising=False)
    spec = importlib.util.spec_from_file_location("stocksense_gunicorn_conf_env", CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.bind == "0.0.0.0:12345"
