"""Cadastro cidadão: validação antes do banco e ligação do endereço confirmado aos pontos da mesma via."""
from fastapi.testclient import TestClient

from app.citizen import nearby_stops, street_key
from app.main import app

client = TestClient(app)
URL = "/citizens/3f2a9c1e-77aa-4d0b-9c1e-0a1b2c3d4e5f/addresses"
ADDRESS = {
    "consent": True, "issuer": "ENEL",
    "street": "Avenida Paulista", "number": "1500", "complement": "", "neighborhood": "Bela Vista",
    "city": "São Paulo", "state": "SP", "postal_code": "01310-100",
}
STOPS = [
    {"id": "SP-1", "name": "Av. Paulista, 1578"},
    {"id": "SP-2", "name": "R. Augusta, 1500"},
    {"id": "SP-3", "name": "Av. Paulista, 900"},
    {"id": "SP-4", "name": "Avenida Paulista, 1490"},
]


def test_address_requires_explicit_consent():
    assert client.post(URL, json={**ADDRESS, "consent": False}).status_code == 422


def test_address_rejects_invalid_state_postal_code_and_extra_fields():
    assert client.post(URL, json={**ADDRESS, "state": "XX"}).status_code == 422
    assert client.post(URL, json={**ADDRESS, "postal_code": "0131-100"}).status_code == 422
    assert client.post(URL, json={**ADDRESS, "cpf": "000"}).status_code == 422


def test_address_routes_reject_malformed_visitor():
    assert client.get("/citizens/x/addresses").status_code == 422
    assert client.delete("/citizens/x/addresses/1").status_code == 422
    assert client.post("/citizens/x%20y/addresses", json=ADDRESS).status_code == 422


def test_street_key_ignores_street_type_abbreviation_and_accents():
    assert street_key("Avenida Paulista") == street_key("AV. PAULISTA") == "PAULISTA"
    assert street_key("Rua da Consolação") == street_key("R. da Consolacao")


def test_nearby_stops_match_same_street_ordered_by_number():
    assert [s["id"] for s in nearby_stops("AVENIDA PAULISTA", "1500", STOPS)] == ["SP-4", "SP-1", "SP-3"]
    assert nearby_stops("Rua Inexistente", "10", STOPS) == []
