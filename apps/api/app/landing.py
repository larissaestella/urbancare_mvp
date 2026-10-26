"""Landing B2B do smoke test (docx Sprint 2): A/B do CTA, formulário de 3 campos e métricas de conversão."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

GOAL_CTR = 0.15  # conversão no CTA: >= 15% dos visitantes
GOAL_LEADS = 3   # >= 3 cadastros completos em 7 dias
FREE_DOMAINS = {"gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com", "msn.com", "yahoo.com",
                "yahoo.com.br", "icloud.com", "bol.com.br", "uol.com.br", "terra.com.br", "ig.com.br", "proton.me"}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Variant = Literal["A", "B"]
Visitor = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visitor: str = Visitor
    variant: Variant
    kind: Literal["visit", "click"]


class LeadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visitor: str = Visitor
    variant: Variant
    company: str = Field(min_length=2, max_length=120)
    size: int = Field(gt=0, le=100_000)
    email: str = Field(max_length=254)

    @field_validator("company")
    @classmethod
    def strip(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("informe a empresa")
        return v.strip()

    @field_validator("email")
    @classmethod
    def corporate(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL.match(v):
            raise ValueError("e-mail inválido")
        if v.rsplit("@", 1)[1] in FREE_DOMAINS:
            raise ValueError("use o e-mail corporativo")
        return v


def metrics(rows: list[dict]) -> dict:
    """rows: (variant, visits, clicks, leads). Conversão = cliques ÷ visitas (definição do docx)."""
    by = {v: {"visits": 0, "clicks": 0, "leads": 0} for v in ("A", "B")}
    for r in rows:
        by[r["variant"]] = {k: r[k] for k in ("visits", "clicks", "leads")}
    total = {k: by["A"][k] + by["B"][k] for k in ("visits", "clicks", "leads")}
    for m in (*by.values(), total):
        m["ctr"] = m["clicks"] / m["visits"] if m["visits"] else None
    return {"A": by["A"], "B": by["B"], "total": total, "goal_ctr": GOAL_CTR, "goal_leads": GOAL_LEADS}
