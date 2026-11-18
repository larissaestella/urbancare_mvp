import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.address_extraction as extraction
from app.address_extraction import extract_address
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "address_docs"
GROUND_TRUTH = json.loads((FIXTURES / "ground_truth.json").read_text())
FIELDS = ("street", "number", "complement", "neighborhood", "city", "state", "postal_code")
client = TestClient(app)


def test_held_out_synthetic_documents_extract_the_installation_address():
    for filename, expected in GROUND_TRUTH.items():
        result = extract_address((FIXTURES / filename).read_bytes())
        assert result["issuer"] == expected["issuer"], filename
        assert result["address"] == expected["address"], filename
        assert result["perspective_corrected"], filename
        assert result["privacy"].startswith("Imagem processada em memória"), filename


@pytest.mark.parametrize(
    ("refined_text", "expected_confidence"),
    [
        ("Endereco: RUA DO SOL 82 CASA 2 CENTRO - 13010-110 - CAMPINAS / SP", 0.75),
        ("Endereco: RUA DO SOL 82 CASA 2 CENTRO - 13010-111 - CAMPINAS / SP", 0.5),
    ],
)
def test_vivo_precise_reread_requires_postal_city_and_state_agreement(
    monkeypatch, refined_text, expected_confidence
):
    image = np.full((1000, 1400, 3), 255, dtype=np.uint8)
    bounds = (1200, 900, 1380, 940)
    source_text = "Endereco: RUA DO SOL 82 CASA 2 CENTRO - 13010-110 - CAMPINAS / SP"
    records = [
        ("VIVO TELEFONICA", (10, 10, 250, 40), 0.5),
        (source_text, bounds, 0.5),
    ]
    monkeypatch.setattr(
        extraction, "_ocr_data",
        lambda *args, **kwargs: (records, 0.5, {bounds: [0.5]}),
    )
    monkeypatch.setattr(
        extraction, "_customer_region",
        lambda *_: (image, source_text, bounds),
    )
    monkeypatch.setattr(extraction, "_read_ocr", lambda *_args, **_kwargs: ([source_text], 0.5))
    monkeypatch.setattr(
        extraction, "read_subscriber_line", lambda *_: (refined_text, 0.75)
    )

    issuer, confidence, address = extraction._extract_anchored(image)

    assert issuer == "VIVO"
    assert confidence == expected_confidence
    assert address is not None
    assert address.postal_code == "13010-110"


def test_enel_inline_bairro_is_not_misclassified_as_complement():
    address = extraction._parse_address(
        ["RUA DO TESTE AZUL, 1030, BAIRRO CENTRO CEP: 11111-222 - CIDADE TESTE/CE"],
        "ENEL",
    )

    assert address is not None
    assert address.street == "RUA DO TESTE AZUL"
    assert address.number == "1030"
    assert address.complement == ""
    assert address.neighborhood == "CENTRO"
    assert address.city == "CIDADE TESTE"
    assert address.state == "CE"
    assert address.postal_code == "11111-222"


def test_vivo_inline_address_separates_lot_from_neighborhood_and_ignores_footer():
    address = extraction._parse_address(
        [
            "Endereco: R CORALINA DE TESTE 2215 LT 14 RESIDENCIAL PARQUE LESTE "
            "21/03/2023 - 33333-444 - CIDADE TESTE / SP",
            "RAW NIVO.COM.BR",
        ],
        "VIVO",
    )

    assert address is not None
    assert address.street == "R CORALINA DE TESTE"
    assert address.number == "2215"
    assert address.complement == "LT 14"
    assert address.neighborhood == "RESIDENCIAL PARQUE LESTE"
    assert address.city == "CIDADE TESTE"
    assert address.state == "SP"
    assert address.postal_code == "33333-444"


def test_claro_customer_block_extracts_inline_number_and_neighborhood():
    address = extraction._parse_address(
        [
            "NOME DO CLIENTE - ENDERECO DA EMPRESA 000 SL 0 E 0",
            "JARDIM EXEMPLO",
            "00000-000 SAO PAULO SP",
        ],
        "CLARO",
    )

    assert address is not None
    assert address.street == ""
    assert address.number == "000"
    assert address.complement == "SL 0 E 0"
    assert address.neighborhood == "JARDIM EXEMPLO"
    assert address.city == "SAO PAULO"
    assert address.state == "SP"
    assert address.postal_code == "00000-000"


