"""Reproduces the PDF report and metrics from the synthetic held-out documents."""

import json
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.address_extraction import extract_address

FIXTURES = ROOT / "tests" / "fixtures" / "address_docs"
OUTPUT = ROOT.parents[1] / "docs" / "extração-automática-de-endereços.pdf"
FIELDS = ("street", "number", "complement", "neighborhood", "city", "state", "postal_code")
FIELD_NAMES = {
    "street": "Logradouro",
    "number": "Número",
    "complement": "Complemento",
    "neighborhood": "Bairro",
    "city": "Cidade",
    "state": "UF",
    "postal_code": "CEP",
}


def _metrics() -> tuple[dict, list[dict]]:
    truth = json.loads((FIXTURES / "ground_truth.json").read_text())
    counts = {field: [0, 0] for field in FIELDS}
    issuer_correct = 0
    by_issuer = {}
    for filename, expected in truth.items():
        result = extract_address((FIXTURES / filename).read_bytes())
        issuer_correct += result["issuer"] == expected["issuer"]
        row = by_issuer.setdefault(expected["issuer"], {"documents": 0, "correct_fields": 0, "total_fields": 0})
        row["documents"] += 1
        for field in FIELDS:
            ok = result["address"][field] == expected["address"][field]
            counts[field][0] += int(ok)
            counts[field][1] += 1
            row["correct_fields"] += int(ok)
            row["total_fields"] += 1
    total_correct = sum(correct for correct, _ in counts.values())
    total = sum(total for _, total in counts.values())
    return {
        "documents": len(truth),
        "issuer_accuracy": issuer_correct / len(truth),
        "field_accuracy": total_correct / total,
        "fields": counts,
        "by_issuer": by_issuer,
    }, list(truth)


