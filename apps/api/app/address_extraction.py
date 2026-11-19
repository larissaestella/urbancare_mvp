import io
import os
import re
import tempfile
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

import cv2
import numpy as np
import pytesseract
from PIL import Image, UnidentifiedImageError

from .refinement import read_postal_code, read_subscriber_line

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
pytesseract.pytesseract.tesseract_cmd = os.environ.get("TESSERACT_CMD", "tesseract")
if os.path.isdir("/dev/shm"):
    os.environ["TMPDIR"] = "/dev/shm"
    tempfile.tempdir = "/dev/shm"


class OCREngineError(RuntimeError):
    pass

ISSUERS = {
    "ENEL": ("ENEL", "DISTRIBUICAO"),
    "VIVO": ("VIVO", "TELEFONICA"),
    "CLARO": ("CLARO", "NET SERVICOS"),
}
ADDRESS_LABELS = {
    "ENEL": ("ENDERECO DA INSTALACAO", "ENDERECO DE INSTALACAO", "ENDERECO DA UNIDADE CONSUMIDORA",
             "INSTALACAO CONSUMIDORA", "UNIDADE CONSUMIDORA"),
    "VIVO": ("CADASTRO DO ASSINANTE", "ENDERECO DO CLIENTE", "ENDERECO DE INSTALACAO", "ENDERECO DO SERVICO",
             "ENDERECO DE SERVICO"),
    "CLARO": ("ENDERECO DE INSTALACAO", "ENDERECO DO PONTO DE ACESSO", "ENDERECO DE SERVICO"),
}
PRIMARY_ADDRESS_LABELS = {
    "ENEL": "ENDERECO DA INSTALACAO",
    "VIVO": "ENDERECO DO CLIENTE",
    "CLARO": "ENDERECO DE INSTALACAO",
}
FALLBACK_ADDRESS_LABELS = {
    "VIVO": ("ENDERECO", "NOME DO CLIENTE"),
    "CLARO": ("ENDERECO DO CLIENTE", "NOME DO CLIENTE", "ENDERECO DA EMPRESA"),
}
ADDRESS_REGIONS = {
    "ENEL": (0.04, 0.078, 0.67, 0.110),
    "VIVO": (0.215, 0.073, 0.745, 0.119),
    "CLARO": (0.205, 0.136, 0.55, 0.188),
}
BILLING_LABELS = (
    "ENDERECO DE COBRANCA",
    "ENDERECO PARA PAGAMENTO",
    "ENDERECO DE FATURAMENTO",
)
BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
REQUIRED_ADDRESS_FIELDS = ("street", "number", "neighborhood", "city", "state", "postal_code")


@dataclass
class Address:
    street: str
    number: str
    complement: str
    neighborhood: str
    city: str
    state: str
    postal_code: str


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char)).upper()


def _order_points(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]
    return ordered


def _deskew(image: np.ndarray) -> tuple[np.ndarray, bool]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 180)
    height, width = gray.shape
    segments = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80,
        minLineLength=max(50, width * 0.2), maxLineGap=20,
    )
    if segments is None:
        return image, False
    angles = []
    for x1, y1, x2, y2 in segments[:, 0]:
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 35:
            angles.append(angle)
    if len(angles) < 3:
        return image, False
    angle = float(np.median(angles))
    if abs(angle) < 0.5:
        return image, False

    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    sine, cosine = abs(matrix[0, 1]), abs(matrix[0, 0])
    target_width = int(np.ceil(height * sine + width * cosine))
    target_height = int(np.ceil(height * cosine + width * sine))
    if target_width * target_height > MAX_IMAGE_PIXELS:
        return image, False
    matrix[0, 2] += (target_width - width) / 2
    matrix[1, 2] += (target_height - height) / 2
    corrected = cv2.warpAffine(
        image, matrix, (target_width, target_height),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return corrected, True


def _rectify(image: np.ndarray) -> tuple[np.ndarray, bool]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 60, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = image.shape[0] * image.shape[1]
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        if area < image_area * 0.5:
            break
        polygon = cv2.approxPolyDP(
            contour, 0.02 * cv2.arcLength(contour, True), True
        )
        if len(polygon) != 4:
            continue
        top_left, top_right, bottom_right, bottom_left = _order_points(
            polygon.reshape(4, 2).astype("float32")
        )
        width = int(max(
            np.linalg.norm(bottom_right - bottom_left),
            np.linalg.norm(top_right - top_left),
        ))
        height = int(max(
            np.linalg.norm(top_right - bottom_right),
            np.linalg.norm(top_left - bottom_left),
        ))
        if min(width, height) < 300 or width * height > MAX_IMAGE_PIXELS:
            continue
        source = np.array(
            [top_left, top_right, bottom_right, bottom_left], dtype="float32"
        )
        destination = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype="float32",
        )
        transform = cv2.getPerspectiveTransform(source, destination)
        return cv2.warpPerspective(image, transform, (width, height)), True
    return image, False


def _ocr_data(
    image: np.ndarray,
    psm: int = 6,
    scale: float = 1.0,
    adaptive: bool = False,
    preprocessed: bool = False,
    lang: str = "por",
    with_word_confidence: bool = False,
) -> tuple[list[tuple[str, tuple[int, int, int, int], float]], float] | tuple[
    list[tuple[str, tuple[int, int, int, int], float]], float,
    dict[tuple[int, int, int, int], list[float]],
]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if not preprocessed:
        if scale > 1 and gray.shape[0] * gray.shape[1] * scale**2 <= MAX_IMAGE_PIXELS:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        elif gray.shape[1] < 1400 and (gray.shape[0] < 2300 or psm == 4):
            factor = 1400 / gray.shape[1]
            gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
        if adaptive:
            gray = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
            )
        else:
            gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    try:
        data = pytesseract.image_to_data(
            gray,
            lang=lang,
            config=f"--oem 3 --psm {psm}",
            output_type=pytesseract.Output.DICT,
            timeout=20,
        )
    except PermissionError as error:
        raise OCREngineError(
            "O sistema negou a execução do Tesseract. Verifique a permissão de execução."
        ) from error
    except (FileNotFoundError, pytesseract.TesseractNotFoundError) as error:
        raise OCREngineError(
            "Tesseract não encontrado. Instale tesseract-ocr e tesseract-ocr-por."
        ) from error
    except RuntimeError as error:
        if "timeout" in str(error).lower():
            raise TimeoutError("A leitura OCR excedeu o tempo limite.") from error
        raise OCREngineError("O Tesseract não conseguiu processar a imagem.") from error
    rows: dict[tuple[int, int, int, int], list[tuple[str, tuple[int, int, int, int], float]]] = {}
    confidences = []
    for index, value in enumerate(data["text"]):
        value = value.strip()
        if not value:
            continue
        try:
            score = float(data["conf"][index])
            if score >= 0:
                confidences.append(score / 100)
        except (ValueError, TypeError):
            score = 0.0
        key = tuple(
            int(data[field][index])
            for field in ("page_num", "block_num", "par_num", "line_num")
        )
        left, top = int(data["left"][index]), int(data["top"][index])
        bounds = (
            left,
            top,
            left + int(data["width"][index]),
            top + int(data["height"][index]),
        )
        rows.setdefault(key, []).append((value, bounds, max(0.0, score) / 100))
    records = []
    word_confidences = {}
    for words in rows.values():
        bounds = (
            min(word[1][0] for word in words),
            min(word[1][1] for word in words),
            max(word[1][2] for word in words),
            max(word[1][3] for word in words),
        )
        scores = [word[2] for word in words]
        records.append((
            " ".join(word[0] for word in words),
            bounds,
            sum(scores) / len(scores) if scores else 0.0,
        ))
        word_confidences[bounds] = scores
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    if with_word_confidence:
        return records, confidence, word_confidences
    return records, confidence


