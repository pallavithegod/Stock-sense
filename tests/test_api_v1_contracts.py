from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.integration


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "api_v1_frontend_contracts.json"


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _assert_utc_iso(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _assert_success_envelope(payload: dict[str, Any], fixture: dict[str, Any]) -> None:
    assert payload["success"] is True
    assert set(fixture["success_envelope_required"]).issubset(payload)
    assert set(fixture["meta_required"]).issubset(payload["meta"])
    assert payload["meta"]["version"] == "v1"
    _assert_utc_iso(payload["meta"]["timestamp"])
    provenance = payload["meta"]["provenance"]
    assert set(fixture["provenance_required"]).issubset(provenance)
    _assert_utc_iso(provenance["fetched_at"])
    assert isinstance(provenance["stale"], bool)
    assert isinstance(provenance["synthetic"], bool)
    assert isinstance(provenance["demo"], bool)


def _assert_error_envelope(payload: dict[str, Any], fixture: dict[str, Any]) -> None:
    assert payload["success"] is False
    assert set(fixture["error_envelope_required"]).issubset(payload)
    assert payload["meta"]["version"] == "v1"
    _assert_utc_iso(payload["meta"]["timestamp"])
    _assert_utc_iso(payload["meta"]["provenance"]["fetched_at"])


def test_v1_frontend_contracts_match_stored_representative_shapes(client):
    fixture = _fixture()

    for endpoint, expected in fixture["frontend_endpoints"].items():
        response = client.get(endpoint)

        assert response.status_code == 200, endpoint
        payload = response.get_json()
        _assert_success_envelope(payload, fixture)
        assert set(expected["data_required"]).issubset(payload["data"]), endpoint
        assert payload["meta"]["compatibility_alias"] == expected["compatibility_alias"]


def test_v1_stocks_contract_uses_consistent_pagination(client):
    fixture = _fixture()
    response = client.get("/api/v1/stocks", query_string={"limit": 2, "offset": 1})

    assert response.status_code == 200
    payload = response.get_json()
    _assert_success_envelope(payload, fixture)
    assert len(payload["data"]["stocks"]) == 2
    assert payload["meta"]["pagination"] == {"limit": 2, "offset": 1, "total": 4, "next_offset": 3}


def test_v1_errors_use_the_canonical_error_envelope(client):
    fixture = _fixture()

    not_found = client.get("/api/v1/stocks/NOPE")
    bad_query = client.get("/api/v1/stocks", query_string={"limit": "bad"})

    assert not_found.status_code == 404
    assert bad_query.status_code == 400
    _assert_error_envelope(not_found.get_json(), fixture)
    _assert_error_envelope(bad_query.get_json(), fixture)
    assert not_found.get_json()["code"] == "STOCK_NOT_FOUND"
    assert bad_query.get_json()["code"] == "VALIDATION_ERROR"


def test_v1_schema_endpoint_exposes_executable_contract_models(client):
    fixture = _fixture()
    response = client.get("/api/v1/schema")

    assert response.status_code == 200
    payload = response.get_json()
    _assert_success_envelope(payload, fixture)
    assert "ApiSuccessEnvelope" in payload["data"]["envelopes"]
    assert "ApiErrorEnvelope" in payload["data"]["envelopes"]
    assert "StockDTO" in payload["data"]["dto_schemas"]
    assert "SystemDTO" in payload["data"]["dto_schemas"]


def test_legacy_aliases_are_not_registered(client):
    assert client.get("/api/stocks").status_code == 404
    assert client.get("/api/stock/INFY").status_code == 404
    assert client.get("/api/predictions").status_code == 404
