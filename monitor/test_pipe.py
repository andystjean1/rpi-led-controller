"""The pipe block from Agent Town: sanitising in web.py, and the rain/conveyor modes drawing from it.

Run: python test_pipe.py (from monitor/; no hardware needed)
"""
import effects
import web


def test_clean_pipe_keeps_known_fields_only():
    pc = web._clean_pc({"overall": "ok", "pipe": [
        {"k": "nba", "st": "late", "run": 1, "ticks": "12", "stored": 5, "picks": -3, "posts": 1, "errors": 0,
         "last": {"id": 1795131001, "stage": "posted", "picks": 2, "err": 0, "note": "C:\\secret"}},
        {"k": "evil", "st": "ok"},
        {"k": "nhl", "st": "weird", "last": {"stage": "exploded"}},
        "junk"]})
    nba, nhl = pc["pipe"]
    assert nba == {"k": "nba", "st": "late", "run": True, "ticks": 12, "stored": 5, "picks": 0, "posts": 1,
                   "errors": 0, "last": {"id": 1795131001, "stage": "posted", "picks": 2, "err": False}}
    assert nhl["st"] == "off" and nhl["last"] is None
    assert "pipe" not in web._clean_pc({"overall": "ok"})  # older Agent Town: no pipe, modes show no_pipe
    assert web._clean_pc({"pipe": "nonsense"})["pipe"] == []


def _ctx(t, state, pipe):
    return {"t": t, "dt": 0.05, "rgb": (255, 255, 255), "speed": 5, "laptops": {}, "state": state,
            "claude": None if pipe is None else {"sessions": [], "pc": {"pipe": pipe}}, "events": []}


def test_modes_draw_and_react():
    row = {"k": "nba", "st": "ok", "run": False, "ticks": 3, "stored": 2, "picks": 0, "posts": 0, "errors": 0,
           "last": {"id": 1, "stage": "skip", "picks": 0, "err": False}}
    for mode in ("rain", "conveyor"):
        assert mode in effects.MODES and mode in web.MODES
        state = {}
        for f in range(40):
            if f == 10:  # a new run that stores and finds picks, then one that fails
                row["last"] = {"id": 2, "stage": "picks", "picks": 2, "err": False}
            if f == 25:
                row["last"] = {"id": 3, "stage": "stored", "picks": 0, "err": True}
            cv = effects.new()
            effects.MODES[mode](cv, _ctx(f * 0.05, state, [dict(row)]))
            assert len(cv) == effects.ROWS and all(len(r) == effects.COLS for r in cv)
            assert all(0 <= v <= 255 for r in cv for px in r for v in px)
        if mode == "conveyor":
            assert state["conveyor"]["packets"]["nba"]["err"]  # jammed
        cv = effects.new()
        effects.MODES[mode](cv, _ctx(1.0, {}, None))  # Agent Town quiet: the faint fallback
        assert any(px != effects.BLACK for r in cv for px in r)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
