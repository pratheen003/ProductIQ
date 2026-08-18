"""
ProductIQ Motor Normalizer — Phase 2
======================================
Main orchestrator: loads Phase 1 evidence → normalizes → produces NormalizedProduct.

Pipeline per product:
  1. Load evidence from data/processed/<product_id>/{pdf,csv,web}_evidence.json
  2. For each EvidenceRecord:
       a. Look up attribute mapping (canonical / unmapped / metadata / skip)
       b. Parse raw_value into float or string
       c. Convert to canonical unit if needed
       d. Build EvidenceRef with full provenance
  3. Assemble per-canonical-field: collect all EvidenceRefs
  4. Detect conflicts: multiple refs with different normalized values
  5. Construct NormalizedField for each canonical field
  6. Collect unmapped evidence and normalization issues
  7. Return NormalizedProduct

Design commitments:
- No LLM calls.
- No fabricated values.
- All conflicts surfaced, never resolved.
- All provenance preserved.
- Malformed inputs → NormalizationIssue, not crash.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from productiq.schema import CANONICAL_UNITS

from productiq.normalization.base import BaseNormalizer
from productiq.normalization.models import (
    ConflictRecord,
    EvidenceRef,
    NormalizationIssue,
    NormalizationOutcome,
    NormalizedField,
    NormalizedProduct,
    NormalizationReport,
)
from productiq.normalization.unit_converter import (
    UnitConversionError,
    convert_value,
    is_equivalent,
)
from productiq.normalization.value_parser import (
    ValueParseError,
    parse_frame_size,
    parse_ip_rating,
    parse_numeric,
    parse_string_field,
)
from productiq.normalization.attribute_mapper import (
    MappingKind,
    get_mapping,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# String-typed canonical fields (not parsed as float)
# ---------------------------------------------------------------------------
_STRING_FIELDS = {"ip_rating", "frame_size"}
_INT_FIELDS    = {"poles"}


# ---------------------------------------------------------------------------
# Helper: build EvidenceRef from a raw EvidenceRecord dict
# ---------------------------------------------------------------------------

def _make_evidence_ref(rec: dict) -> EvidenceRef:
    """Build an EvidenceRef (provenance pointer) from a raw evidence dict."""
    return EvidenceRef(
        source_id    = rec.get("source_id", ""),
        source_type  = rec.get("source_type", ""),
        product_id   = rec.get("product_id", ""),
        attribute    = rec.get("attribute", ""),
        raw_value    = rec.get("raw_value", ""),
        raw_unit     = rec.get("unit"),
        parsed_value = rec.get("value"),   # already-parsed float from Phase 1
        method       = rec.get("method", "unknown"),
        confidence   = float(rec.get("confidence", 0.0)),
        page         = rec.get("page"),
        row          = rec.get("row"),
        column       = rec.get("column"),
        url          = rec.get("url"),
        section      = rec.get("section"),
    )


# ---------------------------------------------------------------------------
# Internal: normalize one evidence record to (canonical_value, canonical_unit)
# ---------------------------------------------------------------------------

@dataclass
class _NormResult:
    """Intermediate result for one evidence record's normalization attempt."""
    canonical_field: str
    canonical_value: Optional[object]     # float, int, or str
    canonical_unit: Optional[str]
    evidence_ref: EvidenceRef
    outcome: NormalizationOutcome
    issue: Optional[NormalizationIssue] = None


