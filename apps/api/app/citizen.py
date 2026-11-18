"""Cadastro cidadão: guarda só o endereço confirmado pelo usuário e o liga aos pontos UrbanFlow da mesma via."""
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .address_extraction import BRAZILIAN_STATES

MAX_NEARBY = 3
MAX_ADDRESSES = 10  # por titular: casa, trabalho, escola… e um teto contra abuso
FIELDS = ("issuer", "street", "number", "complement", "neighborhood", "city", "state", "postal_code")
VISITOR_PATTERN = r"^[A-Za-z0-9-]{8,64}$"
STREET_TYPES = {
    "AV": "AV", "AVENIDA": "AV", "R": "R", "RUA": "R", "AL": "AL", "ALAMEDA": "AL",
    "TV": "TV", "TRAVESSA": "TV", "EST": "EST", "ESTRADA": "EST", "ROD": "ROD", "RODOVIA": "ROD",
    "PC": "PC", "PCA": "PC", "PRACA": "PC",
}
def _text(max_length: int, min_length: int = 1):
    return Field(min_length=min_length, max_length=max_length)


class CitizenAddressIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    consent: Literal[True]
    issuer: Literal["ENEL", "VIVO", "CLARO"]
    street: str = _text(120, 3)
    number: str = Field(min_length=1, max_length=10, pattern=r"^(?:[0-9]+[A-Za-z]?|S/?N)$")
    complement: str = _text(80, 0)
    neighborhood: str = _text(80, 2)
    city: str = _text(80, 2)
    state: str
    postal_code: str = Field(pattern=r"^[0-9]{5}-?[0-9]{3}$")

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        value = value.upper()
        if value not in BRAZILIAN_STATES:
            raise ValueError("UF inválida")
        return value

    @field_validator("postal_code")
    @classmethod
    def format_postal_code(cls, value: str) -> str:
        digits = value.replace("-", "")
        return f"{digits[:5]}-{digits[5:]}"


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char)).upper()
    return re.sub(r"[^A-Z0-9 ]+", " ", text)


def street_key(street: str) -> str:
    """Normaliza 'Avenida Paulista' e 'Av. Paulista' para a mesma chave; o tipo da via é opcional."""
    words = _plain(street).split()
    if words and words[0] in STREET_TYPES:
        words = words[1:]
    return " ".join(words)


def _split_stop_name(name: str) -> tuple[str, int | None]:
    street, _, number = name.partition(",")
    match = re.match(r"\s*([0-9]+)", number)
    return street, int(match[1]) if match else None


def nearby_stops(street: str, number: str, stops: list[dict]) -> list[dict]:
    """Pontos na mesma via, do número mais próximo ao mais distante."""
    key = street_key(street)
    if not key:
        return []
    home = int(match[0]) if (match := re.match(r"[0-9]+", number)) else None
    found = []
    for stop in stops:
        stop_street, stop_number = _split_stop_name(stop["name"])
        if street_key(stop_street) != key:
            continue
        distance = (
            abs(stop_number - home) if home is not None and stop_number is not None else None
        )
        found.append((distance is None, distance or 0, stop["id"], stop))
    found.sort(key=lambda item: item[:3])
    return [stop for *_, stop in found[:MAX_NEARBY]]
