import cv2
import numpy as np
import pytest

from app.refinement import read_postal_code


@pytest.mark.parametrize(
    ("readings", "expected"),
    [
        ([("01234-560", 94), ("01234560", 79)], "01234-560"),
        ([("01234-560", 94), ("01234-568", 90)], None),
        ([("01234-560", 40), ("01234-560", 55)], None),
    ],
)
def test_postal_code_reread_requires_two_agreeing_numeric_reads(
    monkeypatch, readings, expected
):
    image = np.full((110, 1100), 255, dtype=np.uint8)
    cv2.putText(
        image, "01234-56O CIDADE MODELO SP", (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2, cv2.LINE_AA,
    )
    responses = iter([
        {
            "text": ["01234-56O"], "left": [20], "top": [15],
            "width": [300], "height": [50],
        },
        *[{"text": [text], "conf": [confidence]} for text, confidence in readings],
    ])
    monkeypatch.setattr(
        "app.refinement.pytesseract.image_to_data",
        lambda *args, **kwargs: next(responses),
    )

    result = read_postal_code(image)

    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert result[0] == expected
