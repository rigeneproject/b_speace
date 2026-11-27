"""SPEACE-PQB-STD-T007-EN Normative Annex A loader & Clause 7 Conformance Validator."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .benchmark import run_pqb_safeguard_benchmark
from .types import (
    PQBConstitutionalFaultError,
    PQBSafeguardProfile,
    PQBSafeguardValidationError,
)

JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
STANDARD_IDENTIFIER = "SPEACE-PQB-STD-T007-EN"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

NORMATIVE_SCHEMA_FILES: tuple[str, ...] = (
    "pqb_campaign_proposal.schema.json",
    "pqb_safeguard_verdict.schema.json",
    "pqb_conformance_manifest.schema.json",
)


class ConformanceProfileLevel(StrEnum):
    """Three strictly ordered conformance profiles from SPEACE-PQB-STD-T007-EN Clause 7."""

    L1_ADVISORY_CORE = "L1_PQB_ADVISORY_CORE"
    L2_SIMPLEX_PLANT = "L2_PQB_SIMPLEX_PLANT"
    L3_CIVIL_RESILIENCE_C8 = "L3_PQB_CIVIL_RESILIENCE_C8"


PROFILE_REQUIRED_CLAUSES: dict[ConformanceProfileLevel, tuple[str, ...]] = {
    ConformanceProfileLevel.L1_ADVISORY_CORE: (
        "4.1_Authority_Hierarchy",
        "4.5_Numeric_Integrity_RFC8259",
        "5.1_C6_Triadic_Non_Compensability",
        "5.2_C7_Polycrisis_Anti_Risk_Transfer",
    ),
    ConformanceProfileLevel.L2_SIMPLEX_PLANT: (
        "4.1_Authority_Hierarchy",
        "4.2_Q_Sevo_And_H4_Gate",
        "4.3_B_Reference_Assay_And_Wetware_Envelope",
        "4.4_Fast_Slow_Plane_Separation",
        "4.5_Numeric_Integrity_RFC8259",
        "5.1_C6_Triadic_Non_Compensability",
        "5.2_C7_Polycrisis_Anti_Risk_Transfer",
        "6.1_Four_Way_Industrial_Ablation",
        "6.2_T217_Staged_Qualification",
    ),
    ConformanceProfileLevel.L3_CIVIL_RESILIENCE_C8: (
        "4.1_Authority_Hierarchy",
        "4.2_Q_Sevo_And_H4_Gate",
        "4.3_B_Reference_Assay_And_Wetware_Envelope",
        "4.4_Fast_Slow_Plane_Separation",
        "4.5_Numeric_Integrity_RFC8259",
        "5.1_C6_Triadic_Non_Compensability",
        "5.2_C7_Polycrisis_Anti_Risk_Transfer",
        "5.3_C8_Voluntary_Bioregenerative_Habitat",
        "6.1_Four_Way_Industrial_Ablation",
        "6.2_T217_Staged_Qualification",
    ),
}


def schemas_directory() -> Path:
    """Return directory containing the packaged JSON Schema Draft 2020-12 annexes."""
    return Path(__file__).resolve().parent / "schemas"


def load_normative_schema(schema_filename: str) -> dict[str, Any]:
    """Load and verify a packaged Normative Annex A JSON Schema (Draft 2020-12)."""
    if schema_filename not in NORMATIVE_SCHEMA_FILES:
        raise PQBSafeguardValidationError(f"unknown normative schema: {schema_filename!r}")
    path = schemas_directory() / schema_filename
    if not path.is_file():
        raise PQBSafeguardValidationError(f"normative schema file missing: {path}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict) or parsed.get("$schema") != JSON_SCHEMA_DRAFT_2020_12:
        raise PQBSafeguardValidationError(
            f"schema {schema_filename!r} does not declare JSON Schema Draft 2020-12"
        )
    return parsed


def compute_normative_schema_digests() -> dict[str, str]:
    """Compute canonical SHA-256 digests of all packaged Normative Annex A schemas."""
    digests: dict[str, str] = {}
    for fname in NORMATIVE_SCHEMA_FILES:
        schema_obj = load_normative_schema(fname)
        canonical = json.dumps(schema_obj, sort_keys=True, allow_nan=False)
        digests[fname] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digests


@dataclass(frozen=True)
class PQBConformanceManifest:
    """Machine-readable Clause 7 Conformance Declaration & Evidence Bundle."""

    standard_id: str
    schema_version: str
    system_id: str
    conformance_profile: str
    satisfied_clauses: tuple[str, ...]
    profile_sha256: str
    benchmark_report_sha256: str
    schema_digests: dict[str, str]
    eu_ai_act_annex_iv_mapped: bool = True
    ptaa_scc_track_a_only: bool = True
    advisory_only: bool = True
    autonomous_physical_actuation_permitted: bool = False
    manifest_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["satisfied_clauses"] = list(self.satisfied_clauses)
        return payload


def build_conformance_manifest(
    *,
    system_id: str = "b-speace-industry-pqb-reference",
    level: ConformanceProfileLevel = ConformanceProfileLevel.L3_CIVIL_RESILIENCE_C8,
    profile: PQBSafeguardProfile | None = None,
) -> PQBConformanceManifest:
    """Build and SHA-256 seal a Clause 7 conformance manifest backed by T006 benchmark evidence."""
    if not system_id.strip():
        raise PQBSafeguardValidationError("system_id must be non-empty")
    prof = profile if profile is not None else PQBSafeguardProfile()
    bench = run_pqb_safeguard_benchmark(profile=prof)
    if not bench.strictly_beats_baselines:
        raise PQBConstitutionalFaultError(
            "cannot issue conformance manifest when T006 benchmark fails baseline gate"
        )
    clauses = PROFILE_REQUIRED_CLAUSES[level]
    digests = compute_normative_schema_digests()

    draft: dict[str, Any] = {
        "standard_id": STANDARD_IDENTIFIER,
        "schema_version": "1.0.0",
        "system_id": system_id,
        "conformance_profile": level.value,
        "satisfied_clauses": list(clauses),
        "profile_sha256": prof.profile_sha256(),
        "benchmark_report_sha256": bench.report_sha256,
        "schema_digests": digests,
        "eu_ai_act_annex_iv_mapped": True,
        "ptaa_scc_track_a_only": True,
        "advisory_only": True,
        "autonomous_physical_actuation_permitted": False,
    }
    manifest_digest = hashlib.sha256(
        json.dumps(draft, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()

    return PQBConformanceManifest(
        standard_id=STANDARD_IDENTIFIER,
        schema_version="1.0.0",
        system_id=system_id,
        conformance_profile=level.value,
        satisfied_clauses=clauses,
        profile_sha256=prof.profile_sha256(),
        benchmark_report_sha256=bench.report_sha256,
        schema_digests=digests,
        eu_ai_act_annex_iv_mapped=True,
        ptaa_scc_track_a_only=True,
        advisory_only=True,
        autonomous_physical_actuation_permitted=False,
        manifest_sha256=manifest_digest,
    )


def _contains_non_finite(obj: object) -> bool:
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, Mapping):
        return any(_contains_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_contains_non_finite(v) for v in obj)
    return False


def validate_top_level_schema_contract(
    schema_filename: str,
    payload: Mapping[str, Any],
) -> None:
    """Validate top-level required keys, closed-schema additionalProperties & RFC 8259 finiteness."""
    if _contains_non_finite(payload):
        raise PQBSafeguardValidationError("payload contains non-finite float (RFC 8259 violation)")
    schema = load_normative_schema(schema_filename)
    required = set(schema.get("required", []))
    allowed = set(schema.get("properties", {}).keys())
    present = set(payload.keys())

    missing = sorted(required - present)
    if missing:
        raise PQBSafeguardValidationError(f"{schema_filename}: missing required keys {missing}")
    if schema.get("additionalProperties") is False:
        extra = sorted(present - allowed)
        if extra:
            raise PQBSafeguardValidationError(
                f"{schema_filename}: forbidden additional keys {extra}"
            )


def verify_conformance_manifest(manifest_data: Mapping[str, Any]) -> bool:
    """Verify integrity, safety invariants, schema digests & SHA-256 seal of a Clause 7 manifest."""
    try:
        validate_top_level_schema_contract("pqb_conformance_manifest.schema.json", manifest_data)
    except PQBSafeguardValidationError:
        return False

    if manifest_data.get("standard_id") != STANDARD_IDENTIFIER:
        return False
    if manifest_data.get("schema_version") != "1.0.0":
        return False
    if manifest_data.get("advisory_only") is not True:
        return False
    if manifest_data.get("ptaa_scc_track_a_only") is not True:
        return False
    if manifest_data.get("autonomous_physical_actuation_permitted") is not False:
        return False

    raw_level = manifest_data.get("conformance_profile")
    if not isinstance(raw_level, str):
        return False
    try:
        level = ConformanceProfileLevel(raw_level)
    except ValueError:
        return False

    clauses = manifest_data.get("satisfied_clauses")
    if not isinstance(clauses, list) or not all(isinstance(c, str) for c in clauses):
        return False
    required_clauses = set(PROFILE_REQUIRED_CLAUSES[level])
    if not required_clauses.issubset(set(clauses)):
        return False

    for hash_field in ("profile_sha256", "benchmark_report_sha256", "manifest_sha256"):
        val = manifest_data.get(hash_field)
        if not isinstance(val, str) or _SHA256_RE.match(val) is None:
            return False

    expected_digests = compute_normative_schema_digests()
    if manifest_data.get("schema_digests") != expected_digests:
        return False

    draft = {k: v for k, v in manifest_data.items() if k != "manifest_sha256"}
    try:
        recomputed = hashlib.sha256(
            json.dumps(draft, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest()
    except (TypeError, ValueError):
        return False

    sig = manifest_data.get("manifest_sha256")
    return isinstance(sig, str) and recomputed == sig
