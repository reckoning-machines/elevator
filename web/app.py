"""The thin demonstration web UI (docs/ui_design.md). The server holds the engines (UI sessions are EPHEMERAL
pointers to live Executions); the browser holds form values and the last fragment it was sent. This module only
calls the application boundaries (``api.create_engine``, ``Engine.step``/``run``, ``reporting``, ``harness``,
``checkpoint`` for an explicit checkpoint and reopen) and formats what they return. It implements no route
mechanics, no policy cost, no metric and no scenario generation, and it never calls the batch ``simulate``."""

from __future__ import annotations

import csv
import functools
import io
import json
import os
from collections import Counter
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from elevator import api, checkpoint, harness, reporting

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_CSV = os.path.join(HERE, "demo_requests.csv")
DEFAULT_RESULTS = os.path.join(os.path.dirname(HERE), "experiments", "default_experiment_results.json")
POLICIES = {"round_robin": "Round Robin", "nearest_car": "Nearest Car", "cost_based": "Cost Based"}
CSV_HEADER = ["time", "id", "source", "dest"]
MAX_K = 10
#: reported summary paths shown in the single-run comparison and the results block (names owned by reporting)
COMPARE_COLUMNS = [("wait.mean", "avg wait"), ("wait.p95", "p95 wait"), ("wait.max", "max wait"),
                   ("total.mean", "avg total"), ("deferred.count", "capacity deferrals")]


