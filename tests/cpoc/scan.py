"""The architecture scan for ``no_history_to_state_path_in_package`` (testing_contract §7): import graph, call graph
and annotations. It reads source only; it never imports the code it scans."""

from __future__ import annotations

import ast
import os

STATE_BUILDERS = {"Snapshot", "EngineState", "construct_state"}
STATE_TYPES = ("Snapshot", "EngineState")
HISTORY_TYPES = ("HistoryPrefix", "HistoryVerifier", "SimulationHistory", "TickRecord", "SimulationEvent")
HISTORY_NAMES = {"events", "tick_records", "history", "history_prefix", "verifier"}
#: the only functions that may build a Snapshot, an EngineState or call construct_state (cpoc §5.1)
ALLOWED_BUILDERS = {("checkpoint", "load"), ("checkpoint", "construct_state"), ("checkpoint", "parse_snapshot"),
                    ("engine", "state")}


def _functions(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def scan_file(path: str) -> list[str]:
    """Findings for one module: each is a function that takes history-shaped input and yields state, or that builds
    state outside the allowed constructors."""
    module = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    findings = []
    for fn in _functions(tree):
        params = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs + ([fn.args.vararg] if fn.args.vararg else [])
        annotations = [ast.unparse(a.annotation) for a in params if a.annotation is not None]
        history_in = any(a.arg in HISTORY_NAMES for a in params) or any(
            t in text for text in annotations for t in HISTORY_TYPES)
        returns = ast.unparse(fn.returns) if fn.returns is not None else ""
        calls = {c.func.id if isinstance(c.func, ast.Name) else c.func.attr for c in ast.walk(fn)
                 if isinstance(c, ast.Call) and isinstance(c.func, (ast.Name, ast.Attribute))}
        builds = bool(calls & STATE_BUILDERS)
        if history_in and (any(t in returns for t in STATE_TYPES) or builds):
            findings.append(f"{module}.{fn.name}: takes history-shaped input and yields or builds state")
        if builds and (module, fn.name) not in ALLOWED_BUILDERS:
            findings.append(f"{module}.{fn.name}: builds state outside the allowed constructors")
    return sorted(set(findings))


def scan_package(root: str) -> dict[str, list[str]]:
    out = {}
    for sub in ("elevator", "web"):
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in sorted(files):
                if name.endswith(".py"):
                    found = scan_file(os.path.join(dirpath, name))
                    if found:
                        out[os.path.relpath(os.path.join(dirpath, name), root)] = found
    return out


def imports_of(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            mods.add(n.module or "")
            mods |= {f"{n.module}.{a.name}" for a in n.names}
    return mods
