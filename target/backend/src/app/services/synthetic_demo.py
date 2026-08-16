"""SYNTHETIC DEMO — migration slice S-011 pipeline dry-run.

Not a real migrated feature. There is no legacy source for this: the
"legacy behavior" in migration/features/synthetic-demo/ is fabricated to
exercise the discover -> spec -> design -> implement -> review -> verify
pipeline and the migration/judge composite judge (S-001) before any real
feature migration begins, per docs/02-migration-pipeline.md Phase 0
("make the process runnable before migrating production behavior").

See migration/features/synthetic-demo/ for the (labeled-synthetic) feature
card, behavior contract, characterization record, and target design, and
migration/features/synthetic-demo/DRY-RUN-REPORT.md for the dry-run result.
"""


def concatenate(a: str, b: str) -> str:
    """Concatenate two strings. Business rule BR-001 in the synthetic
    behavior contract: exact string concatenation, no normalization."""
    return a + b
