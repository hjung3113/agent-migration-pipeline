"""Composite judge: merges per-source evidence into one overall grade.

Implements the combination half of docs/03-evidence-and-verification.md
"Judge design under incomplete tests" (fixed by migration slice S-001)::

    existing tests
    + contract tests
    + DB assertions
    + output snapshots
    + callback assertions
    + selected manual evidence
    -> PASS / FAIL / PARTIAL / BLOCKED

Standard library only. No evidence collection happens here; this module
only combines :class:`~migration.judge.ports.EvidenceResult` values
produced by the ports defined in ``migration.judge.ports``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from .ports import EvidenceResult, SourceVerdict

BLOCKING_VERDICTS = (SourceVerdict.NOT_SUBMITTED, SourceVerdict.NOT_IMPLEMENTED)


class CompositeVerdict(Enum):
    """Overall grade for one judged scenario.

    - ``PASS``: every submitted source reported PASS.
    - ``FAIL``: at least one source detected a mismatch. A detected
      mismatch is decisive negative evidence, so FAIL outranks BLOCKED —
      the harness already caught something, regardless of sources that
      could not run.
    - ``BLOCKED``: the scenario cannot be judged because an expected
      source was not submitted or has no adapter yet (e.g. while OQ-010 is
      unresolved). Not a quality statement about the target.
    - ``PARTIAL``: judging proceeded but evidence is incomplete — some
      sources PASS while at least one reports INSUFFICIENT.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CompositeReport:
    """Persistable outcome of one composite judgement (Rulebook rule 12).

    Attributes:
        verdict: Overall composite grade.
        results: Per-source results the grade was derived from, including
            synthetic NOT_SUBMITTED entries for expected-but-missing
            sources.
        reasons: Human-readable trace of which results drove the grade.
    """

    verdict: CompositeVerdict
    results: tuple[EvidenceResult, ...] = ()
    reasons: tuple[str, ...] = ()

    def summary(self) -> str:
        """Multi-line text suitable for writing to a verification report."""
        lines = [f"composite verdict: {self.verdict.value}"]
        for reason in self.reasons:
            lines.append(f"reason: {reason}")
        for result in self.results:
            grade = f" [{result.evidence_grade}]" if result.evidence_grade else ""
            detail = f" — {result.detail}" if result.detail else ""
            lines.append(f"source {result.source}: {result.verdict.value}{grade}{detail}")
        return "\n".join(lines)


@dataclass(frozen=True)
class CompositeJudge:
    """Combines evidence-source results into one PASS/FAIL/PARTIAL/BLOCKED grade.

    Combination rules, in evaluation order (docs/03 "Judge design under
    incomplete tests"):

    1. any source FAIL                          -> FAIL
    2. any source NOT_SUBMITTED / NOT_IMPLEMENTED -> BLOCKED
    3. all sources PASS                         -> PASS
    4. otherwise (>=1 PASS + >=1 INSUFFICIENT,
       or all INSUFFICIENT)                     -> PARTIAL

    An empty result set is BLOCKED: nothing was judged.

    Relationship to the characterization capture items
    (``docs/templates/characterization-record.md``):

    The template's capture items — ``exact input fixture``, ``initial DB
    state or relevant records``, ``return/output value``, ``resulting DB
    state``, ``files generated/modified``, ``logs/events``, ``callbacks to
    platform``, ``exception/error code`` — are the raw evidence each *port*
    consumes (see the mapping table in ``migration/judge/ports.py``). This
    class never reads those items directly; it only sees each port's
    distilled :class:`~migration.judge.ports.EvidenceResult`.

    Before any composite verdict is trusted as an exit condition, the
    harness must pass a mutation self-test: inject a known-wrong result
    into each port and confirm FAIL (docs/03 "Judge design under incomplete
    tests"). That self-test ran in slice S-011 and passed
    (migration/judge/tests/test_mutation_self_test.py).

    Attributes:
        expected_sources: Source names (``SOURCE_*`` constants) required for
            this scenario. Required, no default (docs/03 "Which sources a
            judgement requires is explicit, not defaulted"): a source listed
            here but missing from the submitted results is added as a
            synthetic NOT_SUBMITTED entry, which grades the scenario
            BLOCKED, rather than letting an unstated requirement resolve to
            PASS.
    """

    expected_sources: Sequence[str]

    def judge(self, results: Sequence[EvidenceResult]) -> CompositeReport:
        """Grade one scenario from its per-source results."""
        merged = self._merge_results(results)
        reasons = self._reasons(merged)

        if not merged:
            verdict = CompositeVerdict.BLOCKED
        elif any(r.verdict is SourceVerdict.FAIL for r in merged):
            verdict = CompositeVerdict.FAIL
        elif any(r.verdict in BLOCKING_VERDICTS for r in merged):
            verdict = CompositeVerdict.BLOCKED
        elif all(r.verdict is SourceVerdict.PASS for r in merged):
            verdict = CompositeVerdict.PASS
        else:
            verdict = CompositeVerdict.PARTIAL

        return CompositeReport(
            verdict=verdict,
            results=tuple(merged),
            reasons=tuple(reasons),
        )

    def _merge_results(
        self, results: Sequence[EvidenceResult]
    ) -> list[EvidenceResult]:
        merged = list(results)
        submitted = {r.source for r in merged}
        missing = [s for s in self.expected_sources if s not in submitted]
        for source in missing:
            merged.append(
                EvidenceResult(
                    source=source,
                    verdict=SourceVerdict.NOT_SUBMITTED,
                    detail="expected by CompositeJudge but no result was submitted",
                )
            )
        return merged

    def _reasons(self, merged: Sequence[EvidenceResult]) -> list[str]:
        reasons: list[str] = []
        failures = [r for r in merged if r.verdict is SourceVerdict.FAIL]
        blocking = [r for r in merged if r.verdict in BLOCKING_VERDICTS]
        insufficient = [
            r for r in merged if r.verdict is SourceVerdict.INSUFFICIENT
        ]

        if not merged:
            reasons.append("no evidence results were submitted")
        if failures:
            reasons.append(
                f"mismatch detected by: {', '.join(r.source for r in failures)}"
            )
        if blocking:
            kinds = sorted(
                f"{r.source}({r.verdict.value})" for r in blocking
            )
            reasons.append(f"cannot judge, blocked sources: {', '.join(kinds)}")
        if insufficient:
            reasons.append(
                f"insufficient evidence from: "
                f"{', '.join(r.source for r in insufficient)}"
            )
        return reasons
