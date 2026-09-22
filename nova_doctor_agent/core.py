"""Small deterministic policy used only to exercise the local fixture protocol.

The official N.O.V.A. action API is not public yet.  This module deliberately
does not imitate an unknown API, call an LLM, or expose final answers to the
policy.  It gives the later official adapter a narrow seam: public action ->
observation -> next action.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Observation:
    action: str
    text: str
    facts: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    identifier: str
    initial_presentation: str
    diagnosis: str
    required_safety_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    responses: dict[str, Observation]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Scenario":
        responses = {
            action: Observation(
                action=action,
                text=str(value.get("text", "")),
                facts=tuple(str(fact) for fact in value.get("facts", [])),
            )
            for action, value in raw["responses"].items()
        }
        return cls(
            identifier=str(raw["id"]),
            initial_presentation=str(raw["initial_presentation"]),
            diagnosis=str(raw["diagnosis"]),
            required_safety_actions=tuple(raw.get("required_safety_actions", [])),
            forbidden_actions=tuple(raw.get("forbidden_actions", [])),
            responses=responses,
        )


def load_scenarios(path: str | Path) -> list[Scenario]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema") != "nova.synthetic-cases.v1":
        raise ValueError("unsupported fixture schema")
    if raw.get("status") != "self_authored_fixture_only":
        raise ValueError("fixture status must be self_authored_fixture_only")
    scenarios = [Scenario.from_dict(case) for case in raw.get("cases", [])]
    if not scenarios:
        raise ValueError("at least one synthetic scenario is required")
    return scenarios


class CaseSimulator:
    """Exposes only a public presentation and requested-action observations."""

    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario
        self.initial_presentation = scenario.initial_presentation
        self.available_actions = tuple(sorted(scenario.responses))

    def perform(self, action: str) -> Observation:
        try:
            return self._scenario.responses[action]
        except KeyError as exc:
            raise ValueError(f"unsupported fixture action: {action}") from exc

    def expected_diagnosis_for_evaluation(self) -> str:
        """Evaluator-only seam; never pass the simulator to EvidencePolicy."""
        return self._scenario.diagnosis

    @property
    def required_safety_actions_for_evaluation(self) -> tuple[str, ...]:
        return self._scenario.required_safety_actions

    @property
    def forbidden_actions_for_evaluation(self) -> tuple[str, ...]:
        return self._scenario.forbidden_actions


# The mappings are deliberately tiny, self-authored protocol fixtures.  They
# are not a clinical knowledge base and must not be shipped in a product.
_PROFILE_WEIGHTS = {
    "appendicitis_like": {
        "rlq_pain": 3,
        "migration_to_rlq": 3,
        "fever": 1,
        "rebound_tenderness": 2,
        "leukocytosis": 1,
    },
    "ureteral_stone_like": {
        "flank_pain": 3,
        "colicky_pattern": 3,
        "hematuria": 3,
    },
    "biliary_colic_like": {
        "ruq_pain": 3,
        "postprandial_pattern": 3,
        "gallbladder_finding": 3,
    },
}

_PROFILE_CONFIRMATION_ACTIONS = {
    "appendicitis_like": ("exam.abdominal_tenderness", "test.cbc"),
    "ureteral_stone_like": ("ask.colicky_pattern", "test.urinalysis"),
    "biliary_colic_like": ("ask.postprandial_pattern", "test.ultrasound"),
}

_ACTION_FACTS = {
    "ask.pain_location": ("rlq_pain", "flank_pain", "ruq_pain"),
    "ask.pain_migration": ("migration_to_rlq",),
    "ask.colicky_pattern": ("colicky_pattern",),
    "ask.postprandial_pattern": ("postprandial_pattern",),
    "ask.fever": ("fever",),
    "exam.abdominal_tenderness": ("rebound_tenderness",),
    "test.cbc": ("leukocytosis",),
    "test.urinalysis": ("hematuria",),
    "test.ultrasound": ("gallbladder_finding",),
}


class EvidencePolicy:
    """Chooses a next action from public observations without a gold label."""

    def __init__(self) -> None:
        self._scores = {profile: 0 for profile in _PROFILE_WEIGHTS}
        self._performed: list[str] = []

    @property
    def performed_actions(self) -> tuple[str, ...]:
        return tuple(self._performed)

    def observe(self, observation: Observation) -> None:
        self._performed.append(observation.action)
        for profile, weights in _PROFILE_WEIGHTS.items():
            self._scores[profile] += sum(weights.get(fact, 0) for fact in observation.facts)

    def next_action(self, available_actions: tuple[str, ...]) -> str | None:
        remaining = [action for action in available_actions if action not in self._performed]
        if not remaining:
            return None

        # Every fixture begins with an undifferentiated abdominal presentation.
        # Resolve the shared location question before disease-specific branches;
        # otherwise a lexical tie can skip the common safety baseline.
        if not self._performed and "ask.pain_location" in remaining:
            return "ask.pain_location"

        profile, score = self._top_profile()
        if score >= 3:
            for action in _PROFILE_CONFIRMATION_ACTIONS[profile]:
                if action in remaining:
                    return action

        def utility(action: str) -> tuple[int, int, str]:
            facts = _ACTION_FACTS.get(action, ())
            profile_weights = [
                sum(weights.get(fact, 0) for fact in facts)
                for weights in _PROFILE_WEIGHTS.values()
            ]
            spread = max(profile_weights, default=0) - min(profile_weights, default=0)
            question_bonus = 1 if action.startswith("ask.") else 0
            return (spread, question_bonus, action)

        return max(remaining, key=utility)

    def diagnosis_if_ready(self) -> str | None:
        profile, score = self._top_profile()
        required = _PROFILE_CONFIRMATION_ACTIONS[profile]
        if score >= 5 and all(action in self._performed for action in required):
            return profile
        return None

    def _top_profile(self) -> tuple[str, int]:
        return max(self._scores.items(), key=lambda item: (item[1], item[0]))
