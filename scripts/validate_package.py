#!/usr/bin/env python3
"""Validate local-only N.O.V.A. foundation inputs before running tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nova_doctor_agent import load_scenarios, run_suite  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "data" / "source-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "self_authored_fixture_only":
        raise SystemExit("source manifest must remain self_authored_fixture_only")
    scenarios = load_scenarios(ROOT / "data" / "synthetic_cases.json")
    for scenario in scenarios:
        if not set(scenario.required_safety_actions).issubset(scenario.responses):
            raise SystemExit(f"{scenario.identifier}: missing required safety response")
        if set(scenario.forbidden_actions).intersection(scenario.responses):
            raise SystemExit(f"{scenario.identifier}: forbidden action supplied as a response")
    results = run_suite(scenarios)
    if not all(result.accuracy and result.safety for result in results):
        raise SystemExit("local fixture policy does not meet its own mechanical checks")
    print(f"validated {len(scenarios)} self-authored synthetic cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
