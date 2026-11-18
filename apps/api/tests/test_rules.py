from datetime import datetime, timedelta, timezone

from app.rules import StopState, evaluate

T0 = datetime(2026, 8, 31, 18, 42, tzinfo=timezone.utc)


def feed(state, readings):
    events = []
    for secs, count in readings:
        state, ev = evaluate(state, count, T0 + timedelta(seconds=secs))
        events.append(ev)
    return state, events


def test_fires_at_exactly_five_minutes_not_before():
    _, ev = feed(StopState(), [(s, 26) for s in range(0, 301, 30)])
    assert ev[:10] == [None] * 10       # 0..270 s
    assert ev[10] == "open"             # 300 s
    _, ev299 = feed(StopState(), [(0, 26), (299, 26)])
    assert ev299 == [None, None]


def test_does_not_double_fire():
    _, ev = feed(StopState(), [(s, 26) for s in range(0, 601, 30)])
    assert ev.count("open") == 1


def test_resets_when_count_drops_to_threshold():
    state, ev = feed(StopState(), [(0, 26), (240, 26), (270, 20), (300, 26), (540, 26)])
    assert "open" not in ev             # recomeça a contagem em 300 s
    _, ev2 = feed(state, [(570, 26), (599, 26), (600, 26)])
    assert ev2 == [None, None, "open"]  # 300 s depois do novo início


def test_closes_when_count_falls():
    state, ev = feed(StopState(), [(s, 26) for s in range(0, 301, 30)] + [(330, 10)])
    assert ev[-1] == "close" and not state.alert_active


def test_out_of_order_reading_ignored():
    state, _ = feed(StopState(), [(60, 26)])
    same, ev = evaluate(state, 5, T0)
    assert ev is None and same == state
