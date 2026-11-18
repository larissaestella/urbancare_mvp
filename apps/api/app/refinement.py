import os
from pathlib import Path
import re
import shlex

import cv2
import numpy as np
import pytesseract


def _text_rows(image: np.ndarray) -> list[np.ndarray]:
    ink = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    active = (ink > 0).sum(axis=1) > max(2, image.shape[1] * 0.015)
    cuts = np.flatnonzero(np.diff(np.r_[False, active, False]))
    return [
        image[start - 1:end + 1]
        for start, end in zip(cuts[::2], cuts[1::2])
        if end - start >= 4 and start > 0 and end < image.shape[0]
    ]


def _enlarge_line(image: np.ndarray) -> np.ndarray:
    scale = min(3.0, (20_000_000 / image.size) ** 0.5)
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(image, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)


def read_subscriber_line(image: np.ndarray) -> tuple[str, float] | None:
    directory = Path(os.environ.get("TESSDATA_BEST_DIR", "/usr/local/share/tessdata-best"))
    if not (directory / "por.traineddata").is_file():
        return None
    rows = _text_rows(image)
    if not rows:
        return None
    row = max(rows, key=lambda row: float((255 - row.astype(np.float32)).sum()))
    config = (
        f"--tessdata-dir {shlex.quote(str(directory))} --oem 1 --psm 7 "
        "-c preserve_interword_spaces=1"
    )
    data = pytesseract.image_to_data(
        _enlarge_line(row), lang="por", config=config,
        output_type=pytesseract.Output.DICT, timeout=20,
    )
    words = [
        (word, float(confidence))
        for word, confidence in zip(data["text"], data["conf"])
        if word.strip()
    ]
    if not words:
        return None
    confidence = sum(max(0, score) for _, score in words) / len(words) / 100
    return " ".join(word for word, _ in words), round(confidence, 2)


def read_postal_code(image: np.ndarray) -> tuple[str, float] | None:
    for row in reversed(_text_rows(image)[-2:]):
        row = _enlarge_line(row)
        data = pytesseract.image_to_data(
            row, lang="por", config="--oem 3 --psm 7",
            output_type=pytesseract.Output.DICT, timeout=20,
        )
        matches = [
            index for index, word in enumerate(data["text"])
            if re.fullmatch(r"[A-Z0-9/|]{5}-?[A-Z0-9/|]{3}", word, re.IGNORECASE)
            and re.search(r"[0-9]", word)
        ]
        if len(matches) != 1:
            continue
        index = matches[0]
        x, y, width, height = (
            data[key][index] for key in ("left", "top", "width", "height")
        )
        word = row[max(0, y - 3):y + height + 3, max(0, x - 3):x + width + 3]
        word = cv2.copyMakeBorder(
            word, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255
        )
        word = cv2.threshold(word, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        readings = []
        for mode in (7, 8):
            numeric = pytesseract.image_to_data(
                word, lang="por",
                config=f"--oem 3 --psm {mode} -c tessedit_char_whitelist=0123456789-",
                output_type=pytesseract.Output.DICT, timeout=20,
            )
            tokens = [
                (text, float(confidence) / 100)
                for text, confidence in zip(numeric["text"], numeric["conf"])
                if text.strip()
            ]
            if len(tokens) == 1 and re.fullmatch(r"[0-9]{5}-?[0-9]{3}", tokens[0][0]):
                readings.append((tokens[0][0].replace("-", ""), tokens[0][1]))
        if (
            len(readings) == 2 and readings[0][0] == readings[1][0]
            and max(score for _, score in readings) >= 0.85
        ):
            digits = readings[0][0]
            confidence = min(score for _, score in readings)
            if confidence < 0.6:
                confidence = min(0.84, max(score for _, score in readings))
            return f"{digits[:5]}-{digits[5:]}", confidence
    return None
