"""Tests for the SYNTHETIC DEMO feature (migration slice S-011). Not a real
feature — see app.services.synthetic_demo and
migration/features/synthetic-demo/."""

from app.services.synthetic_demo import concatenate


def test_concatenate_matches_synthetic_characterization_record() -> None:
    # Fixture from migration/features/synthetic-demo/characterization-record.md
    assert concatenate("foo", "bar") == "foobar"


def test_concatenate_is_exact_no_normalization() -> None:
    assert concatenate("Foo", "Bar") == "FooBar"
    assert concatenate("", "x") == "x"
