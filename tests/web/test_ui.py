"""Cut 11: the thin web UI (docs/ui_design.md, testing_contract §8). Rendering details are not tested; what the
server shows, refuses and never does is."""

import ast
import json
import os
import re

import pytest
from fastapi.testclient import TestClient

from elevator import api, reporting
from tests.cpoc import fixture as X
from tests.cpoc import scan
from web import app as web_app

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_SRC = os.path.join(ROOT, "web", "app.py")


def make(tmp_path=None, store=None):
    app = web_app.create_app(store=store)
    return app, TestClient(app)


def new_run(client, policy="cost_based", **extra):
    r = client.post("/runs", data={"policy": policy, **extra})
    assert r.status_code == 200, r.text[:300]
    return re.search(r"/sessions/([0-9a-f-]{36})/", r.text).group(1), r


def engine_of(app, sid):
    return app.state.sessions[sid].engine


def tick_count(app, sid):
    return len(engine_of(app, sid).history.tick_records)


def test_page_loads_and_offers_three_policies():
    app, c = make()
    r = c.get("/")
    assert r.status_code == 200
    for label in ("Round Robin", "Nearest Car", "Cost Based"):
        assert label in r.text
    assert c.get("/evaluate").status_code == 200 and c.get("/static/htmx.min.js").status_code == 200


def test_ui_new_run_creates_engine_not_simulate(monkeypatch, tmp_path):
    """POST /runs yields a RUNNING session at t = 0, writes nothing, and reaches create_engine, never simulate."""
    calls = []
    real = api.create_engine
    monkeypatch.setattr(api, "create_engine", lambda *a, **k: calls.append("create_engine") or real(*a, **k))
    monkeypatch.setattr(api, "simulate", lambda *a, **k: pytest.fail("the web UI must not call simulate"))
    monkeypatch.chdir(tmp_path)
    app, c = make()
    sid, r = new_run(c)
    assert calls == ["create_engine"] and os.listdir(tmp_path) == []
    e = engine_of(app, sid)
    assert (e.t, e.standing, e.outcome) == (0, "RUNNING", None) and len(e.history.tick_records) == 0
    assert "RUNNING" in r.text and sid == e.execution.execution_id


def test_stale_step_executes_nothing_and_final_step_is_a_noop():
    app, c = make()
    sid, _ = new_run(c)
    e = engine_of(app, sid)
    assert c.post(f"/sessions/{sid}/step?from_time=0").status_code == 200 and e.t == 1
    before = (e.t, len(e.history.events), len(e.history.tick_records))
    r = c.post(f"/sessions/{sid}/step?from_time=0")  # a stale page
    assert "Stale page" in r.text and (e.t, len(e.history.events), len(e.history.tick_records)) == before
    r = c.post(f"/sessions/{sid}/step?from_time=5")  # a guard from the future is no selector either
    assert "Stale page" in r.text and e.t == 1
    c.post(f"/sessions/{sid}/finish")
    assert e.outcome is not None
    after = (e.t, len(e.history.events), len(e.history.tick_records), e.standing)
    r = c.post(f"/sessions/{sid}/step?from_time={e.t}")
    assert "final" in r.text and (e.t, len(e.history.events), len(e.history.tick_records), e.standing) == after


def test_history_range_rules():
    app, c = make()
    sid, _ = new_run(c)
    assert c.get(f"/sessions/{sid}/tick/0").status_code == 404 and "NO_HISTORY" in c.get(f"/sessions/{sid}/tick/0").text
    c.post(f"/sessions/{sid}/step?from_time=0")  # t = 1
    r = c.get(f"/sessions/{sid}/tick/1")
    assert r.status_code == 404 and "HISTORY_TICK_NOT_AVAILABLE" in r.text  # the current tick is never rendered
    assert c.get(f"/sessions/{sid}/tick/-1").status_code == 404
    zero = c.get(f"/sessions/{sid}/tick/0")
    assert zero.status_code == 200 and "history" in zero.text
    c.post(f"/sessions/{sid}/step?from_time=1")
    assert c.get(f"/sessions/{sid}/tick/1").status_code == 200 and c.get(f"/sessions/{sid}/tick/0").text == zero.text
    c.post(f"/sessions/{sid}/finish")
    final = engine_of(app, sid).outcome.final_tick
    assert c.get(f"/sessions/{sid}/tick/{final}").status_code == 200
    assert "HISTORY_TICK_NOT_AVAILABLE" in c.get(f"/sessions/{sid}/tick/{final + 1}").text


