"""Cut 12: the public documents. Their commands run as written, their links resolve, their numbers equal the
committed evidence, and their text follows the owner's style rules (plain keyboard characters, no marketing words)."""

import csv
import glob
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

from elevator import api

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLIC = ["README.md", "docs/design.md", "docs/walkthrough.md", "docs/README.md"]


def text(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def test_readme_simulate_command_runs_and_matches_the_source_facing_function(tmp_path):
    cmd = [sys.executable, "-B", "-m", "elevator.cli", "simulate", "--requests", "examples/requests.csv", "--floors", "10",
           "--elevators", "3", "--capacity", "4", "--policy", "cost_based", "--out", str(tmp_path / "runs")]
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    fields = dict(line.split(": ", 1) for line in done.stdout.splitlines() if ": " in line)
    out = fields["output"]
    for name in ("elevator_positions.csv", "summary.json", "observations.md", "passengers.csv", "events.jsonl"):
        assert os.path.getsize(os.path.join(out, name)) > 0, name
    with open(os.path.join(ROOT, "examples", "requests.csv"), newline="") as fh:
        rows = list(csv.reader(fh))[1:]
    result = api.simulate(rows, num_elevators=3, num_floors=10, capacity=4, policy="cost_based")  # the README's snippet
    assert result.run_id == fields["run_id"] and result.final_tick == int(fields["final_tick"]) == 31
    with open(os.path.join(out, "elevator_positions.csv"), "rb") as fh:
        assert fh.read() == result.surface["elevator_positions.csv"]
    first = open(os.path.join(out, "elevator_positions.csv")).read().splitlines()
    assert first[0] == "t,elevator_0,elevator_1,elevator_2" and len(first) == 1 + 32  # a header and one row per tick, 0 to 31


def test_readme_web_command_serves_the_demo():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = subprocess.Popen([sys.executable, "-B", "-m", "web", "--port", str(port)], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        body = None
        for _ in range(100):
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read().decode()
                break
            except OSError:
                time.sleep(0.1)
        assert body is not None and "Elevator simulation" in body and "Cost Based" in body
    finally:
        server.terminate()
        server.wait(timeout=10)


def test_every_relative_link_resolves():
    for doc in PUBLIC:
        base = os.path.dirname(os.path.join(ROOT, doc))
        for target in re.findall(r"\]\(([^)\s]+)\)", text(doc)):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = os.path.normpath(os.path.join(base, target.split("#")[0]))
            assert os.path.exists(path), f"{doc} links to {target}"


def test_readme_results_table_equals_the_committed_experiment():
    doc = json.load(open(os.path.join(ROOT, "experiments", "default_experiment_results.json")))
    patterns = [s["pattern"] for s in doc["definition"]["scenarios"]]
    readme = text("README.md")
    for s, name in enumerate(patterns):
        cells = sorted((a for a in doc["aggregates"] if a["scenario"] == s), key=lambda a: a["policy"])
        p95 = [c["metrics"]["wait.p95"]["mean"] for c in cells]
        total = [c["metrics"]["total.mean"]["mean"] for c in cells]
        row = f"| {name} | " + " | ".join(p95 + total) + " |"
        assert row in readme, row
    cfg = doc["definition"]["configuration"]
    assert (cfg["num_floors"], cfg["num_elevators"], cfg["capacity"]) == (20, 4, 8)
    assert len(doc["definition"]["seeds"]) == 20 and len(doc["definition"]["scenarios"]) == 9 and len(doc["runs"]) == 540
    assert len(doc["definition"]["seeds"]) * len(patterns) == 180 and sum(a["halted_count"] for a in doc["aggregates"]) == 0
    # the paired statements of the README
    by = {(a["scenario"], a["policy"]): a for a in doc["aggregates"]}
    cost = {s: by[(s, 2)]["paired_against"] for s in range(9)}
    nc_all_20 = [s for s in range(9) if cost[s]["1"]["wait.p95"]["better"] == 20]
    assert len(nc_all_20) == 8 and cost[7]["1"]["wait.p95"]["equal"] == 20
    assert len([s for s in range(9) if cost[s]["0"]["wait.p95"]["better"] == 20]) == 5
    assert len([s for s in range(9) if cost[s]["0"]["total.mean"]["better"] == 20]) == 7
    cap = cost[6]["0"]
    assert (cap["wait.p95"]["better"], cap["wait.p95"]["equal"], cap["wait.p95"]["worse"], cap["wait.p95"]["mean"]) == (8, 8, 4, "-0.200")
    assert cap["wait.max"]["better"] == 20 and cap["wait.max"]["mean"] == "-13.500"
    assert cost[4]["0"]["total.mean"]["worse"] == 3
    assert by[(0, 1)]["metrics"]["wait.mean"]["mean"] == "5.252" and by[(0, 0)]["metrics"]["wait.mean"]["mean"] == "7.245"
    assert by[(6, 1)]["metrics"]["deferred.count"]["mean"] == "92.000" and by[(6, 0)]["metrics"]["deferred.count"]["mean"] == "68.000"


def test_evidence_the_documents_name_exists():
    assert glob.glob(os.path.join(ROOT, "docs", "cpoc", "witness_*.md"))
    png = open(os.path.join(ROOT, "docs", "images", "web_demo.png"), "rb").read()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 10000
    assert "docs/images/web_demo.png" in text("README.md")
    for name in ("cut_05_cost_based_scheduler.md", "cut_06_reporting_calibration.md", "cut_10_cpoc_witness.md"):
        assert os.path.exists(os.path.join(ROOT, "docs", "implementation", name))
    assert "Approximately 5 hours, including implementation, testing, evaluation, and documentation." in text("README.md")


def test_diagrams_are_the_five_the_documents_promise():
    kinds = []
    for doc in PUBLIC:
        for block in re.findall(r"```mermaid\n(.*?)```", text(doc), re.S):
            kinds.append(block.split("\n", 1)[0].split()[0])
    assert kinds == ["flowchart"] + ["flowchart", "flowchart", "flowchart", "sequenceDiagram"] and len(kinds) == 5
    for doc in PUBLIC:
        assert text(doc).count("```") % 2 == 0, doc


def prose_of(body):
    """Prose only: no code blocks, tables, inline code or link targets."""
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = "\n".join(line for line in body.splitlines() if not line.startswith("|"))
    body = re.sub(r"`[^`]*`", "", body)
    body = re.sub(r"\]\([^)]*\)", "]", body)
    return re.sub(r"https?\S+", "", body)


BANNED = ["journey", "leveraging", "robust", "seamless", "powerful", "holistic", "comprehensive", "innovative",
          "cutting-edge", "best-in-class", "unlock", "enhance", "streamline", "elevate", "delve", "showcase",
          "demonstrate", "this ensures", "this allows", "this enables", "not only", "at its core", "in today's",
          "worth noting", "importantly", "crucially", "ultimately", "overall", "in conclusion", "high level",
          "key takeaway", "designed to", "serves as", "provides a way", "helps to", "in order to", "state-of-the-art",
          "leverage"]


def test_public_text_follows_the_style_rules():
    for doc in PUBLIC:
        body = text(doc)
        assert not [c for c in body if ord(c) > 126], f"{doc} has a non-keyboard character"
        lowered = body.lower()
        assert not [w for w in BANNED if w in lowered], (doc, [w for w in BANNED if w in lowered])
        prose = prose_of(body)
        assert ";" not in prose and ":" not in prose, f"{doc} uses a semicolon or colon in prose"
        assert "--" not in prose, doc  # no dash punctuation
    readme = text("README.md")
    for process_word in ("Revision 7", "owner decision", "constitution", "Constitutional"):
        assert process_word not in readme, process_word
    assert re.search(r"^## 1\. Problem", readme, re.M) and readme.index("web_demo.png") < readme.index("## 3. Architecture")
