"""Tests for the B-SPEACE BCEL equivalence gate catalog."""

from __future__ import annotations

from b_speace.bcel import BCELCatalog, BCELEquivalence


def test_bcel_catalog_contains_functional_and_accidental_entries() -> None:
    catalog = BCELCatalog()
    summary = catalog.summary()
    assert summary["total"] == len(catalog.all())
    assert summary["functional"] >= 4
    assert summary["accidental"] >= 2
    assert summary["functional"] + summary["accidental"] == summary["total"]


def test_bcel_no_consciousness_and_no_ftl_invariants() -> None:
    catalog = BCELCatalog()
    accidental_text = " ".join(e.concept.lower() for e in catalog.accidental())
    assert "consciousness" in accidental_text
    assert "non-local" in accidental_text or "ftl" in accidental_text


def test_bcel_custom_entries_override() -> None:
    custom = (
        BCELEquivalence(
            concept="Custom rule",
            classification="functional",
            digital_rule="Keep as deterministic threshold.",
        ),
    )
    catalog = BCELCatalog(entries=custom)
    assert catalog.summary() == {"total": 1, "functional": 1, "accidental": 0}