def halted_session(app, max_ticks):
    engine = api.create_engine(X.trace_rows(), X.N, X.F, X.C, policy="cost_based", max_ticks=max_ticks)
    sid = engine.execution.execution_id
    app.state.sessions[sid] = web_app.Session(engine, engine.run_identity)
    return sid, engine


def test_halted_run_renders_distinctly_and_history_stops_where_it_halted():
    app, c = make()
    sid, e = halted_session(app, 7)
    c.post(f"/sessions/{sid}/finish")
    assert e.standing == "HALTED"
    page = c.get(f"/sessions/{sid}").text
    assert "HALTED" in page and "HORIZON_EXCEEDED" in page and "did not complete" in page
    assert 'class="badge COMPLETED"' not in page and "A halted run reports no wait or total-time metrics" in page
    k = len(e.history.tick_records)
    assert c.get(f"/sessions/{sid}/tick/{k - 1}").status_code == 200
    assert "HISTORY_TICK_NOT_AVAILABLE" in c.get(f"/sessions/{sid}/tick/{k}").text
    # a completed run is labelled as such, not as halted
    sid2, _ = new_run(c)
    c.post(f"/sessions/{sid2}/finish")
    done = c.get(f"/sessions/{sid2}").text
    assert 'class="badge COMPLETED"' in done and "did not complete" not in done


def test_projection_matches_engine_row_29b():
    app, c = make()
    sid, _ = new_run(c)
    e = engine_of(app, sid)
    for _ in range(13):
        c.post(f"/sessions/{sid}/step?from_time={e.t}")
    view = web_app.projection(e)
    assert [(x["id"], x["floor"], x["heading"], x["load"]) for x in view["cars"]] == [
        (el.elevator_id, el.floor, el.heading.value, e.load(el.elevator_id)) for el in e.elevators] and view["t"] == e.t
    page = c.get(f"/sessions/{sid}").text
    for el in e.elevators:  # the rendered SVG carries each car's id, heading and load/capacity
        arrow = {"UP": "▲", "DOWN": "▼", "NONE": "–"}[el.heading.value]
        assert f"{el.elevator_id} {arrow} {e.load(el.elevator_id)}/{X.C}" in page
    waiting = [p for p in e.passengers if p.standing.value == "WAITING"]
    assert len(view["waiting"]) == len(waiting) and waiting
    # history view equals the TickRecord, not the engine
    rec = e.history.tick_records[5]
    hv = web_app.history_view(e, 5)
    assert [(x["id"], x["floor"], x["heading"], x["load"]) for x in hv["cars"]] == [
        (en.elevator_id, en.floor, en.heading.value, en.load) for en in rec.entries]


def test_second_client_sees_the_same_state():
    app, c = make()
    sid, _ = new_run(c)
    c.post(f"/sessions/{sid}/step?from_time=0")
    other = TestClient(app)  # a fresh client with no cookies and no memory of the first
    a, b = c.get(f"/sessions/{sid}").text, other.get(f"/sessions/{sid}").text
    assert a == b and "t = 1" in a
    assert other.get("/sessions/does-not-exist").status_code == 404


def test_browser_cannot_set_simulation_state():
    """No route takes a position, floor, heading, standing or assignment; extra form fields are ignored; a refresh
    (a GET) changes nothing."""
    app, c = make()
    sid, _ = new_run(c)
    e = engine_of(app, sid)
    snapshot = (e.t, e.state, e.history)
    c.post(f"/sessions/{sid}/step?from_time=0&floor=9&heading=UP&standing=COMPLETED", data={"t": "50", "elevator": "1"})
    assert e.t == 1  # exactly one tick; nothing was set
    for path in (f"/sessions/{sid}", f"/sessions/{sid}/compare", f"/sessions/{sid}/why/0", "/evaluate"):
        before = (e.t, e.state, len(e.history.events))
        c.get(path)
        assert (e.t, e.state, len(e.history.events)) == before
    posted = {r.path for r in app.routes if getattr(r, "methods", None) and "POST" in r.methods}
    assert posted == {"/runs", "/sessions", "/sessions/{sid}/step", "/sessions/{sid}/finish",
                      "/sessions/{sid}/checkpoint", "/experiments"}
    fields = {name for route in app.routes if getattr(route, "dependant", None) and "POST" in route.methods
              for name in [p.name for p in route.dependant.query_params + route.dependant.body_params]}
    assert not fields & {"floor", "heading", "standing", "load", "t", "assigned_elevator", "position", "state"}
    assert snapshot[0] == 0


