"""Rejeições acontecem antes de qualquer acesso ao banco: TestClient sem lifespan."""
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
OK = {"stop_id": "SP-0412", "ts": "2026-08-31T18:42:00-03:00", "count": 12}


def post(body: dict | bytes):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return client.post("/ingest/readings", content=raw, headers={"content-type": "application/json"})


def test_extra_field_rejected():
    r = post({**OK, "image": "abc"})
    assert r.status_code == 422


def test_person_identifier_rejected():
    assert post({**OK, "person_id": 7}).status_code == 422


def test_body_over_300_bytes_rejected():
    r = post(json.dumps({**OK, "stop_id": "X" * 300}).encode())
    assert r.status_code == 413


def test_naive_timestamp_rejected():
    assert post({**OK, "ts": "2026-08-31T18:42:00"}).status_code == 422


def test_missing_field_rejected():
    assert post({"stop_id": "SP-0412", "count": 3}).status_code == 422


def test_negative_count_rejected():
    assert post({**OK, "count": -1}).status_code == 422