class UiRefusal(Exception):
    """An input the UI itself cannot form (not an engine refusal); shown, never a stack trace."""

    def __init__(self, reason: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.reason, self.message, self.status = reason, message, status


@dataclass
class Session:
    """A server-side pointer to one live Execution. Nothing here is authoritative: the engine is."""

    engine: Any
    identity: Any
    writer: Any = None


def rows_from_text(text: str) -> list[list[str]]:
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    return rows[1:] if rows and [c.strip() for c in rows[0]] == CSV_HEADER else rows


def _int(form_value: str, name: str) -> int:
    try:
        return int(form_value)
    except ValueError:
        raise UiRefusal("INVALID_CONFIGURATION", f"{name} must be a whole number") from None


def record_of(session: Session) -> reporting.RunRecord:
    e = session.engine
    return reporting.RunRecord(e._config, e._trace, session.identity, e.history, e.passengers)


def projection(engine: Any) -> dict[str, Any]:
    """The elevator view at the engine's current ``t``, read from engine state (ui §2.2)."""
    cars, waiting = [], []
    for e in engine.elevators:
        onboard = [{"passenger_id": p.passenger_id, "destination": p.destination} for p in engine.passengers
                   if p.standing.value == "ONBOARD" and p.assigned_elevator == e.elevator_id]
        cars.append({"id": e.elevator_id, "floor": e.floor, "heading": e.heading.value, "load": engine.load(e.elevator_id),
                     "onboard": onboard})
    for p in engine.passengers:
        if p.standing.value == "WAITING":
            waiting.append({"passenger_id": p.passenger_id, "floor": p.origin, "destination": p.destination,
                            "elevator": p.assigned_elevator})
    return {"t": engine.t, "floors": engine._config.num_floors, "capacity": engine._config.capacity, "cars": cars,
            "waiting": waiting}


def history_view(engine: Any, k: int) -> dict[str, Any]:
    """The elevator view at recorded tick ``k``, from TickRecords and Simulation Events only (constitution N12)."""
    record = engine.history.tick_records[k]
    events = [e for e in engine.history.events if e.tick == k and e.kind.value in ("ASSIGNED", "BOARDED", "ALIGHTED")]
    return {"t": k, "floors": engine._config.num_floors, "capacity": engine._config.capacity,
            "cars": [{"id": x.elevator_id, "floor": x.floor, "heading": x.heading.value, "load": x.load,
                      "onboard": []} for x in record.entries],
            "waiting": [], "events": [{"kind": e.kind.value, "passenger_id": e.passenger_id, "elevator": e.elevator_id,
                                       "floor": e.floor} for e in events]}


def assignment_receipt(engine: Any, passenger_id: int) -> dict[str, Any] | None:
    """The committed ASSIGNED receipt of one passenger, exactly as recorded (never reconstructed)."""
    for e in engine.history.events:
        if e.kind.value == "ASSIGNED" and e.passenger_id == passenger_id:
            return {"passenger_id": passenger_id, "tick": e.tick, "elevator": e.elevator_id, "receipt": dict(e.receipt or {})}
    return None


def latest_assignment(engine: Any) -> int | None:
    ids = [e.passenger_id for e in engine.history.events if e.kind.value == "ASSIGNED"]
    return ids[-1] if ids else None


def histogram(passengers: list[list[str]]) -> list[dict[str, int]]:
    """Wait-time histogram bars: how many passengers waited each reported number of ticks (the ``wait_time`` cells of
    reporting's passengers table, counted; nothing is derived from simulation state). Layout units only."""
    header, rows = passengers[0], passengers[1:]
    at = header.index("wait_time")
    counts = Counter(int(r[at]) for r in rows if r[at] != "")
    if not counts:
        return []
    top = max(counts.values())
    return [{"wait": w, "count": counts[w], "x": 30 + i * 22, "h": counts[w] * 80 // top, "y": 90 - counts[w] * 80 // top}
            for i, w in enumerate(sorted(counts))]


def strip_plot(series: list[tuple[str, list[int | None]]]) -> dict[str, Any]:
    """Points of per-seed values per policy on a shared axis (layout only: the values are the document's)."""
    values = [v for _, vs in series for v in vs if v is not None]
    if not values:
        return {"rows": [], "lo": None, "hi": None}
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    rows = [{"policy": name, "y": 18 + i * 22, "xs": [30 + (v - lo) * 340 // span for v in vs if v is not None]}
            for i, (name, vs) in enumerate(series)]
    return {"rows": rows, "lo": lo, "hi": hi, "height": 24 + len(series) * 22}


def _table(csv_bytes: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(csv_bytes.decode())))


def create_app(store: str | None = None, results_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Elevator simulation demo")
    app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
    templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))
    sessions: dict[str, Session] = {}
    app.state.sessions, app.state.store = sessions, store
    results_file = results_path or DEFAULT_RESULTS
    downloads: dict[str, dict[str, bytes]] = {}

    def code_identity() -> str:
        """The code identity this process's Executions run under, read from an Execution's own Run identity."""
        with open(DEMO_CSV, newline="", encoding="utf-8") as fh:
            return api.create_engine(rows_from_text(fh.read()), 3, 10, 4).run_identity.code_identity

    def page(request: Request, name: str, status: int = 200, **ctx: Any) -> HTMLResponse:
        return templates.TemplateResponse(request, name, {"policies": POLICIES, **ctx}, status_code=status)

    def store_executions() -> list[str]:
        """Execution ids present in the server's Store (names only: a document is read only by the loader)."""
        if store is None or not os.path.isdir(store):
            return []
        return sorted(n for n in os.listdir(store) if os.path.isfile(os.path.join(store, n, "run.json")))

    def index(request: Request, status: int = 200, error: dict | None = None) -> HTMLResponse:
        return page(request, "index.html", status, error=error, executions=store_executions(), has_store=store is not None)

    def screen_context(sid: str, notice: str = "", playing: bool = False) -> dict[str, Any]:
        s = sessions[sid]
        e = s.engine
        ctx: dict[str, Any] = {"sid": sid, "policy": e._config.policy, "config": e._config, "standing": e.standing,
                               "t": e.t, "notice": notice, "playing": playing and e.outcome is None,
                               "view": projection(e), "outcome": e.outcome, "can_checkpoint": store is not None,
                               "n_history": len(e.history.tick_records), "why": None, "results": None}
        last = latest_assignment(e)
        ctx["why"] = None if last is None else assignment_receipt(e, last)
        if e.outcome is not None:
            record = record_of(s)
            surface = reporting.reproducible_surface(record)
            ctx["results"] = {"summary": reporting.summary(record), "observations": reporting.observations(record),
                              "passengers": _table(surface["passengers.csv"]),
                              "calibration": None}
            ctx["results"]["histogram"] = histogram(ctx["results"]["passengers"])
            if e._config.policy == "cost_based":
                rows = reporting.calibration(record)
                ctx["results"]["calibration"] = {"rows": rows, "summary": reporting.calibration_summary(rows)}
        return ctx

    def screen(request: Request, sid: str, notice: str = "", playing: bool = False, full: bool = False,
               status: int = 200) -> HTMLResponse:
        return page(request, "session.html" if full else "_screen.html", status, **screen_context(sid, notice, playing))

    @app.exception_handler(UiRefusal)
    async def _ui_refusal(request: Request, exc: UiRefusal) -> HTMLResponse:
        return index(request, exc.status, {"reason": exc.reason, "message": exc.message})

    def guarded(fn: Any) -> Any:
        """Show a refusal raised by the application boundaries (api, harness, checkpoint: each carries a named
        ``reason``) as a clean error page. Anything else is a bug and is not hidden."""
        @functools.wraps(fn)
        def run(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except UiRefusal:
                raise
            except Exception as exc:
                reason = getattr(exc, "reason", None)
                if isinstance(reason, str):
                    raise UiRefusal(reason, str(exc)) from exc
                raise
        return run

    def known(sid: str) -> Session:
        if sid not in sessions:
            raise UiRefusal("SESSION_NOT_FOUND", "no such session (sessions that were never checkpointed are lost when "
                                                 "the server restarts)", 404)
        return sessions[sid]

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return index(request)

    @app.post("/runs", response_class=HTMLResponse)
    @guarded
    def new_run(request: Request, policy: str = Form("cost_based"), floors: str = Form("10"),
                elevators: str = Form("3"), capacity: str = Form("4"), source: str = Form("demo"),
                pasted: str = Form("")) -> HTMLResponse:
        """Create a session with ``create_engine`` (the engine is RUNNING at t = 0; nothing is written)."""
        if policy not in POLICIES:
            raise UiRefusal("INVALID_CONFIGURATION", f"unknown policy {policy!r}")
        if source == "demo":
            with open(DEMO_CSV, newline="", encoding="utf-8") as fh:
                rows = rows_from_text(fh.read())
        elif source == "paste":
            rows = rows_from_text(pasted)
        else:
            raise UiRefusal("INVALID_INPUT", "choose the built-in example or paste requests")
        engine = api.create_engine(rows, _int(elevators, "elevators"), _int(floors, "floors"), _int(capacity, "capacity"),
                                   policy=policy)
        sid = engine.execution.execution_id
        sessions[sid] = Session(engine, engine.run_identity)
        return screen(request, sid, full=True)

    @app.post("/sessions", response_class=HTMLResponse)
    @guarded
    def reopen(request: Request, execution_id: str = Form(...)) -> HTMLResponse:
        """Reopen an Execution by its id from the server's Store, through the loader; its refusals are shown verbatim."""
        if store is None:
            raise UiRefusal("NO_STORE", "this server has no Store configured")
        if execution_id not in sessions:
            resumed = checkpoint.resume(store, execution_id)
            sessions[execution_id] = Session(resumed.engine, resumed.loaded.identity, resumed.writer)
        return screen(request, execution_id, full=True)

    @app.get("/sessions/{sid}", response_class=HTMLResponse)
    def show(request: Request, sid: str) -> HTMLResponse:
        known(sid)
        return screen(request, sid, full=True)

    def finalize_if_done(s: Session) -> None:
        if s.engine.outcome is not None and s.writer is not None and s.writer.has_document:
            s.writer.finalize(s.engine)

    @app.post("/sessions/{sid}/step", response_class=HTMLResponse)
    @guarded
    def step(request: Request, sid: str, from_time: int, play: int = 0) -> HTMLResponse:
        """Execute exactly one tick if the engine's ``t`` equals ``from_time`` and the run is RUNNING. The guard is a
        copy of what the page last showed; the server's ``t`` decides."""
        s = known(sid)
        if s.engine.outcome is not None:
            return screen(request, sid, "The run is final; nothing was executed.")
        if from_time != s.engine.t:
            return screen(request, sid, "Stale page: the server is at a different tick; nothing was executed.")
        s.engine.step()
        finalize_if_done(s)
        return screen(request, sid, playing=bool(play))

    @app.post("/sessions/{sid}/finish", response_class=HTMLResponse)
    @guarded
    def finish(request: Request, sid: str) -> HTMLResponse:
        """Run the session's engine to its Run outcome (the same ``step`` the button uses, repeated server-side)."""
        s = known(sid)
        while s.engine.outcome is None:
            s.engine.step()
        finalize_if_done(s)
        return screen(request, sid)

    @app.post("/sessions/{sid}/checkpoint", response_class=HTMLResponse)
    @guarded
    def explicit_checkpoint(request: Request, sid: str) -> HTMLResponse:
        s = known(sid)
        if store is None:
            raise UiRefusal("NO_STORE", "this server has no Store configured", 400)
        if s.engine.outcome is not None:
            return screen(request, sid, "The run is final; no checkpoint was written.")
        if s.writer is None:
            e = s.engine
            checkpoint.bind_store(store, e.execution)  # first checkpoint: binds the log and flushes it once
            s.writer = checkpoint.CheckpointWriter(store, e.execution, s.identity, e._config, e._trace)
        receipt = s.writer.checkpoint(s.engine)
        return screen(request, sid, f"Checkpoint written at t = {s.engine.t} (write_sequence {receipt.write_sequence}).")

    @app.get("/sessions/{sid}/tick/{k}", response_class=HTMLResponse)
    def tick(request: Request, sid: str, k: int) -> HTMLResponse:
        e = known(sid).engine
        n = len(e.history.tick_records)
        if n == 0:
            return page(request, "_refused.html", 404, code="NO_HISTORY", message="No tick has been recorded yet.")
        if not 0 <= k < n:
            return page(request, "_refused.html", 404, code="HISTORY_TICK_NOT_AVAILABLE",
                        message=f"Recorded ticks are 0 to {n - 1}; tick {k} is not available.")
        return page(request, "_tick.html", 200, sid=sid, view=history_view(e, k), k=k, n=n)

    @app.get("/sessions/{sid}/why/{passenger_id}", response_class=HTMLResponse)
    def why(request: Request, sid: str, passenger_id: int) -> HTMLResponse:
        found = assignment_receipt(known(sid).engine, passenger_id)
        if found is None:
            return page(request, "_refused.html", 404, code="NO_ASSIGNMENT", message="That passenger has no assignment yet.")
        return page(request, "_why.html", 200, why=found)

    @app.get("/sessions/{sid}/compare", response_class=HTMLResponse)
    @guarded
    def compare(request: Request, sid: str) -> HTMLResponse:
        """The same Trace under the three policies (three engines built with ``create_engine`` and run server-side)."""
        s = known(sid)
        cfg, trace = s.engine._config, s.engine._trace
        source_hash = s.identity.trace_hash  # the source session's Trace is the comparison authority
        rows = []
        for name, label in POLICIES.items():
            engine = api.create_engine(trace.canonical_rows(), cfg.num_elevators, cfg.num_floors, cfg.capacity,
                                       policy=name, initial_floors=list(cfg.initial_floors))
            got = engine.run_identity.trace_hash
            if got != source_hash:
                return page(request, "_refused.html", 409, code="COMPARISON_TRACE_MISMATCH",
                            message=f"{label} would run trace {got[:12]}, but this session's trace is {source_hash[:12]}; "
                                    "the comparison is refused.")
            outcome = engine.run()
            summary = reporting.summary(reporting.RunRecord(engine._config, engine._trace, engine.run_identity,
                                                            engine.history, engine.passengers))
            rows.append({"policy": name, "label": label, "standing": outcome.standing, "final_tick": outcome.final_tick,
                         "halt_reason": outcome.halt_reason, "trace_hash": got,
                         "cells": [reporting_path(summary, p) for p, _ in COMPARE_COLUMNS]})
        return page(request, "_compare.html", 200, rows=rows, columns=[c for _, c in COMPARE_COLUMNS],
                    trace_hash=source_hash)

    def evaluation(request: Request, doc: dict, source: str, error: dict | None = None,
                   download_id: str | None = None, execution_key: str | None = None) -> HTMLResponse:
        if download_id:
            links = [("experiment_results.json", f"/experiments/{download_id}/experiment_results.json"),
                     ("experiment_execution.json (this execution)",
                      f"/experiments/{download_id}/executions/{execution_key}/experiment_execution.json")]
            note = None
        else:
            links = [("experiment_results.json", "/evaluate/experiment_results.json")]
            note = ("No execution metadata was persisted for the committed Experiment (the committed evidence holds the "
                    "reproducible result surface only), so none is offered; a live Experiment below offers its own.")
        return page(request, "evaluate.html", 200, view=evaluation_view(doc), source=source, error=error, max_k=MAX_K,
                    patterns=sorted({s["pattern"] for s in doc["definition"]["scenarios"]}), downloads=links,
                    download_note=note)

    def served(content: bytes, name: str) -> Response:
        return Response(content, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.get("/evaluate/experiment_results.json")
    def committed_results() -> Response:
        """The already-produced result surface of the fixed Experiment (the configured file's bytes, unchanged)."""
        with open(results_file, "rb") as fh:
            return served(fh.read(), "experiment_results.json")

    @app.get("/experiments/{experiment_id}/experiment_results.json")
    def experiment_results(experiment_id: str) -> Response:
        """The reproducible result bytes produced by a live Experiment of this server (looked up by id in memory)."""
        entry = downloads.get(experiment_id)
        if entry is None:
            raise UiRefusal("NOT_FOUND", "no such experiment result", 404)
        return served(entry["results"], "experiment_results.json")

    @app.get("/experiments/{experiment_id}/executions/{execution_key}/experiment_execution.json")
    def experiment_execution(experiment_id: str, execution_key: str) -> Response:
        """The execution metadata of one specific Execution: another Execution of the same Experiment has its own key."""
        entry = downloads.get(experiment_id)
        if entry is None or execution_key not in entry["executions"]:
            raise UiRefusal("NOT_FOUND", "no such experiment execution", 404)
        return served(entry["executions"][execution_key], "experiment_execution.json")

    @app.get("/evaluate", response_class=HTMLResponse)
    def evaluate(request: Request) -> HTMLResponse:
        with open(results_file, encoding="utf-8") as fh:
            return evaluation(request, json.load(fh), "the committed experiment_results.json (the fixed Experiment)")

    @app.post("/experiments", response_class=HTMLResponse)
    @guarded
    def experiments(request: Request, pattern: str = Form("bursty"), k: str = Form("3"), floors: str = Form("20"),
                    elevators: str = Form("4"), capacity: str = Form("8")) -> HTMLResponse:
        """A small Experiment through the harness, synchronously, with a bounded K. The pattern's parameters are
        those of the fixed Experiment's definition (decision 010), the building is the form's."""
        with open(results_file, encoding="utf-8") as fh:
            fixed = {sc["pattern"]: sc["parameters"] for sc in json.load(fh)["definition"]["scenarios"]}
        if pattern not in fixed:
            raise UiRefusal("INVALID_SCENARIO_PARAMETERS", f"unknown pattern {pattern!r}")
        count = _int(k, "seeds")
        if not 1 <= count <= MAX_K:
            raise UiRefusal("INVALID_CONFIGURATION", f"seeds must be between 1 and {MAX_K}")
        definition = harness.ExperimentDefinition.create(_int(floors, "floors"), _int(elevators, "elevators"),
                                                         _int(capacity, "capacity"), [(pattern, dict(fixed[pattern]))],
                                                         seeds=list(range(count)))
        executed = harness.execute_experiment(definition, code_identity(), run_executor)
        produced = executed.results_bytes()  # produced once, here; the download route only serves these bytes
        # The result surface is logical: repeated executions of one Experiment may produce identical bytes, so it is
        # keyed by the logical Experiment id. The execution metadata is execution-specific: it is keyed, immutably, by
        # the random execution_id of this execution's first Run, so a later execution never replaces it.
        logical = executed.experiment_execution_id
        execution_key = executed.run_facts[0]["execution_id"]
        entry = downloads.setdefault(logical, {"results": produced, "executions": {}})
        entry["executions"][execution_key] = executed.execution_metadata_bytes(pid=os.getpid())
        return evaluation(request, json.loads(produced), f"a live Experiment of {count} seed(s)",
                          download_id=logical, execution_key=execution_key)

    return app


def reporting_path(summary: dict, path: str) -> Any:
    """Read one reported value by its dotted path (a lookup, not a calculation)."""
    return harness.reported(summary, path)


def run_executor(trace: Any, configuration: Any, output_dir: str | None) -> harness.RunExecution:
    """The Experiment's Run executor for the web: a Run is ``create_engine`` then ``run`` (never ``simulate``)."""
    engine = api.create_engine(trace.canonical_rows(), configuration.num_elevators, configuration.num_floors,
                               configuration.capacity, policy=configuration.policy,
                               policy_params=dict(configuration.policy_params),
                               initial_floors=list(configuration.initial_floors))
    outcome = engine.run()
    summary = reporting.summary(reporting.RunRecord(engine._config, engine._trace, engine.run_identity, engine.history,
                                                    engine.passengers))
    identity = engine.run_identity
    return harness.RunExecution(identity.run_id, identity.trace_hash, outcome.standing, outcome.final_tick,
                                outcome.halt_reason, summary, engine.execution.execution_id, None)


def evaluation_view(doc: dict) -> dict[str, Any]:
    """Arrange a results document (the reproducible Experiment surface) for display; every number is the document's."""
    policies = [p["name"] for p in doc["definition"]["policies"]]
    shown = ["wait.mean", "wait.p95", "total.mean", "total.p95", "makespan"]
    paired_shown = ["wait.p95", "total.mean"]
    scenarios = []
    for s, scenario in enumerate(doc["definition"]["scenarios"]):
        cells = [a for a in doc["aggregates"] if a["scenario"] == s]
        rows = [{"policy": policies[a["policy"]], "halted": a["halted_count"], "K": a["K"],
                 "values": [{"mean": a["metrics"][m]["mean"], "n": a["metrics"][m]["n_defined"]} for m in shown]}
                for a in cells]
        strip = strip_plot([(policies[a["policy"]], list(a["metrics"]["wait.p95"]["per_seed"])) for a in cells])
        paired = []
        for a in cells:
            for baseline, pc in a.get("paired_against", {}).items():
                paired.append({"baseline": policies[int(baseline)],
                               "cells": [{"metric": m, **pc[m]} for m in paired_shown]})
        scenarios.append({"pattern": scenario["pattern"], "rows": rows, "paired": paired, "strip": strip})
    return {"scenarios": scenarios, "shown": shown, "paired_shown": paired_shown, "code_identity": doc["code_identity"],
            "definition_hash": doc["definition_hash"], "experiment_execution_id": doc["experiment_execution_id"],
            "building": doc["definition"]["configuration"], "seeds": len(doc["definition"]["seeds"])}