def test_invalid_input_renders_a_refusal_not_a_stack_trace():
    app, c = make()
    for data, reason in (({"source": "paste", "pasted": "0,a,3,3"}, "SAME_FLOOR_REQUEST"),
                         ({"floors": "abc"}, "INVALID_CONFIGURATION"),
                         ({"floors": "1"}, "INVALID_CONFIGURATION"),
                         ({"policy": "magic"}, "INVALID_CONFIGURATION"),
                         ({"source": "paste", "pasted": "0,a,3,99"}, None),
                         ({"source": "paste", "pasted": "x,y"}, None),
                         ({"source": "nowhere"}, "INVALID_INPUT")):
        r = c.post("/runs", data=data)
        assert r.status_code == 400, (data, r.status_code)
        assert 'class="error"' in r.text and "Traceback" not in r.text and "File \"" not in r.text
        if reason:
            assert reason in r.text
    assert not app.state.sessions  # nothing was created


def test_compare_runs_the_three_policies_on_one_trace_and_matches_reporting():
    app, c = make()
    sid, _ = new_run(c, "round_robin")
    r = c.get(f"/sessions/{sid}/compare")
    assert r.status_code == 200
    rows = web_app_rows(r.text)
    assert [row[0] for row in rows] == ["Round Robin", "Nearest Car", "Cost Based"]
    trace_hashes = set()
    for row, policy in zip(rows, web_app.POLICIES):
        e = api.create_engine(X.trace_rows(), X.N, X.F, X.C, policy=policy)
        e.run()
        trace_hashes.add(e.run_identity.trace_hash)
        s = reporting.summary(reporting.RunRecord(e._config, e._trace, e.run_identity, e.history, e.passengers))
        assert row[3:] == [str(s["wait"]["mean"]), str(s["wait"]["p95"]), str(s["wait"]["max"]),
                           str(s["total"]["mean"]), str(s["deferred"]["count"])], policy  # reporting's own values
    assert len(trace_hashes) == 1 and trace_hashes.pop()[:12] in r.text
    assert "not a ranking" in r.text and "winner" not in r.text.lower()
    assert len({row[2] for row in rows}) >= 2  # the policies differ on this demo (final ticks differ)


def web_app_rows(html):
    body = html.split("<table>", 1)[1].split("</table>", 1)[0]
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", body, re.S)[1:]:
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        out.append(cells)
    return out


def test_cost_based_receipt_and_calibration_are_shown_as_committed():
    app, c = make()
    sid, _ = new_run(c)
    c.post(f"/sessions/{sid}/finish")
    e = engine_of(app, sid)
    events = [ev for ev in e.history.events if ev.kind.value == "ASSIGNED"]
    ev = next(x for x in events if len(x.receipt["candidates"]) > 1)
    page = c.get(f"/sessions/{sid}/why/{ev.passenger_id}").text
    assert f"Passenger #{ev.passenger_id}" in page and f"car {ev.elevator_id}" in page
    for cand in ev.receipt["candidates"]:  # every committed candidate value is on the page
        row = re.search(rf"<tr><td>{cand['E']}</td><td>{cand['tier']}</td><td>{cand['wait_c']}</td>"
                        rf"<td>{cand['marginal']}</td><td>{cand['cost']}</td><td>(.*?)</td></tr>", page)
        assert row, cand
        assert ("selected" in row.group(1)) == (cand["E"] == ev.receipt["chosen"])
    assert "not a guarantee" in page
    # calibration: the rows are reporting's, with the definition of the error stated
    full = c.get(f"/sessions/{sid}").text
    assert "error = realized − projected" in full and "not demand forecasting" in full
    cal = reporting.calibration(reporting.RunRecord(e._config, e._trace, e.run_identity, e.history, e.passengers))
    for r in cal[:5]:
        assert (f"<td>{r.passenger_id}</td><td>{r.elevator}</td><td>{r.projected_pickup}</td><td>{r.realized_pickup}</td>"
                f"<td>{r.pickup_error}</td><td>{r.projected_dropoff}</td><td>{r.realized_dropoff}</td><td>{r.dropoff_error}</td>") in full
    # a baseline's run has no calibration section and no fabricated projections
    sid2, _ = new_run(c, "round_robin")
    c.post(f"/sessions/{sid2}/finish")
    assert "Calibration" not in c.get(f"/sessions/{sid2}").text
    assert c.get(f"/sessions/{sid2}/why/0").status_code == 200 and c.get(f"/sessions/{sid2}/why/9999").status_code == 404