def _normalize_one_record(
    rec: dict,
    canonical_field: str,
) -> _NormResult:
    """
    Normalize a single EvidenceRecord dict into a canonical (value, unit).

    Never raises — returns a NormResult with outcome=PARSE_ERROR or
    UNKNOWN_UNIT instead.
    """
    eref = _make_evidence_ref(rec)
    raw_value = rec.get("raw_value", "")
    raw_unit  = rec.get("unit")
    pre_parsed_value = rec.get("value")  # float already parsed by Phase 1

    # --- String fields: ip_rating, frame_size ---
    if canonical_field == "ip_rating":
        try:
            canonical_value = parse_ip_rating(raw_value)
            return _NormResult(
                canonical_field=canonical_field,
                canonical_value=canonical_value,
                canonical_unit=None,
                evidence_ref=eref,
                outcome=NormalizationOutcome.PASSTHROUGH,
            )
        except ValueParseError as e:
            issue = NormalizationIssue(
                canonical_field=canonical_field,
                evidence_attribute=rec.get("attribute", ""),
                raw_value=raw_value,
                raw_unit=raw_unit,
                outcome=NormalizationOutcome.PARSE_ERROR,
                reason=str(e),
                source_ref=eref,
            )
            return _NormResult(
                canonical_field=canonical_field,
                canonical_value=None,
                canonical_unit=None,
                evidence_ref=eref,
                outcome=NormalizationOutcome.PARSE_ERROR,
                issue=issue,
            )

    if canonical_field == "frame_size":
        canonical_value = parse_frame_size(raw_value)
        if not canonical_value:
            issue = NormalizationIssue(
                canonical_field=canonical_field,
                evidence_attribute=rec.get("attribute", ""),
                raw_value=raw_value,
                raw_unit=raw_unit,
                outcome=NormalizationOutcome.PARSE_ERROR,
                reason="Empty frame_size string",
                source_ref=eref,
            )
            return _NormResult(
                canonical_field=canonical_field,
                canonical_value=None,
                canonical_unit=None,
                evidence_ref=eref,
                outcome=NormalizationOutcome.PARSE_ERROR,
                issue=issue,
            )
        return _NormResult(
            canonical_field=canonical_field,
            canonical_value=canonical_value,
            canonical_unit=None,
            evidence_ref=eref,
            outcome=NormalizationOutcome.PASSTHROUGH,
        )

    # --- Numeric fields ---
    # Prefer pre-parsed float from Phase 1 if available and raw_value is plain
    numeric_value: Optional[float] = None
    parsed_unit: Optional[str]     = raw_unit

    if pre_parsed_value is not None:
        # Phase 1 already parsed this value — use it
        numeric_value = float(pre_parsed_value)
        parsed_unit   = raw_unit  # rely on Phase 1's unit field
    else:
        # Parse from raw_value string (handles "1.1 kW", "84.8 %", etc.)
        try:
            numeric_value, embedded_unit = parse_numeric(raw_value, field_name=canonical_field)
            # Prefer the evidence record's unit field; fall back to embedded
            if parsed_unit is None and embedded_unit:
                parsed_unit = embedded_unit
        except ValueParseError as e:
            issue = NormalizationIssue(
                canonical_field=canonical_field,
                evidence_attribute=rec.get("attribute", ""),
                raw_value=raw_value,
                raw_unit=raw_unit,
                outcome=NormalizationOutcome.PARSE_ERROR,
                reason=str(e),
                source_ref=eref,
            )
            return _NormResult(
                canonical_field=canonical_field,
                canonical_value=None,
                canonical_unit=None,
                evidence_ref=eref,
                outcome=NormalizationOutcome.PARSE_ERROR,
                issue=issue,
            )

    # --- Unit conversion ---
    try:
        can_value, can_unit = convert_value(canonical_field, numeric_value, parsed_unit)
        # Determine outcome: NORMALIZED (converted) or PASSTHROUGH (already canonical)
        canonical_unit_expected = CANONICAL_UNITS.get(canonical_field)
        if parsed_unit == canonical_unit_expected or parsed_unit == can_unit:
            outcome = NormalizationOutcome.PASSTHROUGH
        else:
            outcome = NormalizationOutcome.NORMALIZED

        # Integer fields (poles)
        if canonical_field in _INT_FIELDS:
            can_value = int(round(can_value)) if can_value is not None else None

        return _NormResult(
            canonical_field=canonical_field,
            canonical_value=can_value,
            canonical_unit=can_unit,
            evidence_ref=eref,
            outcome=outcome,
        )

    except UnitConversionError as e:
        issue = NormalizationIssue(
            canonical_field=canonical_field,
            evidence_attribute=rec.get("attribute", ""),
            raw_value=raw_value,
            raw_unit=raw_unit,
            outcome=NormalizationOutcome.UNKNOWN_UNIT,
            reason=str(e),
            source_ref=eref,
        )
        return _NormResult(
            canonical_field=canonical_field,
            canonical_value=None,
            canonical_unit=None,
            evidence_ref=eref,
            outcome=NormalizationOutcome.UNKNOWN_UNIT,
            issue=issue,
        )


