from datetime import datetime, timedelta, timezone

from app.dispatch import A_CAMINHO, CHEGOU, ETA_MIN, arrival_time, next_status

T0 = datetime(2026, 8, 31, 18, 42, tzinfo=timezone.utc)


def test_arrival_after_eta_in_sim_time():
    arrive = arrival_time(T0)
    assert arrive == T0 + timedelta(minutes=ETA_MIN)
    assert next_status(A_CAMINHO, arrive, arrive - timedelta(seconds=1)) == A_CAMINHO
    assert next_status(A_CAMINHO, arrive, arrive) == CHEGOU


def test_arrived_stays_arrived():
    assert next_status(CHEGOU, T0, T0 + timedelta(hours=1)) == CHEGOU