def test_results_come_from_the_reporting_layer():
    app, c = make()
    sid, _ = new_run(c)
    c.post(f"/sessions/{sid}/finish")
    e = engine_of(app, sid)
    record = reporting.RunRecord(e._config, e._trace, e.run_identity, e.history, e.passengers)
    s, page = reporting.summary(record), c.get(f"/sessions/{sid}").text
    assert (f"<td>{s['wait']['mean']}</td><td>{s['wait']['median']}</td><td>{s['wait']['p95']}</td><td>{s['wait']['max']}</td>") in page
    assert reporting.observations(record).splitlines()[0] in page.replace("&#39;", "'").replace("&#34;", '"')
    assert "completed 25 of 25" in page


def test_first_checkpoint_flushes_the_log_and_a_session_reopens_by_execution_id(tmp_path):
    from elevator import checkpoint
    store = str(tmp_path / "S")
    checkpoint.init_store(store)
    app, c = make(store=store)
    sid, _ = new_run(c)
    for _ in range(5):
        c.post(f"/sessions/{sid}/step?from_time={engine_of(app, sid).t}")
    assert not os.path.exists(os.path.join(store, sid))  # nothing durable until asked
    r = c.post(f"/sessions/{sid}/checkpoint")
    assert "Checkpoint written at t = 5" in r.text
    log = [json.loads(line) for line in open(os.path.join(store, sid, "operational.jsonl"))]
    assert [(x["op_seq"], x["kind"]) for x in log][:2] == [(1, "EXECUTION_STARTED"), (2, "CHECKPOINT_WRITTEN")]
    # a second server on the same Store lists it and reopens it by execution_id; no file path is accepted
    app2, c2 = make(store=store)
    assert sid in c2.get("/").text
    reopened = c2.post("/sessions", data={"execution_id": sid})
    assert reopened.status_code == 200 and "t = 5" in reopened.text
    assert c2.post("/sessions", data={"execution_id": os.path.join(store, sid)}).status_code == 400
    assert "EXECUTION_NOT_FOUND" in c2.post("/sessions", data={"execution_id": "nope"}).text
    # finishing the reopened session writes finality; the Execution is then final and refuses another reopen
    c2.post(f"/sessions/{sid}/finish")
    app3, c3 = make(store=store)
    refused = c3.post("/sessions", data={"execution_id": sid})
    assert refused.status_code == 400 and "EXECUTION_FINAL" in refused.text
    # a server with no Store refuses to checkpoint or reopen
    app4, c4 = make()
    sid4, _ = new_run(c4)
    assert "NO_STORE" in c4.post(f"/sessions/{sid4}/checkpoint").text and "NO_STORE" in c4.post(
        "/sessions", data={"execution_id": sid}).text


def test_evaluate_page_renders_the_committed_results_and_a_tiny_experiment():
    app, c = make()
    page = c.get("/evaluate").text
    doc = json.load(open(os.path.join(ROOT, "experiments", "default_experiment_results.json")))
    assert doc["experiment_execution_id"][:12] in page and doc["code_identity"][:12] in page
    cost = next(a for a in doc["aggregates"] if "paired_against" in a and a["scenario"] == 0)
    first = cost["paired_against"]["0"]["wait.p95"]
    assert f"<td>{first['better']}</td><td>{first['equal']}</td><td>{first['worse']}</td><td>{first['median']}</td>" in page
    assert "not a claim about real elevator traffic" in page
    tiny = c.post("/experiments", data={"pattern": "bursty", "k": "2"})
    assert tiny.status_code == 200 and "cost_based against round_robin" in tiny.text and "<td>2</td>" in tiny.text
    for bad in ({"k": "0"}, {"k": "11"}, {"k": "x"}, {"pattern": "nope"}, {"floors": "1"}):
        r = c.post("/experiments", data={"pattern": "bursty", "k": "2", **bad})
        assert r.status_code == 400 and 'class="error"' in r.text and "Traceback" not in r.text


