"""Relógio de simulação: sim_now = âncora_sim + (relógio_parede - âncora_parede) x multiplicador."""
import time
from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))
DEMO_START = datetime(2026, 8, 31, 18, 42, tzinfo=BRT)  # "Seg 18:42"
MAX_MULT = 30.0


class SimClock:
    def __init__(self, start=DEMO_START, mult=1.0, paused=False, wall=time.monotonic):
        self._wall = wall
        self._anchor_sim = start
        self._anchor_wall = wall()
        self._mult = mult
        self._paused = paused

    def now(self) -> datetime:
        if self._paused:
            return self._anchor_sim
        elapsed = (self._wall() - self._anchor_wall) * self._mult
        return self._anchor_sim + timedelta(seconds=elapsed)

    def _reanchor(self) -> None:
        self._anchor_sim = self.now()
        self._anchor_wall = self._wall()

    def set_multiplier(self, mult: float) -> None:
        if not 0 < mult <= MAX_MULT:
            raise ValueError(f"multiplicador deve estar em (0, {MAX_MULT}]")
        self._reanchor()
        self._mult = mult

    def pause(self) -> None:
        self._reanchor()
        self._paused = True

    def resume(self) -> None:
        if not self._paused:
            return
        self._anchor_wall = self._wall()
        self._paused = False

    def jump(self, to: datetime) -> None:
        self._anchor_sim = to.astimezone(BRT)
        self._anchor_wall = self._wall()

    def snapshot(self) -> dict:
        return {"sim_now": self.now().isoformat(), "multiplier": self._mult, "paused": self._paused}
