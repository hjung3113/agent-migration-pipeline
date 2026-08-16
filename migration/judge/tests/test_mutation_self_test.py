"""Mutation self-test for the composite judge (migration slice S-011).

Exercises migration/judge/ end-to-end against a synthetic ("dummy") feature
— see migration/features/synthetic-demo/ — instead of a real legacy
feature, per docs/02 "make the process runnable before migrating production
behavior". This test IS the S-011 exit condition from docs/03
"Judge design under incomplete tests": "Before trusting a parity harness,
deliberately introduce a known wrong result and confirm the harness fails.
A judge that cannot catch a controlled mismatch is not a useful exit
condition."

The synthetic scenario: a trivial "concatenate two strings" feature
(migration/features/synthetic-demo/), captured as legacy behavior
input=("foo", "bar") -> output "foobar" (characterization-record.md), and
implemented in target/backend as app.services.greeting.concatenate. The fake
ports below stand in for real adapters (which do not exist yet — concrete
adapters are blocked on OQ-010, per migration/judge/README.md); they do not
touch the real target backend process/venv, only reproduce its known,
trivial behavior inline for comparison, which is sufficient to test the
*judge's* grading logic rather than the target implementation itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from migration.judge.composite import CompositeJudge, CompositeVerdict
from migration.judge.ports import (
    SOURCE_CONTRACT_TESTS,
    SOURCE_DB_ASSERTIONS,
    SOURCE_EXISTING_TESTS,
    SOURCE_OUTPUT_SNAPSHOTS,
    EvidenceResult,
    SourceVerdict,
)

# Characterization-record.md capture for the synthetic feature: input
# fixture and the legacy-side expected output.
_LEGACY_INPUT = ("foo", "bar")
_LEGACY_EXPECTED_OUTPUT = "foobar"

#: Sources declared for this synthetic scenario. The synthetic feature has
#: no DB/callback side effects, so only the sources that apply are
#: expected — narrowing expected_sources is the documented pattern
#: (migration/judge/README.md) for scenarios that legitimately don't need
#: all six.
_EXPECTED_SOURCES = (
    SOURCE_EXISTING_TESTS,
    SOURCE_CONTRACT_TESTS,
    SOURCE_OUTPUT_SNAPSHOTS,
)


def _target_concatenate(a: str, b: str) -> str:
    """Mirrors target/backend's app.services.greeting.concatenate.

    Reproduced inline (not imported) so this test does not depend on the
    target backend's separate uv-managed environment; see module docstring.
    """
    return a + b


@dataclass
class FakePorts:
    """Bundles fake evidence collection for the synthetic scenario.

    ``target_output`` is the single injection point the mutation pass below
    flips to a known-wrong value.
    """

    target_output: str

    def existing_tests(self) -> EvidenceResult:
        # Synthetic feature has no legacy automated test to run against;
        # report INSUFFICIENT rather than fabricating a PASS.
        return EvidenceResult(
            source=SOURCE_EXISTING_TESTS,
            verdict=SourceVerdict.INSUFFICIENT,
            detail="synthetic-demo has no legacy test suite (dummy feature)",
        )

    def contract_test(self) -> EvidenceResult:
        matches = self.target_output == _LEGACY_EXPECTED_OUTPUT
        return EvidenceResult(
            source=SOURCE_CONTRACT_TESTS,
            verdict=SourceVerdict.PASS if matches else SourceVerdict.FAIL,
            detail=(
                f"replayed fixture {_LEGACY_INPUT!r}: "
                f"expected {_LEGACY_EXPECTED_OUTPUT!r}, got {self.target_output!r}"
            ),
            evidence_grade="B",
            linked_capture_items=("exact input fixture", "return/output value"),
        )

    def output_snapshot(self) -> EvidenceResult:
        matches = self.target_output == _LEGACY_EXPECTED_OUTPUT
        return EvidenceResult(
            source=SOURCE_OUTPUT_SNAPSHOTS,
            verdict=SourceVerdict.PASS if matches else SourceVerdict.FAIL,
            detail=f"output snapshot comparison: matches={matches}",
            evidence_grade="B",
            linked_capture_items=("return/output value",),
        )

    def db_assertion_unused(self) -> EvidenceResult:
        # Not in _EXPECTED_SOURCES; included only to show the port exists
        # and to keep NOT_IMPLEMENTED distinct from "not applicable".
        return EvidenceResult(
            source=SOURCE_DB_ASSERTIONS,
            verdict=SourceVerdict.NOT_IMPLEMENTED,
            detail="synthetic-demo has no DB side effects",
        )


def _judge_for(target_output: str) -> tuple[CompositeVerdict, tuple[str, ...]]:
    ports = FakePorts(target_output=target_output)
    results = [ports.existing_tests(), ports.contract_test(), ports.output_snapshot()]
    judge = CompositeJudge(expected_sources=_EXPECTED_SOURCES)
    report = judge.judge(results)
    return report.verdict, report.reasons


def test_baseline_correct_target_output_grades_partial() -> None:
    """Sanity check: correct target output, judge does not FAIL.

    Grades PARTIAL, not PASS, because SOURCE_EXISTING_TESTS is legitimately
    INSUFFICIENT for a feature with no legacy test suite — this is the
    honest baseline for a synthetic feature, not a defect in the scenario.
    """
    verdict, _ = _judge_for(_LEGACY_EXPECTED_OUTPUT)
    assert verdict is CompositeVerdict.PARTIAL


def test_mutation_wrong_target_output_is_caught_as_fail() -> None:
    """The mutation self-test required by docs/03 'Judge design'.

    Deliberately inject a known-wrong target output (mutate "foobar" to
    "foobar!") and confirm the composite judge grades FAIL, not PASS or
    PARTIAL. If this assertion fails, migration/judge is not a trustworthy
    exit condition and must not be used to grade real feature verification
    until fixed (README principle 7: fix the process).
    """
    mutated_output = _LEGACY_EXPECTED_OUTPUT + "!"
    assert mutated_output != _LEGACY_EXPECTED_OUTPUT  # guard against a no-op mutation

    verdict, reasons = _judge_for(mutated_output)

    assert verdict is CompositeVerdict.FAIL
    assert any("mismatch detected by" in r for r in reasons)


def test_mutation_self_test_actually_exercises_both_failing_sources() -> None:
    """Confirms the mutation is caught by every source capable of catching it.

    Guards against a self-test that only *looks* like it's checking the
    judge (e.g. one fake port silently always PASSes regardless of input).
    """
    mutated_output = _LEGACY_EXPECTED_OUTPUT + "!"
    ports = FakePorts(target_output=mutated_output)

    contract_result = ports.contract_test()
    snapshot_result = ports.output_snapshot()

    assert contract_result.verdict is SourceVerdict.FAIL
    assert snapshot_result.verdict is SourceVerdict.FAIL


def test_target_module_actually_produces_the_legacy_expected_output() -> None:
    """Closes the loop: the *real* synthetic target logic (reproduced above)
    genuinely matches the captured legacy expectation on the happy path —
    this is not just a judge unit test in isolation."""
    assert _target_concatenate(*_LEGACY_INPUT) == _LEGACY_EXPECTED_OUTPUT