# --- structure: the web module is a projection and nothing else ------------------------------------------------------

def web_imports():
    tree = ast.parse(open(WEB_SRC).read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            mods |= {f"{n.module}.{a.name}" for a in n.names} | {n.module}
        elif isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
    return mods


def test_web_depends_only_on_the_admitted_components_and_nothing_imports_web():
    mods = {m for m in web_imports() if m.startswith("elevator")}
    assert mods <= {"elevator", "elevator.api", "elevator.checkpoint", "elevator.harness", "elevator.reporting"}
    assert not [m for m in mods if any(x in m for x in ("domain", "route", "policies", "scenarios", "engine", "cli", "operations"))]
    for name in os.listdir(os.path.join(ROOT, "elevator")):
        if name.endswith(".py"):
            assert not [m for m in scan.imports_of(os.path.join(ROOT, "elevator", name)) if m.split(".")[0] == "web"], name


def test_web_never_calls_simulate_and_implements_no_domain_logic():
    src = open(WEB_SRC).read()
    tree = ast.parse(src)
    called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
              for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "simulate" not in called and "create_engine" in called
    # no route mechanics, no policy cost, no metric arithmetic, no scenario generation, no writes of engine state
    for word in ("departure_direction", "eligible_boarders", "next_heading", "project(", "make_policy", "generate(", "percentile",
                 "nearest_rank", "statistics", "_passengers[", "_elevators =", "_t =", "_events"):
        assert word not in src, word
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Attribute) and isinstance(t.value, ast.Attribute) and t.value.attr in ("engine",)
        for t in n.targets)]
    # the only engine mutation is stepping it
    assert {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == "engine"} <= {"step", "load"}
    assert scan.scan_file(WEB_SRC) == []  # no History-to-state path
    # templates contain no arithmetic on results beyond SVG layout and no script beyond htmx and one slider handler
    templates = "".join(open(os.path.join(ROOT, "web", "templates", n)).read() for n in os.listdir(os.path.join(ROOT, "web", "templates")))
    assert "localStorage" not in templates and "sessionStorage" not in templates and "document.cookie" not in templates
    assert templates.count("<script") == 1  # htmx only; one inline handler on the slider
    assert not re.search(r"\{\{[^}]*(sum\(|/\s*\d|\bmean\()", templates)


# --- audit repairs (C11-I-01, -02, -03 partly, -04) --------------------------------------------------------------------

def test_compare_is_bound_to_the_source_sessions_trace(monkeypatch):
    """C11-I-01. The probe: every comparison run is given a Trace other than the session's. Three runs that agree
    with each other must still be refused, because they disagree with the session."""
    app, c = make()
    sid, _ = new_run(c, "round_robin")
    source = app.state.sessions[sid].identity.trace_hash
    ok = c.get(f"/sessions/{sid}/compare")
    assert ok.status_code == 200 and source[:12] in ok.text and "verified against the session" in ok.text
    real = api.create_engine
    seen = []

    def wrong_trace_for_all(rows, *args, **kwargs):
        seen.append(kwargs.get("policy"))
        return real(rows[:-1], *args, **kwargs)  # one request fewer: the same wrong Trace for all three policies

    monkeypatch.setattr(web_app.api, "create_engine", wrong_trace_for_all)
    wrong = {real(rows, X.N, X.F, X.C).run_identity.trace_hash for rows in [X.trace_rows()[:-1]]}
    assert source not in wrong
    r = c.get(f"/sessions/{sid}/compare")
    assert r.status_code == 409 and "COMPARISON_TRACE_MISMATCH" in r.text and "refused" in r.text
    assert "Each run used this session" not in r.text and "<table>" not in r.text and seen == ["round_robin"]  # stopped at once
    # only one policy on a different Trace is refused too
    def wrong_for_cost(rows, *args, **kwargs):
        return real(rows[:-1] if kwargs.get("policy") == "cost_based" else rows, *args, **kwargs)

    monkeypatch.setattr(web_app.api, "create_engine", wrong_for_cost)
    r = c.get(f"/sessions/{sid}/compare")
    assert r.status_code == 409 and "Cost Based" in r.text and "<table>" not in r.text


