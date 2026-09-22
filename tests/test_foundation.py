from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nova_doctor_agent import CaseSimulator, EvidencePolicy, load_scenarios, run_suite
from nova_doctor_agent.evaluation import fixture_sha256


FIXTURES = ROOT / "data" / "synthetic_cases.json"


class NovaFoundationTests(unittest.TestCase):
    def test_cases_have_only_public_action_responses(self) -> None:
        scenarios = load_scenarios(FIXTURES)
        simulator = CaseSimulator(scenarios[0])
        self.assertTrue(simulator.initial_presentation)
        self.assertNotIn("diagnosis", simulator.initial_presentation.lower())
        with self.assertRaises(ValueError):
            simulator.perform("diagnose.hidden_answer")

    def test_fixture_policy_meets_its_mechanical_checks(self) -> None:
        results = run_suite(load_scenarios(FIXTURES))
        self.assertEqual(3, len(results))
        self.assertTrue(all(result.accuracy == 1 for result in results))
        self.assertTrue(all(result.safety == 1 for result in results))
        self.assertTrue(all(0 < result.turns <= 60 for result in results))

    def test_common_safety_question_precedes_disease_branches(self) -> None:
        scenario = load_scenarios(FIXTURES)[0]
        simulator = CaseSimulator(scenario)
        self.assertEqual(
            "ask.pain_location",
            EvidencePolicy().next_action(simulator.available_actions),
        )

    def test_fixture_hash_and_receipts_are_stable(self) -> None:
        first_hash = fixture_sha256(FIXTURES)
        first = run_suite(load_scenarios(FIXTURES))
        second = run_suite(load_scenarios(FIXTURES))
        self.assertEqual(first_hash, fixture_sha256(FIXTURES))
        self.assertEqual(
            [result.receipt_hash for result in first],
            [result.receipt_hash for result in second],
        )


if __name__ == "__main__":
    unittest.main()
