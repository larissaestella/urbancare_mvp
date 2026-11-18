"""Gera comprovantes sintéticos para testes; nenhum documento ou dado pessoal real é usado."""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "address_docs"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

DOCUMENTS = [
    {
        "id": "enel-modelo-a",
        "issuer": "ENEL",
        "address": {"street": "RUA DAS ACACIAS", "number": "145", "complement": "APTO 23",
                    "neighborhood": "VILA MARIANA", "city": "SAO PAULO", "state": "SP", "postal_code": "04101-000"},
        "lines": ["ENEL DISTRIBUICAO SAO PAULO", "CONTA DE ENERGIA ELETRICA", "UNIDADE CONSUMIDORA 000123456",
                  "ENDERECO DE INSTALACAO", "RUA DAS ACACIAS, 145 - APTO 23", "VILA MARIANA",
                  "SAO PAULO - SP", "CEP: 04101-000", "ENDERECO DE COBRANCA", "AVENIDA PAULISTA, 1000",
                  "BELA VISTA", "SAO PAULO - SP", "CEP: 01310-100", "VENCIMENTO 10/11/2026"],
    },
    {
        "id": "enel-modelo-b",
        "issuer": "ENEL",
        "address": {"street": "RUA DO IPE", "number": "78", "complement": "", "neighborhood": "ACLIMACAO",
                    "city": "SAO PAULO", "state": "SP", "postal_code": "01531-020"},
        "lines": ["ENEL", "DEMONSTRATIVO DE CONSUMO", "ENDERECO DA UNIDADE CONSUMIDORA",
                  "RUA DO IPE, 78", "ACLIMACAO", "SAO PAULO - SP", "CEP 01531-020",
                  "ENDERECO DE FATURAMENTO", "RUA DA CONSOLACAO, 200", "CONSOLACAO", "SAO PAULO - SP",
                  "CEP 01302-000", "VALOR TOTAL R$ 82,90"],
    },
    {
        "id": "vivo-modelo-a",
        "issuer": "VIVO",
        "address": {"street": "RUA DO SOL", "number": "82", "complement": "CASA 2",
                    "neighborhood": "CENTRO", "city": "CAMPINAS", "state": "SP", "postal_code": "13010-110"},
        "lines": ["VIVO TELEFONICA BRASIL", "FATURA DE SERVICOS", "CLIENTE 009876543",
                  "ENDERECO DE INSTALACAO", "RUA DO SOL, 82 - CASA 2", "CENTRO",
                  "CAMPINAS - SP", "CEP: 13010-110", "ENDERECO DE COBRANCA", "AVENIDA BRASIL, 900",
                  "JARDIM AMERICA", "CAMPINAS - SP", "CEP: 13073-012", "TOTAL DA FATURA R$ 119,90"],
    },
    {
        "id": "vivo-modelo-b",
        "issuer": "VIVO",
        "address": {"street": "AVENIDA IPIRANGA", "number": "410", "complement": "", "neighborhood": "CENTRO",
                    "city": "SANTOS", "state": "SP", "postal_code": "11010-071"},
        "lines": ["VIVO", "DETALHES DA SUA CONTA", "ENDERECO DO SERVICO",
                  "AVENIDA IPIRANGA, 410", "CENTRO", "SANTOS - SP", "CEP 11010-071",
                  "ENDERECO PARA PAGAMENTO", "RUA XV DE NOVEMBRO, 10", "CENTRO", "SANTOS - SP",
                  "CEP 11010-150", "VENCIMENTO 15/11/2026"],
    },
    {
        "id": "claro-modelo-a",
        "issuer": "CLARO",
        "address": {"street": "AVENIDA BRASIL", "number": "550", "complement": "CASA 2",
                    "neighborhood": "COPACABANA", "city": "RIO DE JANEIRO", "state": "RJ", "postal_code": "22040-001"},
        "lines": ["CLARO S A", "FATURA DE SERVICOS DE TELECOMUNICACOES", "CODIGO DO CLIENTE 00554433",
                  "ENDERECO DE COBRANCA", "RUA DA PRAIA, 20", "CENTRO", "RIO DE JANEIRO - RJ",
                  "CEP 20010-000", "ENDERECO DE INSTALACAO", "AVENIDA BRASIL, 550 - CASA 2",
                  "COPACABANA", "RIO DE JANEIRO - RJ", "CEP: 22040-001", "VALOR TOTAL R$ 99,90"],
    },
    {
        "id": "claro-modelo-b",
        "issuer": "CLARO",
        "address": {"street": "RUA DA LAGOA", "number": "31", "complement": "", "neighborhood": "TIJUCA",
                    "city": "RIO DE JANEIRO", "state": "RJ", "postal_code": "20520-110"},
        "lines": ["CLARO", "RESUMO DA FATURA", "ENDERECO DO CLIENTE",
                  "RUA DA PRAIA, 20", "CENTRO", "RIO DE JANEIRO - RJ", "CEP 20010-000",
                  "ENDERECO DO PONTO DE ACESSO", "RUA DA LAGOA, 31", "TIJUCA", "RIO DE JANEIRO - RJ",
                  "CEP 20520-110", "VALOR TOTAL R$ 79,90"],
    },
]


def _document(spec: dict) -> np.ndarray:
    image = Image.new("RGB", (1000, 1300), "white")
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(FONT_PATH, 44)
    body = ImageFont.truetype(FONT_PATH, 31)
    draw.rectangle((30, 30, 970, 1270), outline="#333333", width=4)
    y = 70
    for index, line in enumerate(spec["lines"]):
        font = title if index == 0 else body
        if line.startswith("ENDERECO"):
            draw.rectangle((60, y - 5, 940, y + 42), fill="#e8e8e8")
        draw.text((70, y), line, fill="#111111", font=font)
        y += 84 if index == 0 else 76
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _photo(document: np.ndarray, index: int) -> np.ndarray:
    height, width = document.shape[:2]
    canvas_w, canvas_h = 1200, 1500
    backgrounds = (205, 215, 200)
    canvas = np.full((canvas_h, canvas_w, 3), backgrounds[index % len(backgrounds)], dtype=np.uint8)
    margin = 65 + index * 6
    corners = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    target = np.float32([[margin + 10, margin], [canvas_w - margin, margin + 18],
                         [canvas_w - margin - 5, canvas_h - margin], [margin, canvas_h - margin - 16]])
    transform = cv2.getPerspectiveTransform(corners, target)
    warped = cv2.warpPerspective(document, transform, (canvas_w, canvas_h))
    mask = cv2.warpPerspective(np.full((height, width), 255, dtype=np.uint8), transform, (canvas_w, canvas_h))
    canvas[mask > 0] = warped[mask > 0]
    return canvas


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for index, spec in enumerate(DOCUMENTS):
        path = ROOT / f"{spec['id']}.jpg"
        image = _photo(_document(spec), index)
        if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
            raise RuntimeError(f"Could not generate {path}")
        manifest[path.name] = {"issuer": spec["issuer"], "address": spec["address"],
                               "split": "held-out synthetic test"}
    (ROOT / "ground_truth.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Generated {len(manifest)} synthetic document photos in {ROOT}")


if __name__ == "__main__":
    main()