def results_copy(tmp_path, mutate):
    doc = json.load(open(os.path.join(ROOT, "experiments", "default_experiment_results.json")))
    mutate(doc)
    path = tmp_path / "results.json"
    path.write_text(json.dumps(doc))
    return str(path)


def test_evaluation_shows_each_metrics_own_n_defined_not_k(tmp_path):
    """C11-I-02: K = 20 seeds, one metric defined for 19 of them: the page says 19 beside that value and 20 as seeds."""
    def mutate(doc):
        doc["aggregates"][0]["metrics"]["wait.mean"]["n_defined"] = 19
    app = web_app.create_app(results_path=results_copy(tmp_path, mutate))
    page = TestClient(app).get("/evaluate").text
    mean = json.load(open(os.path.join(ROOT, "experiments", "default_experiment_results.json")))["aggregates"][0]["metrics"]["wait.mean"]["mean"]
    assert f'{mean} <span class="muted">(n=19)</span>' in page  # the defined count, beside the aggregate
    assert "(n=20)" in page and "<th>seeds (K)</th>" in page and "<td>20</td>" in page  # K is labelled as seeds
    view = web_app.evaluation_view(json.load(open(results_copy(tmp_path, mutate))))
    assert view["scenarios"][0]["rows"][0]["K"] == 20 and view["scenarios"][0]["rows"][0]["values"][0]["n"] == 19


def test_wait_histogram_bars_are_the_reported_wait_times():
    app, c = make()
    sid, _ = new_run(c)
    c.post(f"/sessions/{sid}/finish")
    e = engine_of(app, sid)
    record = reporting.RunRecord(e._config, e._trace, e.run_identity, e.history, e.passengers)
    table = [row.split(",") for row in reporting.reproducible_surface(record)["passengers.csv"].decode().splitlines()]
    waits = [int(r[table[0].index("wait_time")]) for r in table[1:]]
    bars = web_app.histogram(table)
    assert sum(b["count"] for b in bars) == len(waits) == 25 and [b["wait"] for b in bars] == sorted(set(waits))
    assert all(b["count"] == waits.count(b["wait"]) for b in bars)
    page = c.get(f"/sessions/{sid}").text
    assert "wait-time histogram" in page and page.count("<rect") >= len(bars)
    # a halted run draws bars only for the passengers it completed (reporting's wait_time cells), none fabricated
    sid2, e2 = halted_session(app, 7)
    c.post(f"/sessions/{sid2}/finish")
    done = [p for p in e2.passengers if p.standing.value == "COMPLETED"]
    halted_page = c.get(f"/sessions/{sid2}").text
    assert len(done) == 3 and halted_page.split("wait-time histogram", 1)[1].split("</svg>", 1)[0].count("<rect") == len({p.pickup_time - p.request_time for p in done})


def test_evaluation_distribution_visual_uses_the_documents_per_seed_values():
    app, c = make()
    page = c.get("/evaluate").text
    doc = json.load(open(os.path.join(ROOT, "experiments", "default_experiment_results.json")))
    first = [a for a in doc["aggregates"] if a["scenario"] == 0]
    dots = sum(1 for a in first for v in a["metrics"]["wait.p95"]["per_seed"] if v is not None)
    pattern = doc["definition"]["scenarios"][0]["pattern"]
    section = page.split(f"<section><h3>{pattern}</h3>", 1)[1].split("</section>", 1)[0]  # the first pattern's section
    assert section.count("<circle") == dots == 60 and "per-seed p95 wait" in section
    view = web_app.strip_plot([("a", [1, None, 5]), ("b", [3])])
    assert [len(r["xs"]) for r in view["rows"]] == [2, 1] and (view["lo"], view["hi"]) == (1, 5)


def experiment_links(page):
    results = re.search(r'href="(/experiments/[0-9a-f]{64}/experiment_results\.json)"', page).group(1)
    execution = re.search(r'href="(/experiments/[0-9a-f]{64}/executions/[0-9a-f-]{36}/experiment_execution\.json)"', page).group(1)
    return results, execution