def test_layout_specific_crop_fills_missing_fields_without_overwriting_road():
    current = extraction.Address("RUA DE TESTE", "12", "APTO 4", "", "", "", "")
    focused = extraction.Address("", "", "", "CENTRO", "CIDADE TESTE", "SP", "11111-222")

    merged = extraction._merge_addresses(focused, current)

    assert merged == extraction.Address(
        "RUA DE TESTE", "12", "APTO 4", "CENTRO", "CIDADE TESTE", "SP", "11111-222"
    )


@pytest.mark.parametrize("issuer", ["ENEL", "CLARO", "VIVO"])
def test_customer_region_anchors_to_customer_and_excludes_supplier(issuer):
    image = np.full((1000, 1400), 255, dtype=np.uint8)
    lines = [
        ("RUA DO FORNECEDOR 999", (20, 20, 500, 40), 0.9),
        ("99999-999 OUTRA CIDADE SP", (20, 45, 500, 65), 0.9),
    ]
    if issuer == "ENEL":
        lines += [
            ("RUA DAS FLORES, 120, BAIRRO CENTRO", (160, 220, 900, 240), 0.9),
            ("CEP: 12345-678 - CIDADE TESTE/SP", (160, 245, 850, 265), 0.9),
            ("CPF/CNPJ: 000.000.000-00", (160, 270, 700, 290), 0.9),
        ]
    elif issuer == "CLARO":
        lines += [
            ("NOME DO CLIENTE -", (160, 195, 600, 215), 0.9),
            ("RUA DAS FLORES 120", (160, 220, 800, 240), 0.9),
            ("CENTRO", (160, 245, 350, 265), 0.9),
            ("12345-678 CIDADE TESTE SP", (160, 270, 850, 290), 0.9),
        ]
    else:
        lines += [
            ("CADASTRO DO ASSINANTE", (160, 180, 600, 200), 0.9),
            ("ENDERECO: RUA DAS FLORES 120 CENTRO - 12345-678 - CIDADE TESTE / SP",
             (160, 220, 1300, 240), 0.9),
            ("CODIGO DO CLIENTE: 000", (160, 245, 600, 265), 0.9),
        ]

    shifted = [
        (text, tuple(value + 75 for value in bounds), confidence)
        for text, bounds, confidence in lines
    ]
    region, text, _ = extraction._customer_region(image, shifted, issuer)

    assert region.size > 0
    assert "FORNECEDOR" not in text
    address = extraction._parse_address(text.splitlines(), issuer)
    assert address is not None
    assert (address.street, address.number, address.neighborhood) == (
        "RUA DAS FLORES", "120", "CENTRO"
    )
    assert (address.city, address.state, address.postal_code) == (
        "CIDADE TESTE", "SP", "12345-678"
    )


def test_public_extract_endpoint_returns_structured_address_without_storing_file():
    filename = next(iter(GROUND_TRUTH))
    response = client.post(
        "/address/extract",
        content=(FIXTURES / filename).read_bytes(),
        headers={"content-type": "image/jpeg"},
    )
    assert response.status_code == 200
    result = response.json()
    assert set(result["address"]) == set(FIELDS)
    assert result["address"] == GROUND_TRUTH[filename]["address"]
    assert "image" not in result and "path" not in result


def test_extract_endpoint_rejects_non_image_media_types():
    response = client.post("/address/extract", content=b"not an image", headers={"content-type": "text/plain"})
    assert response.status_code == 415


def test_extract_endpoint_rejects_malformed_image_bytes():
    response = client.post("/address/extract", content=b"not an image", headers={"content-type": "image/jpeg"})
    assert response.status_code == 422


def test_extract_endpoint_rejects_oversized_upload():
    response = client.post(
        "/address/extract",
        content=b"x" * (10 * 1024 * 1024 + 1),
        headers={"content-type": "image/jpeg"},
    )
    assert response.status_code == 413
