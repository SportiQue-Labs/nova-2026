#!/usr/bin/env python3
"""Run the local fixture evaluator; this is not the official submission entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from nova_doctor_agent import load_scenarios, run_suite
from nova_doctor_agent.evaluation import fixture_sha256, results_as_json


ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURES = ROOT / "data" / "synthetic_cases.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = run_suite(load_scenarios(args.fixtures), max_turns=args.max_turns)
    if args.json:
        print(results_as_json(results))
    else:
        print(f"fixture_sha256={fixture_sha256(args.fixtures)}")
        for result in results:
            print(
                f"{result.case_id}: accuracy={result.accuracy} safety={result.safety} "
                f"turns={result.turns} efficiency={result.efficiency:.4f}"
            )
    return 0 if all(result.accuracy and result.safety for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
