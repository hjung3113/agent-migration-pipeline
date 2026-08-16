"""Composite verification judge framework skeleton (migration slice S-001).

Pure interface skeleton fixed by docs/03-evidence-and-verification.md
"Judge design under incomplete tests": six evidence-source ports whose
results are combined into one PASS / FAIL / PARTIAL / BLOCKED grade.

No concrete adapters and no legacy/DB connections exist here. Which
sources can actually be wired up is pending OQ-010; real judge integration
is a separate later task. The mutation self-test required before trusting
this judge as an exit condition is scheduled as slice S-011.

Standard library only.
"""

from __future__ import annotations

from .composite import CompositeJudge, CompositeReport, CompositeVerdict
from .ports import (
    SOURCE_CALLBACK_ASSERTIONS,
    SOURCE_CONTRACT_TESTS,
    SOURCE_DB_ASSERTIONS,
    SOURCE_EXISTING_TESTS,
    SOURCE_MANUAL_EVIDENCE,
    SOURCE_OUTPUT_SNAPSHOTS,
    CallbackAssertionPort,
    ContractTestPort,
    DbAssertionPort,
    EvidencePort,
    EvidenceResult,
    ExistingTestsPort,
    ManualEvidencePort,
    OutputSnapshotPort,
    SourceVerdict,
)

__all__ = [
    "CallbackAssertionPort",
    "CompositeJudge",
    "CompositeReport",
    "CompositeVerdict",
    "ContractTestPort",
    "DbAssertionPort",
    "EvidencePort",
    "EvidenceResult",
    "ExistingTestsPort",
    "ManualEvidencePort",
    "OutputSnapshotPort",
    "SOURCE_CALLBACK_ASSERTIONS",
    "SOURCE_CONTRACT_TESTS",
    "SOURCE_DB_ASSERTIONS",
    "SOURCE_EXISTING_TESTS",
    "SOURCE_MANUAL_EVIDENCE",
    "SOURCE_OUTPUT_SNAPSHOTS",
    "SourceVerdict",
]
