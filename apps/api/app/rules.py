"""Regra de alerta: lotação > 20 por mais de 5 min, medida em tempo de simulação (ts da leitura)."""
from dataclasses import dataclass
from datetime import datetime, timedelta

THRESHOLD = 20
HOLD = timedelta(minutes=5)


@dataclass(frozen=True)
class StopState:
    last_ts: datetime | None = None
    over_since: datetime | None = None
    alert_active: bool = False


def evaluate(state: StopState, count: int, ts: datetime) -> tuple[StopState, str | None]:
    """Devolve (novo estado, evento) com evento em {"open", "close", None}."""
    if state.last_ts is not None and ts <= state.last_ts:
        return state, None  # leitura repetida ou fora de ordem
    if count > THRESHOLD:
        over_since = state.over_since or ts
        if not state.alert_active and ts - over_since >= HOLD:
            return StopState(ts, over_since, True), "open"
        return StopState(ts, over_since, state.alert_active), None
    if state.alert_active:
        return StopState(ts, None, False), "close"
    return StopState(ts, None, False), None