# ---------------------------------------------------------------------------
# Main normalizer
# ---------------------------------------------------------------------------

class MotorNormalizer(BaseNormalizer):
    """
    Phase 2 normalizer for WEG motor evidence records.

    Usage:
        normalizer = MotorNormalizer(data_dir=Path("data"))
        product = normalizer.normalize_product(product_entry, product_id)
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"

    # BaseNormalizer abstract method — not used in batch flow but required
    def normalize(self, field_name: str, field_value) -> object:
        """Normalize a single FieldValue (BaseNormalizer interface)."""
        raise NotImplementedError(
            "Use normalize_product() for Phase 2 full-product normalization."
        )

    # -----------------------------------------------------------------------
    # Evidence loading
    # -----------------------------------------------------------------------

    def _load_evidence_file(self, path: Path) -> List[dict]:
        """Load evidence records from a JSON file. Returns empty list on failure."""
        if not path.exists():
            logger.warning("Evidence file not found: %s", path)
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read %s: %s", path, e)
            return []

        # File is an ExtractionResult dict with "evidence" key
        if isinstance(data, dict):
            if data.get("status") == "failed":
                logger.info("Source %s failed during extraction — 0 evidence records", path)
                return []
            return data.get("evidence", [])
        # If it's already a plain list
        if isinstance(data, list):
            return data
        return []

    def load_all_evidence(self, product_id: str) -> List[dict]:
        """Load all evidence records for a product (PDF + CSV + web)."""
        product_dir = self.processed_dir / product_id
        all_records: List[dict] = []

        for source_file in ("pdf_evidence.json", "csv_evidence.json", "web_evidence.json"):
            path = product_dir / source_file
            records = self._load_evidence_file(path)
            all_records.extend(records)

        logger.debug("Loaded %d evidence records for %s", len(all_records), product_id)
        return all_records

    def load_global_evidence(self) -> List[dict]:
        """Load global/shared evidence (e.g. rated_voltage from brochure header)."""
        return self._load_evidence_file(self.processed_dir / "GLOBAL" / "pdf_evidence.json")

    # -----------------------------------------------------------------------
    # Normalize a single product
    # -----------------------------------------------------------------------

    def normalize_product(
        self,
        manifest_entry: dict,
        product_id: str,
    ) -> NormalizedProduct:
        """
        Normalize all evidence for one product into a NormalizedProduct.

        Args:
            manifest_entry: Row from dataset_manifest.json for this product.
            product_id:     Canonical product identifier string.

        Returns:
            NormalizedProduct (never raises — issues captured internally).
        """
        manufacturer = manifest_entry.get("manufacturer", "Unknown")
        model        = manifest_entry.get("model", "Unknown")

        product = NormalizedProduct(
            product_id=product_id,
            manufacturer=manufacturer,
            model=model,
        )

        # --- Load evidence ---
        all_evidence = self.load_all_evidence(product_id)
        global_evidence = self.load_global_evidence()

        # Product-specific evidence first, then global (so product values take priority)
        all_evidence_combined = all_evidence + global_evidence

        if not all_evidence_combined:
            product.normalization_notes.append(
                "No evidence records found — all fields will be Missing."
            )

        # --- Accumulate norm results per canonical field ---
        # field_name → List[_NormResult]
        field_results: Dict[str, List[_NormResult]] = {
            f: [] for f in CANONICAL_UNITS
        }
        unmapped_refs: List[EvidenceRef] = []
        issues: List[NormalizationIssue] = []

        for rec in all_evidence_combined:
            attribute = rec.get("attribute", "")
            canonical_field, kind, note = get_mapping(attribute)

            if kind == MappingKind.SKIP or kind == MappingKind.METADATA:
                # Intentionally excluded from normalization
                continue

            if kind == MappingKind.UNMAPPED or canonical_field is None:
                # Preserve as unmapped — do not silently drop
                eref = _make_evidence_ref(rec)
                unmapped_refs.append(eref)
                continue

            # CANONICAL: normalize
            result = _normalize_one_record(rec, canonical_field)
            if result.issue:
                issues.append(result.issue)
            field_results[canonical_field].append(result)

        # --- Assemble NormalizedField for each canonical field ---
        for field_name, results in field_results.items():
            canonical_unit = CANONICAL_UNITS.get(field_name)
            nf = self._assemble_field(field_name, canonical_unit, results)
            product.fields[field_name] = nf

        product.unmapped_evidence = unmapped_refs
        product.issues = issues

        logger.info(
            "Normalized %s: %d fields, %d normalized, %d conflicts, %d issues, %d unmapped",
            product_id,
            product.field_count,
            product.normalized_count,
            product.conflict_count,
            product.issue_count,
            len(product.unmapped_evidence),
        )
        return product

    # -----------------------------------------------------------------------
    # Assemble a NormalizedField from multiple norm results
    # -----------------------------------------------------------------------

    def _assemble_field(
        self,
        field_name: str,
        canonical_unit: Optional[str],
        results: List[_NormResult],
    ) -> NormalizedField:
        """
        Given all normalization results for one canonical field,
        produce a NormalizedField with conflict detection.
        """
        # Filter to successful results only
        successful = [r for r in results if r.canonical_value is not None]

        if not successful:
            return NormalizedField(
                canonical_field=field_name,
                canonical_unit=canonical_unit,
                canonical_value=None,
                outcome=NormalizationOutcome.MISSING,
                evidence_refs=[r.evidence_ref for r in results],
                confidence=None,
                notes=["No evidence available for this field."] if not results else
                      ["Evidence present but all records failed to normalize."],
            )

        # Build evidence refs list (ALL records, including failed ones)
        all_refs = [r.evidence_ref for r in results]

        # Detect conflicts among successful normalizations
        conflicts: List[ConflictRecord] = []
        representative = successful[0]

        for other in successful[1:]:
            # String fields: compare as strings
            if field_name in _STRING_FIELDS:
                if str(representative.canonical_value) != str(other.canonical_value):
                    conflicts.append(ConflictRecord(
                        canonical_field=field_name,
                        value_a=None,
                        unit_a=representative.canonical_unit,
                        source_a=representative.evidence_ref,
                        value_b=None,
                        unit_b=other.canonical_unit,
                        source_b=other.evidence_ref,
                        note=(
                            f"String conflict: '{representative.canonical_value}' "
                            f"vs '{other.canonical_value}'"
                        ),
                    ))
            else:
                # Numeric comparison
                v_a = float(representative.canonical_value) if representative.canonical_value is not None else None
                v_b = float(other.canonical_value) if other.canonical_value is not None else None
                if not is_equivalent(
                    field_name,
                    v_a,
                    representative.canonical_unit,
                    v_b,
                    other.canonical_unit,
                ):
                    conflicts.append(ConflictRecord(
                        canonical_field=field_name,
                        value_a=v_a,
                        unit_a=representative.canonical_unit,
                        source_a=representative.evidence_ref,
                        value_b=v_b,
                        unit_b=other.canonical_unit,
                        source_b=other.evidence_ref,
                        note=(
                            f"Numeric conflict: {v_a} {representative.canonical_unit} "
                            f"vs {v_b} {other.canonical_unit}"
                        ),
                    ))

        # Determine outcome and canonical value
        if conflicts:
            # CONFLICT: preserve both evidence refs, do not pick a winner
            canonical_value = None
            outcome = NormalizationOutcome.CONFLICT
        else:
            # All agree (or single source): use representative value
            canonical_value = representative.canonical_value
            outcome = representative.outcome

        # Aggregate confidence: average of all successful results
        confidence_values = [r.evidence_ref.confidence for r in successful]
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None

        return NormalizedField(
            canonical_field=field_name,
            canonical_unit=canonical_unit,
            canonical_value=canonical_value,
            outcome=outcome,
            evidence_refs=all_refs,
            conflicts=conflicts,
            confidence=round(avg_confidence, 4) if avg_confidence is not None else None,
        )


# ---------------------------------------------------------------------------
# Batch normalizer
# ---------------------------------------------------------------------------

class BatchNormalizer:
    """
    Batch normalization runner for all products in the dataset manifest.

    Usage:
        batch = BatchNormalizer(data_dir=Path("data"))
        report = batch.run_all(output_dir=Path("data/processed"))
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self._normalizer = MotorNormalizer(data_dir=self.data_dir)

    def load_manifest(self) -> List[dict]:
        """Load the dataset manifest."""
        manifest_path = self.data_dir / "dataset_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        raise ValueError(f"Unexpected manifest format: {type(data)}")

    def run_all(self, output_dir: Optional[Path] = None) -> NormalizationReport:
        """
        Normalize all products from the manifest and save outputs.

        Args:
            output_dir: Directory where normalized_product.json files are written.
                        Defaults to data/processed/<product_id>/.

        Returns:
            NormalizationReport with batch statistics.
        """
        manifest = self.load_manifest()
        report = NormalizationReport()
        report.products_processed = len(manifest)

        for entry in manifest:
            product_id = entry.get("product_id", "")
            if not product_id:
                logger.warning("Manifest entry missing product_id: %s", entry)
                report.products_failed += 1
                continue

            try:
                normalized = self._normalizer.normalize_product(entry, product_id)

                # Save output
                if output_dir is not None:
                    out_dir = output_dir / product_id
                else:
                    out_dir = self.data_dir / "processed" / product_id
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / "normalized_product.json"
                out_path.write_text(normalized.to_json(), encoding="utf-8")
                logger.info("Saved normalized output: %s", out_path)

                # Accumulate statistics
                report.products_succeeded += 1
                report.evidence_consumed  += len(normalized.unmapped_evidence) + sum(
                    len(f.evidence_refs) for f in normalized.fields.values()
                )
                for f in normalized.fields.values():
                    if f.outcome in (NormalizationOutcome.NORMALIZED, NormalizationOutcome.PASSTHROUGH):
                        report.fields_normalized += 1
                    elif f.outcome == NormalizationOutcome.CONFLICT:
                        report.fields_conflicted += 1
                    elif f.outcome == NormalizationOutcome.MISSING:
                        report.fields_missing += 1

                report.unmapped_attrs += len(normalized.unmapped_evidence)
                for issue in normalized.issues:
                    if issue.outcome == NormalizationOutcome.PARSE_ERROR:
                        report.parse_errors += 1
                    elif issue.outcome == NormalizationOutcome.UNKNOWN_UNIT:
                        report.unknown_units += 1

            except Exception as e:
                logger.error("Failed to normalize product %s: %s", product_id, e)
                report.products_failed += 1

        # Save batch report
        report_path = self.data_dir / "processed" / "normalization_report.json"
        report_path.write_text(report.to_json(), encoding="utf-8")
        logger.info("Saved normalization report: %s", report_path)

        return report
