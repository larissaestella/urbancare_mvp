from app import demo, overview, seed


def _rows():
    ids = [s[0] for s in seed.build()["stops"]]
    d = demo.build(ids)
    return d, [{"count": v["count"], "board_rate": v["board_rate"], "alert_active": bool(v["over_min"])} for v in d.values()]


def test_demo_hits_render_numbers():
    d, rows = _rows()
    o = overview.compute(rows, extras_today=12)
    assert (o["people"], round(o["avg_wait_min"]), o["stops_in_alert"], o["critical"], o["attention"]) == (1284, 11, 7, 3, 4)
    assert o["stops_total"] == 142 and o["wait_over_goal_min"] == 3
    assert abs(o["avg_wait_min"] - 11) < 0.05


def test_demo_render_stops():
    d, _ = _rows()
    for sid, count, wait in [("SP-0412", 26, 17), ("SP-0071", 24, 15), ("SP-0233", 22, 14), ("SP-0587", 18, 12)]:
        assert d[sid]["count"] == count and round(overview.stop_wait(count, d[sid]["board_rate"])) == wait


def test_only_hot_stops_are_steady_and_fillers_below_attention():
    d, _ = _rows()
    assert sum(v["steady"] for v in d.values()) == 7
    assert all(v["count"] < overview.ATTENTION_MIN for v in d.values() if not v["steady"])
