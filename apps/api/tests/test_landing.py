"""Validação da landing antes de qualquer acesso ao banco: TestClient sem lifespan."""
from fastapi.testclient import TestClient

from app.landing import metrics
from app.main import app

client = TestClient(app)
VISITOR = "3f2a9c1e-77aa-4d0b-9c1e-0a1b2c3d4e5f"
LEAD = {"visitor": VISITOR, "variant": "A", "company": "Via Sul", "size": 40, "email": "cco@viasul.com.br"}


def test_lead_extra_field_rejected():
    assert client.post("/leads", json={**LEAD, "phone": "11999999999"}).status_code == 422


def test_lead_free_email_rejected():
    assert client.post("/leads", json={**LEAD, "email": "fulano@gmail.com"}).status_code == 422


def test_lead_malformed_email_rejected():
    assert client.post("/leads", json={**LEAD, "email": "cco@viasul"}).status_code == 422


def test_lead_size_must_be_positive():
    assert client.post("/leads", json={**LEAD, "size": 0}).status_code == 422


def test_lead_unknown_variant_rejected():
    assert client.post("/leads", json={**LEAD, "variant": "C"}).status_code == 422


def test_event_unknown_kind_rejected():
    assert client.post("/landing/events", json={"visitor": VISITOR, "variant": "B", "kind": "lead"}).status_code == 422


def test_metrics_ctr_per_variant_and_no_division_by_zero():
    m = metrics([{"variant": "A", "visits": 10, "clicks": 2, "leads": 1}])
    assert m["A"]["ctr"] == 0.2 and m["B"]["ctr"] is None
    assert m["total"] == {"visits": 10, "clicks": 2, "leads": 1, "ctr": 0.2}
