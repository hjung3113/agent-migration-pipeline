"""Abstract evidence-source ports for the composite parity judge.

This module defines adapter *ports only*. There is intentionally:

- no concrete implementation,
- no connection code to the legacy system, MSSQL, or the host platform,
- no external dependency (standard library only).

Which evidence sources can actually be wired up is pending OQ-010
("Which outputs are observable without the full UI: DB, files, logs,
callbacks, return values?" -- see docs/05-open-questions.md), so the
framework ships as a pure interface skeleton (migration slice S-001).

Evidence-source model, fixed by docs/03-evidence-and-verification.md
"Judge design under incomplete tests"::

    existing tests
    + contract tests
    + DB assertions
    + output snapshots
    + callback assertions
    + selected manual evidence

Each source is one port. A port implementation collects evidence for one
judged scenario and reports a single :class:`EvidenceResult`.

Connection to the characterization capture items
-------------------------------------------------
``docs/templates/characterization-record.md`` is the shared storage schema
for captured evidence. Its eight core capture items (plus the conditional
timing/order item) feed the ports as follows:

    capture item (template section)      primary port(s)
    -----------------------------------  ---------------------------------
    exact input fixture                  ContractTestPort (replays fixture)
    initial DB state or relevant records DbAssertionPort (before side)
    return/output value                  ContractTestPort, OutputSnapshotPort
    resulting DB state                   DbAssertionPort (after side)
    files generated/modified             OutputSnapshotPort
    logs/events                          OutputSnapshotPort
    callbacks to platform                CallbackAssertionPort
    exception/error code                 ContractTestPort, OutputSnapshotPort
    timing/order (business-significant)  CallbackAssertionPort (call order)

Two ports are cross-cutting and do not map to a single capture item:

- :class:`ExistingTestsPort` reports the legacy suite's own result as the
  baseline evidence source (coverage strength depends on OQ-011/OQ-012).
- :class:`ManualEvidencePort` carries selected human-verified observation
  recorded under the "Human verification" rules in docs/03 (who/when,
  scenario, observation, artifacts, remaining uncertainty).

Comparison semantics (equality rules in docs/03) belong to the behavior
contract, never to these ports or to the composite judge.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

SOURCE_EXISTING_TESTS = "existing-tests"
SOURCE_CONTRACT_TESTS = "contract-tests"
SOURCE_DB_ASSERTIONS = "db-assertions"
SOURCE_OUTPUT_SNAPSHOTS = "output-snapshots"
SOURCE_CALLBACK_ASSERTIONS = "callback-assertions"
SOURCE_MANUAL_EVIDENCE = "manual-evidence"

VALID_EVIDENCE_GRADES = ("A", "B", "C", "D", "?")


class SourceVerdict(Enum):
    """Verdict reported by a single evidence source for one scenario.

    - ``PASS``: source ran and its assertions agree with the target.
    - ``FAIL``: source ran and detected a mismatch.
    - ``INSUFFICIENT``: source ran or was reviewed, but the evidence is too
      weak or incomplete to assert either way (feeds PARTIAL).
    - ``NOT_SUBMITTED``: source is expected for this scenario but no result
      was provided (feeds BLOCKED).
    - ``NOT_IMPLEMENTED``: no concrete adapter exists for this source yet,
      e.g. while OQ-010 is unresolved (feeds BLOCKED).
    """

    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT = "INSUFFICIENT"
    NOT_SUBMITTED = "NOT_SUBMITTED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

    @property
    def is_blocking(self) -> bool:
        """Whether this verdict blocks the composite grade (BLOCKED)."""
        return self in (SourceVerdict.NOT_SUBMITTED, SourceVerdict.NOT_IMPLEMENTED)


@dataclass(frozen=True)
class EvidenceResult:
    """One evidence source's verdict for one judged scenario.

    Attributes:
        source: Evidence-source name. Use the ``SOURCE_*`` constants so
            results line up with declared expectations in
            :class:`migration.judge.composite.CompositeJudge`.
        verdict: Per-source verdict.
        detail: Human-readable explanation; required in practice for FAIL,
            INSUFFICIENT, and blocking verdicts so reports stay auditable.
        evidence_grade: Optional docs/03 grade ("A" | "B" | "C" | "D" | "?")
            describing the certainty of this source's evidence. Grades
            communicate certainty, not correctness.
        linked_capture_items: Names of the characterization-record capture
            items this result judged (subset of the eight core items plus
            the conditional timing/order item). Informational only; kept so
            judge reports can reference the underlying characterization
            records without re-reading them.
    """

    source: str
    verdict: SourceVerdict
    detail: str | None = None
    evidence_grade: str | None = None
    linked_capture_items: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.evidence_grade is not None and self.evidence_grade not in VALID_EVIDENCE_GRADES:
            raise ValueError(
                f"evidence_grade must be one of {VALID_EVIDENCE_GRADES}, "
                f"got {self.evidence_grade!r}"
            )


class EvidencePort(ABC):
    """Common base for all evidence-source adapter ports.

    A port isolates "where evidence comes from" from "how verdicts are
    combined". Concrete adapters are written later, after OQ-010 confirms
    which outputs are observable without the full UI. Adapters must not
    implement business comparison logic; equality semantics live in the
    behavior contract (docs/03 "Equality rules").
    """

    #: Stable evidence-source name; override with a ``SOURCE_*`` constant.
    source_name: str = ""


class ExistingTestsPort(EvidencePort):
    """Runs the legacy suite's existing automated tests as baseline evidence.

    Coverage is expected to be incomplete (docs/03 "Problem"), so a PASS
    here only means "known automated checks still hold". The overlap between
    these tests and the migrated feature must be stated in the result's
    ``detail``; an empty overlap should be reported as INSUFFICIENT, not
    PASS. Depends on OQ-011/OQ-012 (what tests exist; whether CI is
    runnable by agents).
    """

    source_name = SOURCE_EXISTING_TESTS

    @abstractmethod
    def run_existing_suite(self) -> EvidenceResult:
        """Execute the legacy existing test suite and report one result."""


class ContractTestPort(EvidencePort):
    """Replays characterization fixtures as contract tests at the boundary.

    Consumes capture items: ``exact input fixture`` (replayed as-is),
    ``return/output value``, and ``exception/error code`` (asserted verbatim,
    including explicit ``none observed`` happy-path captures). The contract
    being replayed is the approved behavior contract for the feature, not
    the characterization record itself.
    """

    source_name = SOURCE_CONTRACT_TESTS

    @abstractmethod
    def run_contract_tests(self) -> EvidenceResult:
        """Replay contract fixtures against the target and report one result."""


class DbAssertionPort(EvidencePort):
    """Compares relevant database rows before/after the scenario.

    Consumes capture items: ``initial DB state or relevant records`` and
    ``resulting DB state``. Scoping follows the characterization record
    (records the scenario touches, not full dumps). Migration must also
    account for database-resident business logic (OQ-013) when judging DB
    parity. No database connection code exists in this skeleton.
    """

    source_name = SOURCE_DB_ASSERTIONS

    @abstractmethod
    def assert_db_state(self) -> EvidenceResult:
        """Compare target DB side effects against captured legacy state."""


class OutputSnapshotPort(EvidencePort):
    """Compares captured outputs (values, files, logs) as snapshots.

    Consumes capture items: ``return/output value``,
    ``files generated/modified``, ``logs/events``, and
    ``exception/error code``. Snapshots are compared under the equality
    rules of the behavior contract (exact / tolerance / normalized), never
    byte-for-byte by default.
    """

    source_name = SOURCE_OUTPUT_SNAPSHOTS

    @abstractmethod
    def compare_output_snapshots(self) -> EvidenceResult:
        """Compare target outputs against captured legacy snapshots."""


class CallbackAssertionPort(EvidencePort):
    """Asserts calls the component makes back into the host platform.

    Consumes capture items: ``callbacks to platform`` (ordered table of
    entry point/API + payload) and, when business-significant, the
    conditional ``timing/order`` item. Whether callbacks are observable at
    all depends on OQ-005/OQ-010; until then any adapter stays
    unimplemented (NOT_IMPLEMENTED), not silently skipped.
    """

    source_name = SOURCE_CALLBACK_ASSERTIONS

    @abstractmethod
    def assert_platform_callbacks(self) -> EvidenceResult:
        """Assert target-to-platform callbacks match captured legacy calls."""


class ManualEvidencePort(EvidencePort):
    """Carries selected human-verified observation as evidence.

    Used only where automation is not currently possible (docs/03 "Human
    verification"). The concrete adapter must surface the recorded manual
    evidence (who/when, scenario executed, observation, artifacts, remaining
    uncertainty) and report INSUFFICIENT when any required field is missing.
    Manual observation must never be converted into an undocumented
    permanent assumption.
    """

    source_name = SOURCE_MANUAL_EVIDENCE

    @abstractmethod
    def collect_manual_evidence(self) -> EvidenceResult:
        """Review recorded manual evidence for the scenario and report one result."""