def _page(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#c9c7c0"))
    canvas.line(18 * mm, 15 * mm, 192 * mm, 15 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#55585e"))
    canvas.drawString(18 * mm, 10 * mm, "UrbanFlow · Extração automática de endereços · Dados de teste sintéticos")
    canvas.drawRightString(192 * mm, 10 * mm, f"{document.page}")
    canvas.restoreState()


def main() -> None:
    metrics, _ = _metrics()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Cover", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=24, leading=29, textColor=colors.HexColor("#16181b"), alignment=TA_CENTER,
                              spaceAfter=12))
    styles.add(ParagraphStyle(name="Sub", parent=styles["Normal"], fontSize=11, leading=16, alignment=TA_CENTER,
                              textColor=colors.HexColor("#55585e"), spaceAfter=20))
    styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontSize=14, leading=18,
                              textColor=colors.HexColor("#16181b"), spaceBefore=8, spaceAfter=7))
    styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontSize=9.5, leading=14, spaceAfter=7))
    styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontSize=8, leading=11))
    story = [
        Spacer(1, 21 * mm),
        Paragraph("Extração Automática<br/>de Endereços", styles["Cover"]),
        Paragraph("Applied Computer Vision · MVP CitizenTech<br/>Enel · Vivo · Claro · " + date.today().strftime("%d/%m/%Y"),
                  styles["Sub"]),
        Paragraph("Resumo executivo", styles["H2x"]),
        Paragraph(
            "Pipeline de visão computacional para ler fotografias de comprovantes, identificar o emissor, "
            "corrigir a perspectiva, aplicar OCR e devolver o endereço de instalação em campos editáveis. "
            "O cidadão revisa e confirma antes de usar os dados no fluxo de cadastro.",
            styles["Bodyx"],
        ),
        Paragraph("Pipeline", styles["H2x"]),
        Paragraph(
            "1. Recebe JPEG, PNG ou WEBP via POST, limitado a 10 MB e 24 megapixels. "
            "2. Decodifica em memória, procura o maior contorno quadrilateral e corrige a perspectiva quando encontrado. "
            "3. Corrige inclinação por linhas detectadas e tenta OCR convencional com CLAHE. "
            "4. Se necessário, amplia a região superior de cadastro e aplica threshold adaptativo com segmentações "
            "alternativas. "
            "5. Envia PNG pela entrada padrão do Tesseract (português + inglês); nenhum arquivo temporário é criado. "
            "6. Identifica Enel, Vivo ou Claro e busca rótulos de instalação/serviço, evitando seções de cobrança. "
            "7. Valida e estrutura logradouro, número, complemento, bairro, cidade, UF e CEP para revisão humana.",
            styles["Bodyx"],
        ),
        Paragraph("Resultados em imagens inéditas sintéticas", styles["H2x"]),
        Paragraph(
            f"{metrics['documents']} fotos de teste (duas por empresa, perspectivas diferentes), separadas do código de "
            "extração; todos os dados foram inventados. A métrica é correspondência exata com o gabarito, incluindo "
            f"campos opcionais vazios. Identificação do emissor: {metrics['issuer_accuracy']:.0%}. "
            f"Acerto agregado por campo: {metrics['field_accuracy']:.0%} "
            f"({sum(x[0] for x in metrics['fields'].values())}/{sum(x[1] for x in metrics['fields'].values())}). "
            "Esse resultado mede somente o conjunto sintético; não representa acurácia em contas reais.",
            styles["Bodyx"],
        ),
    ]

    field_rows = [["Campo", "Acertos", "Total", "Acurácia"]]
    for field in FIELDS:
        correct, total = metrics["fields"][field]
        field_rows.append([FIELD_NAMES[field], str(correct), str(total), f"{correct / total:.0%}"])
    table = Table(field_rows, colWidths=[72 * mm, 25 * mm, 25 * mm, 35 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16181b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f2f1ec")),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#c9c7c0")),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.extend([
        table,
        Spacer(1, 6 * mm),
        Paragraph("Desempenho por emissor", styles["H2x"]),
    ])
    company_rows = [["Empresa", "Fotos", "Campos corretos"]]
    for issuer, result in metrics["by_issuer"].items():
        company_rows.append([issuer, str(result["documents"]),
                             f"{result['correct_fields']}/{result['total_fields']} "
                             f"({result['correct_fields'] / result['total_fields']:.0%})"])
    company_table = Table(company_rows, colWidths=[72 * mm, 25 * mm, 60 * mm], repeatRows=1)
    company_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16181b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#c9c7c0")),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.extend([
        company_table,
        PageBreak(),
        Paragraph("Integração ao MVP", styles["H2x"]),
        Paragraph(
            "Endpoint: POST /api/address/extract, com a imagem bruta no corpo e Content-Type image/jpeg, image/png "
            "ou image/webp. Resposta: emissor, endereço estruturado, confiança OCR e indicador de correção de "
            "perspectiva. Erros de formato/tamanho retornam 415/413; emissor não reconhecido ou endereço incompleto "
            "retornam 422. Tela: /cadastro-endereco. O formulário recebe os campos, permite edição e só os confirma "
            "após ação explícita do cidadão; a confirmação fica no estado da tela, sem gravação no servidor ou "
            "armazenamento local. Sirva a aplicação por HTTPS em implantação pública.",
            styles["Bodyx"],
        ),
        Paragraph("Privacidade, proteção de dados e LGPD", styles["H2x"]),
        Paragraph(
            "A fotografia e o OCR transitam apenas em memória durante a requisição. O Tesseract recebe PNG pela "
            "entrada padrão, sem criar arquivo temporário; a API não registra o corpo nem persiste a imagem. "
            "A resposta contém somente campos extraídos, e a tela os mantém em memória até ser fechada. Isso é uma "
            "medida técnica de minimização, não uma certificação jurídica de conformidade LGPD: publicação real deve "
            "adotar HTTPS, controle de acesso/abuso, política de retenção para os dados confirmados, aviso de "
            "privacidade, base legal e processo de atendimento aos direitos do titular.",
            styles["Bodyx"],
        ),
        Paragraph("Limitações e erros esperados", styles["H2x"]),
        Paragraph(
            "O OCR pode falhar em fotos desfocadas, reflexos, sombras fortes, baixa resolução, documentos cortados, "
            "fontes incomuns, rótulos alterados ou CEP/número pouco legíveis. A correção de perspectiva depende de "
            "detectar um quadrilátero; sem contorno suficiente, a foto segue sem correção e o indicador informa isso. "
            "Layouts fora dos três emissores suportados não são aceitos. A confiança reportada é uma média do "
            "Tesseract e não equivale à probabilidade de o endereço estar correto. A revisão humana é obrigatória.",
            styles["Bodyx"],
        ),
        Paragraph("Reprodução e testes", styles["H2x"]),
        Paragraph(
            "Requisitos: Python 3.12, Tesseract OCR com idiomas por e eng. Em apps/api, instale "
            "<font name='Courier'>pip install -r requirements.txt</font>; em Debian/Ubuntu instale "
            "<font name='Courier'>tesseract-ocr tesseract-ocr-por</font>. Gere os comprovantes com "
            "<font name='Courier'>python scripts/generate_address_fixtures.py</font>, rode "
            "<font name='Courier'>pytest -q</font> e gere este PDF com "
            "<font name='Courier'>python scripts/build_address_report.py</font>. "
            "Fixtures e gabarito: tests/fixtures/address_docs/.",
            styles["Bodyx"],
        ),
        Paragraph("Técnicas e métricas avaliadas", styles["H2x"]),
        Paragraph(
            "OpenCV: contorno quadrilateral, transformação de perspectiva, deskew por Hough, escala de cinza, "
            "ampliação, CLAHE e threshold adaptativo. Tesseract: OCR por linhas em português e inglês, com "
            "segmentações alternativas na região de cadastro. Extração: regras de layout/rótulo, prioridade para "
            "endereço de instalação/serviço e regex de CEP/UF/número. Métricas: identificação de empresa e acurácia "
            "exata por campo no conjunto sintético. Não há treinamento de modelo; as regras são reproduzíveis e "
            "inspecionáveis.",
            styles["Bodyx"],
        ),
        Spacer(1, 5 * mm),
        Paragraph("Dados sintéticos para demonstração; não representam contas, clientes ou resultados de campo.",
                  styles["Smallx"]),
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                            topMargin=17 * mm, bottomMargin=21 * mm, title="Extração Automática de Endereços")
    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    print(f"Generated {OUTPUT}")
    print(f"Issuer accuracy {metrics['issuer_accuracy']:.0%}; exact field accuracy {metrics['field_accuracy']:.0%}")


if __name__ == "__main__":
    main()
