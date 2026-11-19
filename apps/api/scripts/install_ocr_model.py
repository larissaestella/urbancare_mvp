import argparse
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
from urllib.request import urlopen


MODEL_URL = "https://registry.npmjs.org/@tesseract.js-data/por/-/por-1.0.0.tgz"
ARCHIVE_SHA256 = "e9d54a379afab14fbd18530fc6a6e6cc8f7c0be2799c74be854eda920aabddac"
MODEL_SHA256 = "016c6a371bb1e4c48fe521908cf3ba3d751fade0ab846ad5d4086b563f5c528c"
MODEL_MEMBER = "package/4.0.0/por.traineddata.gz"


def install(destination: Path) -> None:
    target = destination / "por.traineddata"
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == MODEL_SHA256:
        return
    with urlopen(MODEL_URL, timeout=60) as response:
        archive_bytes = response.read(12 * 1024 * 1024 + 1)
    if hashlib.sha256(archive_bytes).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("O pacote do modelo OCR não corresponde ao checksum esperado.")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        with archive.extractfile(MODEL_MEMBER) as compressed:
            model = gzip.decompress(compressed.read())
    if hashlib.sha256(model).hexdigest() != MODEL_SHA256:
        raise ValueError("O modelo OCR não corresponde ao checksum esperado.")
    destination.mkdir(parents=True, exist_ok=True)
    target.write_bytes(model)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instala dados OCR precisos com versão e checksums fixos.")
    parser.add_argument(
        "--output", type=Path,
        default=Path.home() / ".cache/urbancare/tessdata-best",
    )
    install(parser.parse_args().output)