def test_fixed_experiment_page_offers_its_committed_result_and_no_invented_metadata():
    app, c = make()
    page = c.get("/evaluate").text
    committed = open(os.path.join(ROOT, "experiments", "default_experiment_results.json"), "rb").read()
    r = c.get("/evaluate/experiment_results.json")
    assert r.status_code == 200 and r.content == committed and "attachment" in r.headers["content-disposition"]
    assert 'href="/evaluate/experiment_results.json"' in page
    # no execution metadata was ever persisted for the committed Experiment: none is offered or fabricated
    assert "experiment_execution.json" not in page.split("Run a small Experiment")[0] and "No execution metadata was persisted" in page
    assert not [f for f in os.listdir(os.path.join(ROOT, "experiments")) if "execution" in f]
    for bad in ("/evaluate/experiment_execution.json", "/evaluate/../pyproject.toml", "/evaluate/%2e%2e/pyproject.toml"):
        assert c.get(bad).status_code in (400, 404, 405), bad


def test_two_executions_of_one_experiment_keep_their_own_metadata():
    """Same logical Experiment, same reproducible result bytes, two Executions: each metadata link keeps returning the
    metadata of the Execution that produced it (C11 re-audit finding)."""
    app, c = make()
    form = {"pattern": "bursty", "k": "2"}
    page_a = c.post("/experiments", data=form).text
    results_a, meta_a = experiment_links(page_a)
    got_a = c.get(meta_a).content
    page_b = c.post("/experiments", data=form).text  # the identical Experiment again: Execution B
    results_b, meta_b = experiment_links(page_b)
    # logical identity and reproducible result bytes are shared; the Execution links are not
    assert results_a == results_b and meta_a != meta_b
    assert c.get(results_a).content == c.get(results_b).content
    assert c.get(meta_a).content == got_a  # A's link still returns A's exact metadata, not B's
    got_b = c.get(meta_b).content
    assert got_a != got_b  # distinct Executions have distinct execution metadata
    doc_a, doc_b = json.loads(got_a), json.loads(got_b)
    ids_a, ids_b = [r["execution_id"] for r in doc_a["runs"]], [r["execution_id"] for r in doc_b["runs"]]
    assert doc_a["experiment_execution_id"] == doc_b["experiment_execution_id"] and doc_a["definition_hash"] == doc_b["definition_hash"]
    assert not set(ids_a) & set(ids_b) and meta_a.split("/")[-2] == ids_a[0] and meta_b.split("/")[-2] == ids_b[0]
    # neither Execution's facts leak into the reproducible result surface
    results = c.get(results_a).content.decode()
    for fact in ids_a + ids_b + ['"pid"', "started_at", "ended_at", "output_path"]:
        assert fact not in results, fact
    # unknown or mismatched keys and path tricks reach nothing
    base = results_a.rsplit("/", 1)[0]
    for bad in (f"{base}/executions/{'0' * 36}/experiment_execution.json", f"{base}/executions/../experiment_execution.json",
                "/experiments/" + "0" * 64 + "/experiment_results.json", f"{base}/experiment_execution.json",
                f"{base}/executions/%2e%2e%2fpyproject.toml/experiment_execution.json", "/experiments/../../etc/passwd"):
        assert c.get(bad).status_code in (400, 404), bad


# --- revision 7.4 (decision 011): the reduced UI contract ----------------------------------------------------------

def test_running_screen_shows_current_state_only_and_the_form_has_no_scenario_controls():
    app, c = make()
    index = c.get("/").text
    assert 'name="seed"' not in index and 'name="scenario"' not in index and 'name="pattern"' not in index
    sid, page = new_run(c)
    for _ in range(6):
        page = c.post(f"/sessions/{sid}/step?from_time={engine_of(app, sid).t}")
    text = page.text
    assert "RUNNING" in text and "t = 6" in text and "Elevators at t = 6" in text and "Waiting" in text and "Onboard" in text
    for final_only in ("<h3>Results</h3>", "Wait times", "Calibration", "<h3>Observations</h3>", "<h3>Passengers</h3>"):
        assert final_only not in text, final_only  # no partial reporting while RUNNING
    assert "stop" not in text.lower()  # no projected or committed stops are drawn
    c.post(f"/sessions/{sid}/finish")
    done = c.get(f"/sessions/{sid}").text
    assert "<h3>Results</h3>" in done and "Wait times" in done and "Calibration" in done  # final-run outputs appear
    for name in ("route", "scenarios", "domain"):
        assert f"elevator.{name}" not in "".join(web_imports())