def _ocr(image: np.ndarray, psm: int = 6, scale: float = 1.0, adaptive: bool = False) -> tuple[list[str], float]:
    records, confidence = _ocr_data(image, psm, scale, adaptive)
    return [text for text, _, _ in records], confidence


def _read_ocr(image: np.ndarray) -> tuple[list[str], float]:
    """Reads an already prepared crop without extra contrast or resizing."""
    records, confidence = _ocr_data(image, psm=6, preprocessed=True)
    return [text for text, _, _ in records], round(confidence, 2)


def _preprocess(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 9, 7, 21)
    contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    return cv2.adaptiveThreshold(
        contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )


def _issuer(lines: list[str]) -> str | None:
    text = _plain(" ".join(lines))
    for issuer, clues in ISSUERS.items():
        if any(clue in text for clue in clues):
            return issuer
    return None


def _address_section(lines: list[str], issuer: str) -> list[str] | None:
    labels = [
        (0, label) for label in ADDRESS_LABELS[issuer]
    ] + [
        (1, label) for label in FALLBACK_ADDRESS_LABELS.get(issuer, ())
    ]
    starts = []
    for index, line in enumerate(lines):
        normalized = _plain(line)
        if any(_plain(label) in normalized for label in BILLING_LABELS):
            continue
        for priority, label in labels:
            marker = normalized.find(_plain(label))
            if marker >= 0:
                starts.append((priority, index, marker, label))
    for _, start, marker, label in sorted(starts):
        section = []
        inline = lines[start][marker + len(label):].strip(" :-\t")
        if inline:
            section.append(inline)
        for line in lines[start + 1:]:
            normalized = _plain(line)
            if any(
                token in normalized
                for token in (
                    "RESUMO DO DOCUMENTO",
                    "VEJA AQUI O QUE ESTA SENDO COBRADO",
                    "CANAIS DE ATENDIMENTO",
                    *BILLING_LABELS,
                )
            ):
                break
            if line.strip():
                section.append(line.strip())
            if re.search(r"\b\d{5}[- ]?\d{3}\b", normalized) or len(section) == 6:
                break
        if _parse_document_address(section, issuer) is not None:
            return section
    return None


