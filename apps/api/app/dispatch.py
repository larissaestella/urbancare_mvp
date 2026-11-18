"""Ciclo do despacho em tempo de simulação: a_caminho -> chegou."""
from datetime import datetime, timedelta

ETA_MIN = 9      # Garagem Vila Mariana, como no render
BOARDS = 25      # pessoas que o extra leva ao chegar

A_CAMINHO = "a_caminho"
CHEGOU = "chegou"


def arrival_time(created_at: datetime, eta_min: int = ETA_MIN) -> datetime:
    return created_at + timedelta(minutes=eta_min)


def next_status(status: str, arrive_at: datetime, sim_now: datetime) -> str:
    if status == A_CAMINHO and sim_now >= arrive_at:
        return CHEGOU
    return status
