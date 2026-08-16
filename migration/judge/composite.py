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
from dataclasses import dataclass, field
from enum import Enum

from .ports import (
    SOURCE_CALLBACK_ASSERTIONS,
    SOURCE_CONTRACT_TESTS,
    SOURCE_DB_ASSERTIONS,
    SOURCE_EXISTING_TESTS,
    SOURCE_MANUAL_EVIDENCE,
    SOURCE_OUTPUT_SNAPSHOTS,
    EvidenceResult,
    SourceVerdict,
)

BLOCKING_VERDICTS = (SourceVerdict.NOT_SUBMITTED, SourceVerdict.NOT_IMPLEMENTED)

#: All six canonical sources. Used as the default for
#: ``CompositeJudge.expected_sources`` so an under-configured judge cannot
#: silently PASS on a single submitted source — callers must narrow this
#: explicitly if a scenario legitimately does not need all six.
ALL_SOURCES = (
    SOURCE_EXISTING_TESTS,
    SOURCE_CONTRACT_TESTS,
    SOURCE_DB_ASSERTIONS,
    SOURCE_OUTPUT_SNAPSHOTS,
    SOURCE_CALLBACK_ASSERTIONS,
    SOURCE_MANUAL_EVIDENCE,
)


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
    #: False when any source was blocking (NOT_SUBMITTED/NOT_IMPLEMENTED) or
    #: reported conflicting duplicate verdicts. A FAIL verdict with
    #: coverage_complete=False is still a real FAIL (the source that caught
    #: the mismatch ran), but readers should know other expected sources
    #: never weighed in.
    coverage_complete: bool = True

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

    Combination rules, in evaluation order:

    0. two results for the same source disagree (conflicting duplicate
       submission)                              -> BLOCKED
    1. any source FAIL                          -> FAIL
    2. any source NOT_SUBMITTED / NOT_IMPLEMENTED -> BLOCKED
    3. no source PASS (empty, or all INSUFFICIENT) -> BLOCKED
    4. all sources PASS                         -> PASS
    5. otherwise (>=1 PASS + >=1 INSUFFICIENT)  -> PARTIAL

    All-INSUFFICIENT is BLOCKED, not PARTIAL: it carries zero confirming
    evidence, the same epistemic state as an empty result set. PARTIAL is
    reserved for scenarios with at least one PASS alongside incomplete
    evidence elsewhere.

    A conflicting duplicate (the same source reporting two different
    verdicts) is not treated as ordinary FAIL-wins evidence: it means we
    cannot tell which submission is authoritative, so it forces BLOCKED
    even if one of the conflicting entries was FAIL. Identical duplicate
    submissions (e.g. from a retry) collapse silently to one entry and do
    not trigger this.

    Relationship to the characterization capture items
    (``docs/templates/characterization-record.md``):

    The template's eight core capture items — ``exact input fixture``,
    ``initial DB state or relevant records``, ``return/output value``,
    ``resulting DB state``, ``files generated/modified``, ``logs/events``,
    ``callbacks to platform``, ``exception/error code`` — are the raw
    evidence each *port* consumes (see the mapping table in
    ``migration/judge/ports.py``). This class never reads those items
    directly; it only sees each port's distilled
    :class:`~migration.judge.ports.EvidenceResult`, where
    ``linked_capture_items`` records which of the eight items the source
    judged. A capture item recorded as ``not captured (see caveats)`` in
    the characterization record should surface as INSUFFICIENT (-> PARTIAL)
    from the port responsible for that item, or as NOT_SUBMITTED (->
    BLOCKED) when declared in ``expected_sources`` but absent — never as a
    silent PASS. Capture items marked ``N/A`` for the scenario are exempt.

    Before any composite verdict is trusted as an exit condition, the
    harness must pass a mutation self-test: inject a known-wrong result
    into each port and confirm FAIL (docs/03 "Judge design under incomplete
    tests"). That self-test is scheduled as slice S-011; until it passes,
    treat this judge as unproven scaffolding.

    Attributes:
        expected_sources: Source names (``SOURCE_*`` constants) that must be
            submitted for a scenario. Sources listed here but missing from
            the submitted results are added as synthetic NOT_SUBMITTED
            entries, which grades the scenario BLOCKED. Declare only the
            sources the scenario actually requires: ``selected`` manual
            evidence, for example, is often legitimately absent.
    """

    #: Sources that must be submitted for a scenario to be judgeable.
    #: Defaults to all six canonical sources so an under-configured judge
    #: cannot silently PASS on a single submitted result — narrow this
    #: explicitly per scenario (e.g. drop SOURCE_MANUAL_EVIDENCE when no
    #: manual evidence is expected).
    expected_sources: Sequence[str] = field(default=ALL_SOURCES)

    def judge(self, results: Sequence[EvidenceResult]) -> CompositeReport:
        """Grade one scenario from its per-source results."""
        merged = self._merge_results(results)
        deduped, conflicts = self._dedupe(merged)
        reasons = self._reasons(deduped, conflicts)
        blocking = [r for r in deduped if r.verdict in BLOCKING_VERDICTS]

        if conflicts:
            verdict = CompositeVerdict.BLOCKED
        elif not deduped:
            verdict = CompositeVerdict.BLOCKED
        elif any(r.verdict is SourceVerdict.FAIL for r in deduped):
            verdict = CompositeVerdict.FAIL
        elif blocking:
            verdict = CompositeVerdict.BLOCKED
        elif not any(r.verdict is SourceVerdict.PASS for r in deduped):
            verdict = CompositeVerdict.BLOCKED
        elif all(r.verdict is SourceVerdict.PASS for r in deduped):
            verdict = CompositeVerdict.PASS
        else:
            verdict = CompositeVerdict.PARTIAL

        return CompositeReport(
            verdict=verdict,
            results=tuple(merged),
            reasons=tuple(reasons),
            coverage_complete=not (blocking or conflicts),
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

    def _dedupe(
        self, merged: Sequence[EvidenceResult]
    ) -> tuple[list[EvidenceResult], list[str]]:
        """Collapse identical duplicate submissions; flag conflicting ones.

        A conflict (same source, different verdicts) is reported separately
        rather than folded into the normal verdict scan, because we cannot
        tell which of the disagreeing submissions is authoritative.
        """
        by_source: dict[str, list[EvidenceResult]] = {}
        for result in merged:
            by_source.setdefault(result.source, []).append(result)

        deduped: list[EvidenceResult] = []
        conflicts: list[str] = []
        for source, entries in by_source.items():
            distinct_verdicts = {e.verdict for e in entries}
            if len(distinct_verdicts) > 1:
                conflicts.append(source)
            else:
                deduped.append(entries[0])
        return deduped, sorted(conflicts)

    def _reasons(
        self, deduped: Sequence[EvidenceResult], conflicts: Sequence[str]
    ) -> list[str]:
        reasons: list[str] = []
        failures = [r for r in deduped if r.verdict is SourceVerdict.FAIL]
        blocking = [r for r in deduped if r.verdict in BLOCKING_VERDICTS]
        insufficient = [
            r for r in deduped if r.verdict is SourceVerdict.INSUFFICIENT
        ]
        has_pass = any(r.verdict is SourceVerdict.PASS for r in deduped)

        if conflicts:
            reasons.append(
                f"conflicting results submitted for: {', '.join(conflicts)}"
            )
        if not deduped and not conflicts:
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
        if deduped and not has_pass and not failures and not conflicts:
            reasons.append("no source reported PASS; nothing was confirmed")
        return reasons
