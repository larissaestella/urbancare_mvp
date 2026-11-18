"""Fórmulas dos KPIs da Visão geral. O seed Demo é calibrado contra esta mesma função."""
from datetime import date

META_WAIT_MIN = 8
ATTENTION_MIN = 15  # faixa de atenção: 15..20 sem alerta aberto


def stop_wait(count: int, board_rate: float) -> float:
    return count / board_rate


def status(count: int, alert_active: bool) -> str:
    return "critico" if alert_active else "atencao" if count >= ATTENTION_MIN else "normal"


def compute(rows: list[dict], extras_today: int, avg_hour: int | None = None) -> dict:
    """rows: count, board_rate, alert_active por ponto. Espera média = média ponderada pela lotação.
    avg_hour: média de 4 semanas para a hora atual (vs_avg_pct = lotação agora contra ela)."""
    people = sum(r["count"] for r in rows)
    avg_wait = sum(r["count"] * stop_wait(r["count"], r["board_rate"]) for r in rows) / people if people else 0.0
    critical = sum(1 for r in rows if r["alert_active"])
    attention = sum(1 for r in rows if not r["alert_active"] and r["count"] >= ATTENTION_MIN)
    return {"people": people, "avg_wait_min": round(avg_wait, 1), "wait_over_goal_min": round(avg_wait) - META_WAIT_MIN,
            "goal_wait_min": META_WAIT_MIN, "stops_total": len(rows), "stops_in_alert": critical + attention,
            "critical": critical, "attention": attention, "extras_today": extras_today,
            "vs_avg_pct": round((people / avg_hour - 1) * 100) if avg_hour else None}
