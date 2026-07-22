#!/usr/bin/env python3
"""Build a Phase 9 report from real run-result JSONL records."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from matemium.agent.evaluation import BenchmarkResult, evaluate_release


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path, help="JSONL produced by cloud/local benchmark runs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    suite = json.loads((root / "evals/agent/phase0-benchmarks.json").read_text())
    config = json.loads((root / "evals/agent/phase0-thresholds.json").read_text())
    rows = [BenchmarkResult.from_dict(json.loads(line)) for line in args.results.read_text().splitlines() if line.strip()]
    report = evaluate_release(rows, {case["id"] for case in suite["cases"]}, config["release_thresholds"])
    report.update({"schema_version": 1, "suite_id": suite["suite_id"], "generated_at": datetime.now(timezone.utc).isoformat(), "source_results": str(args.results)})
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["approved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