def _address_block(lines: list[str], issuer: str) -> list[str] | None:
    def compact(text: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", _plain(text))

    labels = [(0, label) for label in ADDRESS_LABELS[issuer]]
    labels.extend((1, label) for label in FALLBACK_ADDRESS_LABELS.get(issuer, ()))
    normalized_labels = [(priority, compact(label)) for priority, label in labels]
    billing_labels = tuple(compact(label) for label in BILLING_LABELS)
    starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        normalized = compact(line)
        if any(label in normalized for label in billing_labels):
            continue
        for priority, label in normalized_labels:
            if label in normalized:
                starts.append((priority, index))
    for _, start in sorted(set(starts)):
        block = []
        for line in lines[start:start + 10]:
            normalized = _plain(line)
            compact_line = compact(line)
            if any(label in compact_line for label in billing_labels):
                break
            if any(token in normalized for token in ("VENCIMENTO", "VALOR TOTAL", "CONSUMO", "NOTA FISCAL")):
                break
            block.append(line)
            if re.search(r"\b\d{5}[- ]?\d{3}\b", normalized):
                break
        if _parse_address(block, issuer) is not None:
            return block
    return None


def _neighborhood_from_line(line: str) -> str:
    if not line or re.search(r"\d", line):
        return ""
    if re.search(r"(?:WWW|HTTP|\.COM(?:\.|$)|@|VIVO|TELEFONICA|CLARO|ENEL)", line):
        return ""
    noise = ("ENDERECO", "INSTALACAO", "SERVICO", "CADASTRO", "ASSINANTE", "CLIENTE", "COBRANCA",
             "VENCIMENTO", "FATURA", "CONTA", "CEP", "NOTA FISCAL", "CONSUMIDORA")
    if any(token in line for token in noise) or re.search(r"\b(?:SP|RJ|MG|PR|SC|RS|BA|PE|CE)\b", line):
        return ""
    return line


def _parse_claro_customer_block(lines: list[str], address: Address) -> Address:
    normalized = [_plain(line).strip(" ,;:-") for line in lines]
    start = next((index for index, line in enumerate(normalized)
                  if "NOME DO CLIENTE" in line or "ENDERECO DA EMPRESA" in line), None)
    if start is None:
        return address
    block = normalized[start:start + 8]
    source = next((line for line in block if "ENDERECO DA EMPRESA" in line), "")
    if not source:
        return address

    tail = re.sub(r"^.*?\bENDERECO DA EMPRESA\b", "", source).strip(" ,;:-")
    number_match = re.search(r"\b(\d+[A-Z]?)\b", tail)
    if number_match is None:
        return address
    address.number = number_match.group(1)
    remainder = tail[number_match.end():].strip(" ,;:-")
    split = re.search(r"\b(JARDIM|VILA|CENTRO|PARQUE|RESIDENCIAL|ALDEIA|CONJUNTO)\b", remainder)
    if split:
        address.complement = remainder[:split.start()].strip(" ,;:-")
        address.neighborhood = remainder[split.start():].strip(" ,;:-")
    else:
        address.complement = remainder

    for line in block[block.index(source) + 1:]:
        if re.search(r"\b\d{5}[- ]?\d{3}\b", line):
            break
        neighborhood = _neighborhood_from_line(line)
        if neighborhood:
            address.neighborhood = neighborhood
            break
    return address


def _parse_address(lines: list[str], issuer: str | None = None) -> Address | None:
    normalized = [_plain(line).strip(" ,;:-") for line in lines]
    postal_code = ""
    for line in normalized:
        match = re.search(r"\b(\d{5})[- ]?(\d{3})\b", line)
        if match:
            postal_code = f"{match.group(1)}-{match.group(2)}"
            break

    city, state = "", ""
    for line in normalized:
        match = re.search(r"\b([A-Z][A-Z .'-]{1,35})\s*[-/]\s*([A-Z]{2})\b", line)
        if match is None:
            match = re.search(r"\b([A-Z][A-Z .'-]{1,35})\s+([A-Z]{2})\b", line)
        if match and match.group(2) in BRAZILIAN_STATES:
            city, state = match.group(1).strip(" .-"), match.group(2)
            break

    road_pattern = re.compile(r"^(RUA|R\.?|AVENIDA|AV\.?|ALAMEDA|AL\.?|TRAVESSA|ESTRADA|RODOVIA|PRACA)\s+(.+)$")
    street = number = complement = inline_neighborhood = ""
    address_index = -1
    for index, line in enumerate(normalized):
        candidate = re.sub(r"^.*?\bENDERECO\b\s*[:.-]?\s*", "", line)
        candidate = re.sub(r"\b\d{5}[- ]?\d{3}\b", "", candidate)
        candidate = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", "", candidate)
        candidate = re.sub(r"\bCEP\b\s*[:.-]?\s*", "", candidate)
        if city and state:
            candidate = re.sub(rf"\b{re.escape(city)}\s*[-/]?\s*{re.escape(state)}\b", "", candidate)
        candidate = candidate.strip(" ,;:-/")
        road = road_pattern.match(candidate)
        if road is None:
            continue
        body = re.sub(r"\s+", " ", road.group(2)).strip(" ,;:-/")
        number_match = re.search(r"\b(\d+[A-Z]?)\b", body)
        street_name = body[:number_match.start()].strip(" ,") if number_match else ""
        street = f"{road.group(1)} {street_name}".strip()
        number = number_match.group(1) if number_match else ""
        remainder = body[number_match.end():].strip(" ,;:-") if number_match else ""
        neighborhood_match = re.search(r"\bBAIRRO\s+(.+)$", remainder)
        if neighborhood_match:
            inline_neighborhood = neighborhood_match.group(1).strip(" ,;:-")
            remainder = remainder[:neighborhood_match.start()].strip(" ,;:-")
        residential_match = re.search(r"\bRESIDENCIAL\s+(.+)$", remainder)
        if residential_match and issuer == "VIVO":
            inline_neighborhood = residential_match.group(0).strip(" ,;:-")
            remainder = remainder[:residential_match.start()].strip(" ,;:-")
        lot_match = re.match(r"\b(LT|LOTE)\s*([A-Z0-9-]+)\b", remainder)
        if lot_match:
            complement = f"LT {lot_match.group(2)}"
            lot_tail = remainder[lot_match.end():].strip(" ,;:-")
            if issuer == "VIVO" and not inline_neighborhood:
                inline_neighborhood = _neighborhood_from_line(lot_tail)
        elif issuer == "VIVO" and remainder and not inline_neighborhood:
            complement_match = re.match(
                r"(?i)^(?:APTO?|AP|BL(?:OCO)?|CASA|SL|SALA)\s*[A-Z0-9-]+(?:\s+|$)",
                remainder,
            )
            if complement_match:
                complement = remainder[:complement_match.end()].strip(" ,;:-")
                inline_neighborhood = _neighborhood_from_line(
                    remainder[complement_match.end():].strip(" ,;:-")
                )
            else:
                inline_neighborhood = _neighborhood_from_line(remainder)
                complement = "" if inline_neighborhood else remainder
        else:
            complement = remainder
        address_index = index
        break

    if not ((street and number) or (postal_code and city and state)):
        return None
    neighborhood = inline_neighborhood
    if not neighborhood and address_index >= 0:
        neighborhood = next(
            (value for line in normalized[address_index + 1:]
             if (value := _neighborhood_from_line(line))),
            "",
        )
    address = Address(street, number, complement, neighborhood, city, state, postal_code)
    return _parse_claro_customer_block(lines, address) if issuer == "CLARO" else address


UNIT_PREFIX = r"(?:SL|SALA|AP|APTO|BL|BLOCO|CJ|LJ|LT|LOTE|QD)"


def _clean_street(street: str) -> str:
    # "RCORA" -> "R CORA": no street name starts with R followed by a consonant.
    street = re.sub(r"^R(?=[BCDFGJKLMNPQSTVWXZ][A-Z])", "R ", street)
    # Unit identifiers glued to an O read instead of zero ("SLO" -> "SL 0").
    return re.sub(r"\b(SL|AP|BL|CJ|LJ|LT|QD)[O0]\b", r"\1 0", street)


def _clean_complement(complement: str) -> str:
    if not re.match(rf"^{UNIT_PREFIX}\b", complement):
        return complement
    complement = re.sub(r"\bE[O0]\b", "E 0", complement)
    # In "SL 0 E 0"-style ranges a lone O/Q/D next to a unit prefix is a misread zero.
    tokens = complement.split()
    return " ".join(
        "0" if token == "O" or (
            token in {"Q", "D"} and index and re.fullmatch(UNIT_PREFIX, tokens[index - 1])
            and index + 1 < len(tokens) and tokens[index + 1] == "E"
        ) else token
        for index, token in enumerate(tokens)
    )


def _parse_reference_region(text: str) -> Address | None:
    address = Address("", "", "", "", "", "", "")
    lines = []
    for line in text.splitlines():
        line = line.translate(str.maketrans({"—": "-", "–": "-", "−": "-"}))
        normalized = _plain(line)
        metadata = [
            normalized.find(label)
            for label in ("CPF/CNPJ", "RAZAO SOCIAL", "CNPJ MATRIZ", "FILIAL:")
            if normalized.find(label) >= 0
        ]
        side_box = CLARO_SIDE_BOX.search(normalized)
        if side_box and side_box.start() > 0:
            metadata.append(side_box.start())
        if metadata:
            line = line[:min(metadata)]
        if line.strip() and not _plain(line).startswith("NOME DO CLIENTE"):
            lines.append(line.strip(" :-\t"))
    states = "|".join(sorted(BRAZILIAN_STATES, key=len, reverse=True))
    postal_pattern = re.compile(r"\b([0-9]{5})[- ]?([0-9]{3})(?![0-9])")
    city_pattern = re.compile(
        rf"^(.+?)\s*[-/ ]\s*({states})(?:\s+[|\[\]].*)?\s*$", re.IGNORECASE
    )
    location_lines = []
    for line in lines:
        postal = postal_pattern.search(line)
        if postal:
            address.postal_code = f"{postal[1]}-{postal[2]}"
            line = line[postal.end():].strip(" ,-")
        else:
            line = re.sub(r"\s+CEP\b.*$", "", line, flags=re.IGNORECASE)
            line = re.sub(r"^CEP\b\s*[:.]?\s*", "", line, flags=re.IGNORECASE)
            unreadable_postal = re.match(
                r"^([A-Z0-9]{5}\s*-\s*[A-Z0-9]{3})(?![0-9])\s*[-,]?\s*(.*)$",
                line,
                flags=re.IGNORECASE,
            )
            if (
                unreadable_postal
                and re.search(r"[0-9]", unreadable_postal[1])
                and (
                    not unreadable_postal[2]
                    or city_pattern.fullmatch(unreadable_postal[2])
                )
            ):
                line = unreadable_postal[2]
            line = re.sub(r"^[0-9][0-9 -]*\s+", "", line)
        city = city_pattern.fullmatch(line)
        separator_lost = False
        if city is None and postal:
            city = re.fullmatch(rf"(.{{3,}}?)({states})", line, re.IGNORECASE)
            separator_lost = city is not None
        if city:
            address.city = city[1].strip(" ,-")
            if separator_lost:
                # The "/" between city and UF is often read as I, J, l or |.
                address.city = re.sub(r"(?<=[A-Z]{3})[IJl|1/\\]{1,2}$", "", address.city)
            address.state = city[2].upper()
            break
        if line and not postal:
            location_lines.append(_plain(line))
    while len(location_lines) > 1 and not re.search(r"[0-9]", location_lines[0]):
        if not re.search(r"[0-9]", location_lines[1]):
            break
        location_lines.pop(0)
    if location_lines:
        street = _clean_street(location_lines[0])
        neighborhood = re.search(r"\bBAIRRO\s*:?\s*(.+)", street, re.IGNORECASE)
        if neighborhood:
            address.neighborhood = neighborhood[1].strip()
            street = street[:neighborhood.start()].strip(" ,")
        elif len(location_lines) > 1:
            address.neighborhood = re.sub(
                r"^BAIRRO\s*:\s*", "", location_lines[1], flags=re.IGNORECASE
            ).strip()
        number = re.search(
            r"(?:,\s*|\s+(?:N[ºO°.]?\s*)?)([0-9]+[A-Z]?)(?=\s*[.;]?\s*(?:$|,|SL\b|AP\b|CJ\b|BL\b))",
            street,
            re.IGNORECASE,
        )
        if number:
            address.number = number[1].upper()
            address.street = street[:number.start()].strip(" ,")
            address.complement = _clean_complement(street[number.end():].strip(" ,.;:-"))
        else:
            address.street = street
    return address if any(asdict(address).values()) else None


def _parse_reference_vivo(text: str) -> Address | None:
    marker = re.search(r"(?im)^\s*ENDERE[ÇC]O(?:\s*:\s*|\s+)", text)
    if marker is None:
        return None
    block = text[marker.end():]
    block = re.split(
        r"(?im)^\s*(?:C[ÓO]DIGO DO CLIENTE|M[ÊE]S DE REFER[ÊE]NCIA|N[ÚU]MERO DA FATURA|DATA DE EMISS[ÃA]O)\b",
        block,
        maxsplit=1,
    )[0]
    block = " ".join(block.split()).translate(str.maketrans({"—": "-", "–": "-"}))
    postal = re.search(r"\b[0-9]{5}-?[0-9]{3}\b", block)
    if postal is None:
        return None
    location = block[:postal.start()].strip(" ,-")
    city_line = postal[0]
    city = re.match(
        rf"[\s,-]*([^\d/:;\n]+?)\s*[-/ ]\s*({'|'.join(BRAZILIAN_STATES)})\b",
        block[postal.end():],
        flags=re.IGNORECASE,
    )
    if city:
        city_line = f"{postal[0]} - {city[1]} / {city[2]}"
    street = re.fullmatch(r"(.+?)\s+([0-9]+[A-Z]?)\b(.*)", location, flags=re.IGNORECASE)
    if street is None:
        return _parse_reference_region(city_line)
    remainder = street[3].strip(" ,")
    lot = re.match(r"(?i)^(?:LT|LOTE)\.?\s*([0-9A-Z-]+)\b", remainder)
    complement = f"LT {lot[1]}" if lot else ""
    neighborhood = re.sub(
        r"^(?:(?:LT|LOTE)\.?\s+[0-9A-Z-]+\s*)+",
        "",
        remainder,
        flags=re.IGNORECASE,
    ).strip(" ,-")
    # Text from the neighbouring box (e.g. the due date) may join the line.
    neighborhood = re.split(r"\s+-\s+|\s+-?\s*[0-9]{2}/[0-9]{2}", neighborhood)[0].strip(" ,-")
    address = _parse_reference_region(
        f"{street[1]} {street[2]}\n{neighborhood}\n{city_line}"
    )
    if address is not None:
        address.complement = complement
    return address


def _has_street_prefix(street: str) -> bool:
    return re.match(
        r"^(?:RUA|R\.?|AVENIDA|AV\.?|ALAMEDA|AL\.?|TRAVESSA|ESTRADA|RODOVIA|PRACA)\b",
        _plain(street),
    ) is not None


def _parse_document_address(
    lines: list[str], issuer: str, prefer_reference: bool = False
) -> Address | None:
    text = "\n".join(lines)
    if prefer_reference:
        # Anchored blocks use the reference parsers; the validated merge is only
        # used when OCR noise above the address was taken as the street.
        direct = (
            _parse_reference_vivo(text) if issuer == "VIVO" else _parse_reference_region(text)
        )
        merged = _parse_document_address(lines, issuer)
        if direct is None or (
            not _has_street_prefix(direct.street)
            and merged is not None and _has_street_prefix(merged.street)
        ):
            return merged
        return direct
    parsed = _parse_address(lines, issuer)
    if issuer == "VIVO":
        reference = _parse_reference_vivo(text)
    elif issuer == "CLARO":
        reference = None
    else:
        cleaned_lines = []
        labels = sorted(
            ADDRESS_LABELS.get(issuer, ()) + FALLBACK_ADDRESS_LABELS.get(issuer, ()),
            key=len,
            reverse=True,
        )
        for line in lines:
            normalized = _plain(line)
            for label in labels:
                marker = _plain(label)
                index = normalized.find(marker)
                if index >= 0:
                    line = line[index + len(label):].strip(" :-\t")
                    break
            if line:
                cleaned_lines.append(line)
        reference = _parse_reference_region("\n".join(cleaned_lines))
    if reference is None:
        return parsed
    if parsed is None:
        parsed = Address("", "", "", "", "", "", "")
    valid_reference_street = _has_street_prefix(reference.street)
    valid_reference_postal = re.fullmatch(r"[0-9]{5}-[0-9]{3}", reference.postal_code) is not None
    reference_street = reference.street if valid_reference_street else ""
    reference_number = (
        reference.number
        if valid_reference_street and re.fullmatch(r"[0-9]+[A-Z]?", reference.number)
        else ""
    )
    reference_neighborhood = (
        reference.neighborhood
        if valid_reference_street
        and _neighborhood_from_line(reference.neighborhood)
        and re.search(r"[A-Z]{3,}", _plain(reference.neighborhood))
        else ""
    )
    reference_city = (
        reference.city
        if valid_reference_postal and not re.search(r"\d", reference.city)
        else ""
    )
    reference_state = (
        reference.state
        if valid_reference_postal and reference.state in BRAZILIAN_STATES
        else ""
    )
    reference_postal = reference.postal_code if valid_reference_postal else ""
    return Address(
        parsed.street or reference_street,
        parsed.number or reference_number,
        parsed.complement or reference.complement,
        parsed.neighborhood or reference_neighborhood,
        parsed.city or reference_city,
        parsed.state or reference_state,
        parsed.postal_code or reference_postal,
    )


def _address_score(address: Address) -> int:
    return sum(bool(getattr(address, field)) for field in REQUIRED_ADDRESS_FIELDS)


def _has_required_address(address: Address | None) -> bool:
    return address is not None and all(getattr(address, field) for field in REQUIRED_ADDRESS_FIELDS)


def _merge_addresses(preferred: Address, fallback: Address | None) -> Address:
    if fallback is None:
        return preferred
    preferred_fields = asdict(preferred)
    fallback_fields = asdict(fallback)
    return Address(**{
        field: preferred_fields[field] or fallback_fields[field]
        for field in preferred_fields
    })


def _customer_region(
    image: np.ndarray,
    lines: list[tuple[str, tuple[int, int, int, int], float]],
    issuer: str,
) -> tuple[np.ndarray, str, tuple[int, int, int, int]] | None:
    original_text = {bounds: text for text, bounds, _ in lines}
    ordered = sorted(
        ((_plain(text), bounds) for text, bounds, _ in lines),
        key=lambda item: (item[1][1], item[1][0]),
    )
    selected = []
    if issuer == "ENEL":
        for text, (left, top, _, bottom) in ordered:
            if "CPF" not in text:
                continue
            line_height = bottom - top
            preceding = [
                (text, bounds) for text, bounds in ordered
                if top - line_height * 6 <= bounds[1] < top
                and abs(bounds[0] - left) < line_height * 2
            ]
            streets = [
                bounds for text, bounds in preceding
                if re.match(r"^(?:RUA|R\.|AV\.?|AVENIDA|TRAVESSA|PRACA)\s", text)
            ]
            if streets:
                street_top = streets[-1][1]
                selected = [bounds for _, bounds in preceding if bounds[1] >= street_top]
                break
    elif issuer == "CLARO":
        anchor_index = next(
            (index for index, (text, _) in enumerate(ordered)
             if text.startswith("NOME DO CLIENTE")),
            None,
        )
        if anchor_index is None:
            anchor_index = next(
                (index for index, (text, _) in enumerate(ordered)
                 if any(label in text for label in (
                     "ENDERECO DO PONTO DE ACESSO", "ENDERECO DE INSTALACAO",
                 ))),
                None,
            )
        if anchor_index is not None:
            _, anchor = ordered[anchor_index]
            left, top, _, bottom = anchor
            line_height = bottom - top
            selected = []
            for text, bounds in ordered[anchor_index:anchor_index + 10]:
                if abs(bounds[0] - left) > line_height * 2:
                    continue
                selected.append(bounds)
                if re.search(r"\b\d{5}[- ]?\d{3}\b", text):
                    break
    elif issuer == "VIVO":
        subscriber = next(
            (bounds for text, bounds in ordered if "CADASTRO DO ASSINANTE" in text),
            None,
        )
        for text, bounds in ordered:
            marker = re.match(r"^ENDERECO(?:\s*:|\s+)", text)
            first_word = text.split()[0].rstrip(":")
            approximate_marker = (
                SequenceMatcher(None, first_word, "ENDERECO").ratio() >= 0.6
                and re.search(r"\b[0-9]{5}-?[0-9]{3}\b", text)
            )
            if not marker and not approximate_marker:
                continue
            if "FORNECEDOR" in text or "EMISSOR" in text:
                continue
            left, top, _, bottom = bounds
            line_height = bottom - top
            if subscriber and not subscriber[3] <= top <= subscriber[3] + line_height * 8:
                continue
            if not subscriber and not any(
                "CODIGO DO" in text and top + line_height * 0.4 <= box[1] <= bottom + line_height * 4
                for text, box in ordered
            ):
                continue
            selected = [bounds]
            if not re.search(r"\b[0-9]{5}-?[0-9]{3}\b", text):
                selected += [
                    box for text, box in ordered
                    if bottom <= box[1] <= bottom + line_height * 2
                    and abs(box[0] - left) < line_height * 2
                    and not re.match(r"^(?:CODIGO|MES|NUMERO|DATA)\b", text)
                ]
            if not marker:
                original_text[bounds] = re.sub(
                    r"^\S+\s*", "Endereco: ", original_text[bounds], count=1
                )
            break
    if not selected:
        return None
    padding = max(
        4,
        int(np.median([bounds[3] - bounds[1] for bounds in selected]) * 0.3),
    )
    left = max(0, min(bounds[0] for bounds in selected) - padding)
    top = max(0, min(bounds[1] for bounds in selected) - padding)
    right = min(image.shape[1], max(bounds[2] for bounds in selected) + padding)
    bottom = min(image.shape[0], max(bounds[3] for bounds in selected) + padding)
    text = "\n".join(original_text[bounds] for bounds in selected)
    return image[top:bottom, left:right], text, (left, top, right, bottom)


def _region_image(image: np.ndarray, issuer: str) -> np.ndarray:
    height, width = image.shape[:2]
    left, top, right, bottom = ADDRESS_REGIONS[issuer]
    region = image[
        int(height * top):int(height * bottom),
        int(width * left):int(width * right),
    ]
    scale = min(6.0, max(1.0, 1600 / region.shape[1]))
    enlarged = cv2.resize(region, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
    if issuer == "VIVO":
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return cv2.copyMakeBorder(
        gray, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255
    )


def _extract_anchored(image: np.ndarray) -> tuple[str | None, float, Address | None]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    background = cv2.GaussianBlur(gray, (0, 0), 25)
    scan = cv2.divide(gray, background, scale=255)
    scale = min(1.5, (8_000_000 / scan.size) ** 0.5)
    scan = cv2.resize(scan, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    lines, confidence, word_confidences = _ocr_data(
        scan, psm=11, preprocessed=True, lang="por", with_word_confidence=True
    )
    issuer = _issuer([text for text, _, _ in lines])
    if issuer is None:
        return None, confidence, None
    located = _customer_region(scan, lines, issuer)
    if located is None:
        return issuer, confidence, None
    region, anchor_text, bounds = located
    if issuer in ADDRESS_REGIONS:
        left, top, right, bottom = ADDRESS_REGIONS[issuer]
        height, width = scan.shape
        if (
            left * width <= bounds[0] and top * height <= bounds[1]
            and bounds[2] <= right * width and bounds[3] <= bottom * height
        ):
            text, region_confidence = _read_ocr(_region_image(image, issuer))
            candidate = _parse_document_address(text, issuer, prefer_reference=True)
            if _has_required_address(candidate) and region_confidence >= 0.85:
                return issuer, region_confidence, candidate
    candidates = [(
        _parse_document_address(anchor_text.splitlines(), issuer, prefer_reference=True),
        confidence,
    )]
    selected_confidences = [
        score for box, scores in word_confidences.items() for score in scores
        if bounds[0] <= box[0] and bounds[1] <= box[1]
        and box[2] <= bounds[2] and box[3] <= bounds[3]
    ]
    if selected_confidences:
        confidence = round(sum(selected_confidences) / len(selected_confidences), 2)
        candidates[0] = (candidates[0][0], confidence)
    for target_width in (1600, 2400):
        scale = min(
            4.0,
            max(1.0, target_width / region.shape[1]),
            (MAX_IMAGE_PIXELS / region.size) ** 0.5,
        )
        enlarged = cv2.resize(region, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        enlarged = cv2.copyMakeBorder(
            enlarged, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255
        )
        text, region_confidence = _read_ocr(enlarged)
        candidate = _parse_document_address(text, issuer, prefer_reference=True)
        candidates.append((candidate, region_confidence))
        if _has_required_address(candidate) and region_confidence >= 0.85:
            break
    address, confidence = max(
        candidates,
        key=lambda candidate: (
            _address_score(candidate[0]) if candidate[0] is not None else 0,
            candidate[1],
        ),
    )
    if address is not None and any(
        other is not None and getattr(other, field) and getattr(address, field)
        and _plain(getattr(other, field)) != _plain(getattr(address, field))
        for other, _ in candidates for field in REQUIRED_ADDRESS_FIELDS
    ):
        confidence = min(confidence, 0.84)
    if confidence < 0.85 and issuer == "VIVO":
        refined = read_subscriber_line(region)
        if refined:
            refined_text, refined_confidence = refined
            refined_text = re.sub(
                r"(?i)^\s*ENDERE[ÇC]OS\b", "Endereco", refined_text
            )
            candidate = _parse_document_address(
                [refined_text], issuer, prefer_reference=True
            )
            if (
                _has_required_address(candidate)
                and refined_confidence >= 0.7
                and all(
                    getattr(candidate, field) == getattr(address, field)
                    for field in ("postal_code", "city", "state")
                )
            ):
                if candidate != address:
                    refined_confidence = min(refined_confidence, 0.84)
                address, confidence = candidate, refined_confidence
    if confidence < 0.85 and issuer in {"CLARO", "ENEL"}:
        postal = read_postal_code(region)
        if postal:
            if address is None:
                address = Address("", "", "", "", "", "", "")
            address.postal_code = postal[0]
            confidence = min(confidence, postal[1])
    return issuer, confidence, address


def _rotate(image: np.ndarray, angle: float) -> np.ndarray:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    sine, cosine = abs(matrix[0, 1]), abs(matrix[0, 0])
    target_width = int(np.ceil(height * sine + width * cosine))
    target_height = int(np.ceil(height * cosine + width * sine))
    matrix[0, 2] += (target_width - width) / 2
    matrix[1, 2] += (target_height - height) / 2
    border = (255, 255, 255) if image.ndim == 3 else 255
    return cv2.warpAffine(
        image, matrix, (target_width, target_height),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=border,
    )


def _text_skew(image: np.ndarray, limit: float = 25.0) -> float:
    """Estimates the text angle by maximising the sharpness of the row projection.

    Unlike edge-based Hough lines, it is not misled by monitor bezels, table borders
    or the background, and also works when the page edges are out of frame.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    factor = min(1.0, 1000 / max(gray.shape))
    small = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    binary = cv2.adaptiveThreshold(
        small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 10
    )
    height, width = binary.shape
    center = (width / 2, height / 2)

    def sharpness(angle: float) -> float:
        rotated = cv2.warpAffine(
            binary, cv2.getRotationMatrix2D(center, angle, 1), (width, height),
            flags=cv2.INTER_NEAREST,
        )
        profile = rotated.sum(axis=1, dtype=np.float64)
        return float(np.square(np.diff(profile)).sum())

    best = max(np.arange(-limit, limit + 0.01, 1.0), key=sharpness)
    return float(max(np.arange(best - 1, best + 1.01, 0.1), key=sharpness))


def _label_similarity(word: str) -> float:
    word = re.sub(r"[^A-Z]", "", _plain(word))
    if len(word) < 6 or not word.startswith("E"):
        return 0.0
    return SequenceMatcher(None, word, "ENDERECO").ratio()


def _normalize_label(line: str) -> str:
    """Rewrites a misread "Endereço" label (e.g. "Endeseço", "| Endoroço:").

    Text from a neighbouring column may come before the label, so it is searched
    among the first words and anything before it is dropped.
    """
    words = line.split()
    for index, word in enumerate(words[:3]):
        if _label_similarity(word) >= 0.74:
            return "Endereco: " + " ".join(words[index + 1:])
    return line


CLARO_SIDE_BOX = re.compile(
    r"\bN[º°O]?\s*D[AO]\s+(?:CONTA|CLIENTE)|\bCPF|\bCNPJ|\bRAZAO|\bFILIAL|\bPERIODO|\bVEJA AQUI"
)


def _anchor_windows(
    lines: list[tuple[str, tuple[int, int, int, int], float]],
    issuer: str,
    shape: tuple[int, int],
) -> list[tuple[tuple[int, int, int, int], int]]:
    """Customer block windows, sized in line heights from an anchor word box.

    Returns (box, line height) pairs, most reliable anchors first.
    """
    page_height, page_width = shape
    ordered = sorted(lines, key=lambda item: (item[1][1], item[1][0]))
    candidates = []
    states = "|".join(BRAZILIAN_STATES)
    for text, (left, top, right, bottom), _ in ordered:
        normalized = _plain(text)
        line_height = max(8, bottom - top)
        window = None
        if issuer == "ENEL":
            if re.search(r"\bCPF", normalized):
                window = (2, (left - 2 * line_height, top - 5 * line_height,
                              left + 30 * line_height, bottom + line_height / 2))
            elif re.search(r"\bCEP\b", normalized) and re.search(r"[0-9]{5}", normalized):
                window = (1, (left - 2 * line_height, top - 4 * line_height,
                              left + 30 * line_height, bottom + line_height / 2))
        elif issuer == "CLARO":
            # The fiscal note at the bottom repeats "NOME DO CLIENTE ENDERECO".
            if top > page_height * 0.5 or ("ENDERECO" in normalized and "NOME" in normalized):
                continue
            if "NOME DO CLI" in normalized or re.match(r"^\W*E? ?DO CLIENTE\b", normalized):
                window = (3, (left - 5 * line_height, top - 1.5 * line_height,
                              left + 22 * line_height, top + 6 * line_height))
            elif "ENDERECO DA" in normalized:
                window = (2, (left - 3 * line_height, top - 2.5 * line_height,
                              left + 22 * line_height, top + 5 * line_height))
            elif re.search(rf"[A-Z]{{3,}}\s+({states})$", normalized) or re.search(
                r"\b[0-9]{5}-[0-9]{3}\b", normalized
            ):
                window = (1, (left - 12 * line_height, top - 4.5 * line_height,
                              left + 16 * line_height, bottom + line_height))
            if window:
                # Stop before the account box on the right (CPF/CNPJ, razão social...).
                x0, y0, x1, y1 = window[1]
                side = [
                    box[0] for value, box, _ in ordered
                    if CLARO_SIDE_BOX.search(_plain(value))
                    and box[0] > left + 4 * line_height and box[3] > y0 and box[1] < y1
                ]
                if side:
                    window = (window[0], (x0, y0, min(x1, min(side) - line_height / 2), y1))
        elif issuer == "VIVO":
            if "FORNECEDOR" in normalized or "EMISSOR" in normalized:
                continue
            similarity = max((_label_similarity(word) for word in text.split()[:3]), default=0)
            if similarity >= 0.74:
                window = (1 + similarity, (left - line_height, top - 3 * line_height,
                                           page_width, bottom + 3 * line_height))
            elif "CADASTRO DO ASSINANTE" in normalized:
                window = (1, (left - line_height, bottom, page_width, bottom + 7 * line_height))
        if window:
            candidates.append((window[0], window[1], line_height))
    boxes = []
    for _, (x0, y0, x1, y1), line_height in sorted(candidates, key=lambda item: -item[0]):
        box = (int(max(0, x0)), int(max(0, y0)),
               int(min(page_width, x1)), int(min(page_height, y1)))
        if box[2] - box[0] > 50 and box[3] - box[1] > 20 and box not in [b for b, _ in boxes]:
            boxes.append((box, line_height))
    return boxes


def _vote(
    reads: list[tuple[Address, float]],
) -> tuple[Address, float, bool]:
    """Confidence-weighted vote per field; returns the address, confidence and unanimity."""
    values, unanimous = {}, True
    for field in asdict(Address("", "", "", "", "", "", "")):
        found = [
            (getattr(address, field), confidence)
            for address, confidence in reads if getattr(address, field)
        ]
        if not found:
            values[field] = ""
            continue
        weights: Counter = Counter()
        for value, confidence in found:
            weights[re.sub(r"[^A-Z0-9]", "", _plain(value))] += max(confidence, 0.05)
        winner = weights.most_common(1)[0][0]
        members = [
            value for value, _ in found
            if re.sub(r"[^A-Z0-9]", "", _plain(value)) == winner
        ]
        if field in REQUIRED_ADDRESS_FIELDS and len(members) < len(reads):
            unanimous = False
        values[field] = Counter(members).most_common(1)[0][0]
    address = Address(**values)
    agreeing = [
        confidence for candidate, confidence in reads
        if all(
            _plain(getattr(candidate, field)) == _plain(getattr(address, field))
            for field in REQUIRED_ADDRESS_FIELDS
        )
    ]
    confidence = max(agreeing) if agreeing else max(confidence for _, confidence in reads)
    return address, round(confidence, 2), unanimous


def _window_lines(text: list[str], issuer: str) -> list[str]:
    if issuer == "VIVO":
        return [_normalize_label(line) for line in text]
    if issuer == "CLARO":
        # Noise above the block is dropped; the block starts at "NOME DO CLIENTE".
        start = next(
            (index for index, line in enumerate(text)
             if re.search(r"\bD[O0]\s*CLIENTE\b", _plain(line))),
            None,
        )
        if start is not None:
            return text[start:]
    return text


def _extract_windowed(
    image: np.ndarray, issuer: str | None
) -> tuple[str | None, float, Address | None]:
    """Locates the customer block, rectifies it locally and votes on several readings.

    Photos taken at an angle (e.g. of a screen or a curved page) have keystone
    distortion, so one global rotation leaves residual slope that breaks lines
    apart. Here the page is levelled by text, the block is located from word boxes,
    then each window is levelled again on its own before being re-read.
    """
    angle = _text_skew(image)
    page = _rotate(image, angle) if abs(angle) >= 0.5 else image
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    full = cv2.divide(gray, cv2.GaussianBlur(gray, (0, 0), 25), scale=255)
    # Anchors are located on a reduced copy (fast); windows are cut from the full page.
    scale = min(1.0, (4_000_000 / full.size) ** 0.5)
    scan = cv2.resize(full, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    lines, confidence = _ocr_data(scan, psm=11, preprocessed=True)
    issuer = _issuer([text for text, _, _ in lines]) or issuer
    if issuer is None:
        return None, confidence, None
    best = None
    for box, line_height in _anchor_windows(lines, issuer, scan.shape)[:3]:
        left, top, right, bottom = (int(value / scale) for value in box)
        crop = full[top:bottom, left:right]
        local_angle = _text_skew(crop, limit=12)
        if abs(local_angle) >= 0.3:
            crop = _rotate(crop, local_angle)
        line_height /= scale
        reads = []
        # Three readings with different text sizes and binarisations for the vote.
        for target_height, binarize in ((40, False), (40, True), (56, False)):
            factor = min(4.0, max(0.5, target_height / line_height),
                         (MAX_IMAGE_PIXELS / crop.size) ** 0.5)
            enlarged = cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
            if binarize:
                enlarged = cv2.threshold(
                    cv2.GaussianBlur(enlarged, (3, 3), 0), 0, 255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU,
                )[1]
            enlarged = cv2.copyMakeBorder(enlarged, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
            text, read_confidence = _read_ocr(enlarged)
            parsed = _parse_document_address(
                _window_lines(text, issuer), issuer, prefer_reference=True
            )
            reads.append((parsed or Address("", "", "", "", "", "", ""), read_confidence))
        address, window_confidence, unanimous = _vote(reads)
        if not unanimous:
            window_confidence = min(window_confidence, 0.84)
        if best is None or _address_score(address) > _address_score(best[1]):
            best = (window_confidence, address)
        if _has_required_address(address):
            break
    if best is None or not any(asdict(best[1]).values()):
        return issuer, confidence, None
    return issuer, best[0], best[1]


def extract_address(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Imagem vazia ou acima do limite de 10 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as metadata:
            width, height = metadata.size
            image_format = metadata.format
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("Arquivo inválido. Envie uma fotografia JPEG, PNG ou WEBP.") from error
    if image_format not in {"JPEG", "PNG", "WEBP"}:
        raise ValueError("Formato não suportado. Envie uma fotografia JPEG, PNG ou WEBP.")
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError("A imagem excede o limite de 24 megapixels.")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Arquivo inválido. Envie uma fotografia JPEG, PNG ou WEBP.")
    if image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
        raise ValueError("A imagem excede o limite de 24 megapixels.")
    rectified, perspective_corrected = _rectify(image)
    page, deskew_corrected = _deskew(rectified)
    if page.shape[0] * page.shape[1] > MAX_IMAGE_PIXELS:
        raise ValueError("A imagem corrigida excede o limite de 24 megapixels.")
    page_height, page_width = page.shape[:2]
    height, width = page_height, page_width
    margin_x, margin_y = int(page_width * 0.02), int(page_height * 0.02)
    corrected = (
        page[margin_y:page_height - margin_y, margin_x:page_width - margin_x]
        if margin_x and margin_y else page
    )
    processed = _preprocess(corrected)
    full_records, confidence = _ocr_data(processed, psm=6, preprocessed=True)
    full_lines = [text for text, _, _ in full_records]
    full_text = "\n".join(full_lines)
    issuer = _issuer(full_lines)
    result = None

    if issuer:
        block = _address_section(full_lines, issuer) or _address_block(full_lines, issuer)
        if block:
            result = _parse_document_address(block, issuer)

    has_primary_label = bool(
        issuer and _plain(PRIMARY_ADDRESS_LABELS[issuer]) in _plain(full_text)
    )
    windowed_complete = False
    if not (has_primary_label and _has_required_address(result)):
        windowed_issuer, windowed_confidence, windowed_address = _extract_windowed(
            rectified, issuer
        )
        if _has_required_address(windowed_address):
            issuer = issuer or windowed_issuer
            result, confidence, windowed_complete = windowed_address, windowed_confidence, True
        else:
            anchored_issuer, anchored_confidence, anchored_address = _extract_anchored(page)
            if anchored_address is not None and any(asdict(anchored_address).values()):
                issuer = anchored_issuer or issuer
                result = _merge_addresses(anchored_address, result)
                confidence = anchored_confidence
            elif issuer is None:
                issuer = anchored_issuer or windowed_issuer
            if windowed_address is not None and (
                result is None or _address_score(windowed_address) > _address_score(result)
            ):
                issuer = issuer or windowed_issuer
                result = _merge_addresses(windowed_address, result)
                confidence = min(confidence, windowed_confidence)

    if issuer is None:
        header = page[:max(1, int(height * 0.07))]
        scale = 1600 / header.shape[1]
        header = cv2.resize(
            header, (1600, max(1, int(header.shape[0] * scale))),
            interpolation=cv2.INTER_CUBIC,
        )
        header_text, confidence = _read_ocr(header)
        issuer = _issuer(header_text)

    detected_text = _plain(full_text)
    has_primary_label = bool(
        issuer and _plain(PRIMARY_ADDRESS_LABELS[issuer]) in detected_text
    )
    if (
        not windowed_complete and not deskew_corrected
        and issuer in ADDRESS_REGIONS and not has_primary_label
    ):
        ratio = width / height
        valid_ratio = 0.25 < ratio < 0.4 if issuer == "ENEL" else 0.6 < ratio < 0.85
        if valid_ratio:
            region_text, region_confidence = _read_ocr(_region_image(page, issuer))
            candidate = _parse_document_address(
                region_text, issuer, prefer_reference=True
            )
            if candidate is not None and (
                issuer == "VIVO" or (candidate.city and candidate.postal_code)
            ):
                result = _merge_addresses(candidate, result)
                confidence = region_confidence

    if issuer is None:
        raise ValueError(
            "Não foi possível identificar a empresa. Envie uma conta Enel, Vivo ou Claro legível."
        )
    if result is None:
        raise ValueError(
            "Endereço de instalação incompleto ou ilegível. Revise a foto e tente novamente."
        )
    return {
        "issuer": issuer,
        "address": asdict(result),
        "confidence": round(confidence, 3),
        "perspective_corrected": perspective_corrected,
        "deskew_corrected": deskew_corrected,
        "privacy": "Imagem processada em memória e descartada; nenhum arquivo é armazenado.",
    }
