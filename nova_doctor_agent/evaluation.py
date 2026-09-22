"""Reproducible local evaluation for the self-authored fixture protocol."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .core import CaseSimulator, EvidencePolicy, Scenario


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    predicted_diagnosis: str | None
    expected_diagnosis: str
    turns: int
    accuracy: int
    efficiency: float
    safety: int
    performed_actions: tuple[str, ...]
    receipt_hash: str


def evaluate_case(scenario: Scenario, max_turns: int = 60) -> EvaluationResult:
    if max_turns < 1:
        raise ValueError("max_turns must be positive")
    simulator = CaseSimulator(scenario)
    policy = EvidencePolicy()
    predicted: str | None = None

    for _ in range(max_turns):
        action = policy.next_action(simulator.available_actions)
        if action is None:
            break
        policy.observe(simulator.perform(action))
        predicted = policy.diagnosis_if_ready()
        if predicted is not None:
            break

    actions = policy.performed_actions
    safety = int(
        set(simulator.required_safety_actions_for_evaluation).issubset(actions)
        and not set(simulator.forbidden_actions_for_evaluation).intersection(actions)
    )
    accuracy = int(predicted == simulator.expected_diagnosis_for_evaluation())
    payload = {
        "case_id": scenario.identifier,
        "predicted_diagnosis": predicted,
        "expected_diagnosis": simulator.expected_diagnosis_for_evaluation(),
        "performed_actions": actions,
    }
    receipt_hash = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return EvaluationResult(
        case_id=scenario.identifier,
        predicted_diagnosis=predicted,
        expected_diagnosis=simulator.expected_diagnosis_for_evaluation(),
        turns=len(actions),
        accuracy=accuracy,
        efficiency=round(max(0.0, 1 - len(actions) / max_turns), 4),
        safety=safety,
        performed_actions=actions,
        receipt_hash=receipt_hash,
    )


def run_suite(scenarios: list[Scenario], max_turns: int = 60) -> list[EvaluationResult]:
    return [evaluate_case(scenario, max_turns=max_turns) for scenario in scenarios]


def results_as_json(results: list[EvaluationResult]) -> str:
    return json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2)


def fixture_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
