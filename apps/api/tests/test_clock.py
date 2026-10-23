from datetime import datetime, timedelta, timezone

from app.clock import DEMO_START, SimClock


class FakeWall:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_clock_runs_at_multiplier():
    w = FakeWall()
    c = SimClock(wall=w, mult=1.0)
    c.set_multiplier(30)
    w.t += 10
    assert c.now() == DEMO_START + timedelta(seconds=300)


def test_multiplier_change_does_not_jump():
    w = FakeWall()
    c = SimClock(wall=w, mult=1.0)
    w.t += 60
    before = c.now()
    c.set_multiplier(30)
    assert c.now() == before


def test_pause_and_resume():
    w = FakeWall()
    c = SimClock(wall=w, mult=10)
    w.t += 5
    c.pause()
    frozen = c.now()
    w.t += 100
    assert c.now() == frozen
    c.resume()
    w.t += 1
    assert c.now() == frozen + timedelta(seconds=10)


def test_multiplier_limits():
    c = SimClock(wall=FakeWall())
    for bad in (0, -1, 31):
        try:
            c.set_multiplier(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_jump():
    w = FakeWall()
    c = SimClock(wall=w)
    to = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    c.jump(to)
    assert c.now() == to


def test_resume_on_running_clock_does_not_rewind():
    w = FakeWall()
    c = SimClock(wall=w, mult=10)
    w.t += 60
    before = c.now()
    c.resume()
    assert c.now() == before


def test_jump_normalizes_to_brt():
    from app.clock import BRT
    c = SimClock(wall=FakeWall())
    c.jump(datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc))
    assert c.now().hour == 8 and c.now().tzinfo == BRT
