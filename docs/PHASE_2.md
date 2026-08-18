# Phase 2 — Normalization

## Objective

Transform raw EvidenceRecord observations extracted in Phase 1 into normalized, canonical product specifications, with full provenance preservation, deterministic unit conversion, and explicit conflict surfacing.

**Phase 2 does NOT:**
- Resolve conflicts (Phase 3's job)
- Score trust or validate correctness (Phase 3 and Phase 5)
- Enrich with external data (Phase 4)
- Call any LLM API

## Status

| Metric | Value |
|---|---|
| **Status** | ✅ COMPLETE |
| **Products processed** | 12 / 12 |
| **Evidence consumed** | 385 records |
| **Fields normalized** | 48 |
| **Fields conflicted** | 49 |
| **Fields missing** | 35 |
| **Unmapped attributes** | 144 |
| **Parse errors** | 0 |
| **Unknown units** | 0 |
| **Tests** | 518 passed, 3 skipped, 0 failed |
| **Verification checks** | 13 / 13 passed |

## Inputs

Phase 2 consumes Phase 1 output exclusively. It never re-reads original source files.

| Input | Location | Count |
|---|---|---|
| PDF evidence records | `data/processed/<product_id>/pdf_evidence.json` | 1,704 |
| CSV evidence records | `data/processed/<product_id>/csv_evidence.json` | 133 |
| Web evidence records | `data/processed/<product_id>/web_evidence.json` | 0 (HTTP 403) |
| Global evidence | `data/processed/GLOBAL/pdf_evidence.json` | `rated_voltage` (4× duplicated) |
| Dataset manifest | `data/dataset_manifest.json` | 12 products |

## Outputs

| Output | Location | Description |
|---|---|---|
| Normalized product | `data/processed/<product_id>/normalized_product.json` | Per-product normalized output |
| Batch report | `data/processed/normalization_report.json` | Aggregate statistics |

### `normalized_product.json` schema

```json
{
  "product_id": "PIQ-W22SP-4P-1.1",
  "manufacturer": "WEG",
  "model": "W22 Severe Process IE3 (4-pole)",
  "normalization_version": "2.0.0",
  "fields": {
    "rated_power": {
      "canonical_field": "rated_power",
      "canonical_unit": "kW",
      "canonical_value": null,
      "outcome": "conflict",
      "evidence_refs": [ ... ],
      "conflicts": [ ... ],
      "confidence": 0.92
    },
    ...
  },
  "unmapped_evidence": [ ... ],
  "issues": []
}
```

## Architecture

```
data/processed/<product_id>/
  pdf_evidence.json ──┐
  csv_evidence.json ──┼──► MotorNormalizer.load_all_evidence()
  web_evidence.json ──┘         │
GLOBAL/pdf_evidence.json ────────┘
                                 │
                          EvidenceRecord (dict)
                                 │
                    ┌────────────▼─────────────┐
                    │   attribute_mapper        │
                    │   get_mapping(attribute)  │
                    └────────┬──────┬──────────┘
                    CANONICAL│ METADATA/SKIP
                             │
                    ┌────────▼──────────────────┐
                    │   value_parser            │
                    │   parse_numeric / parse_ip│
                    └────────┬──────────────────┘
                             │ (float, raw_unit)
                    ┌────────▼──────────────────┐
                    │   unit_converter          │
                    │   convert_value()         │
                    └────────┬──────────────────┘
                             │ (canonical_value, canonical_unit)
                    ┌────────▼──────────────────┐
                    │   EvidenceRef (provenance) │
                    └────────┬──────────────────┘
                             │
                    ┌────────▼──────────────────┐
                    │   _assemble_field()        │
                    │   conflict detection       │
                    └────────┬──────────────────┘
                             │
                    NormalizedField (per canonical field)
                             │
                    NormalizedProduct (per product)
```

## Implementation

### Module structure

| Module | Responsibility |
|---|---|
| `normalization/models.py` | Data structures: `NormalizedField`, `NormalizedProduct`, `EvidenceRef`, `ConflictRecord`, `NormalizationIssue`, `NormalizationReport` |
| `normalization/unit_converter.py` | Deterministic unit conversion (W→kW, HP→kW, g→kg, lb→kg, efficiency normalization, PF normalization) |
| `normalization/value_parser.py` | Safe raw string parsing — raises `ValueParseError` on failure, never fabricates |
| `normalization/attribute_mapper.py` | Explicit mapping from evidence attribute names to canonical MotorProduct fields |
| `normalization/normalizer.py` | `MotorNormalizer` (single product) and `BatchNormalizer` (all 12 products) |
| `normalization/base.py` | `BaseNormalizer` abstract interface (Phase 0 stub, extended here) |
| `normalization/__init__.py` | Public package exports |

## Test Results

```
tests/test_normalization_units.py       ── unit converter (35 tests)
tests/test_normalization_values.py      ── value parser (28 tests)
tests/test_normalization_mapping.py     ── attribute mapper (28 tests)
tests/test_normalization_provenance.py  ── provenance preservation (20 tests)
tests/test_phase2.py                    ── integration tests (141 tests)
```

**Total: 518 passed, 3 skipped, 0 failed** (3 skips are pre-existing LLM connectivity tests requiring live API)

## Real Dataset Results

### Per-product summary (4-pole motors)

| Product | Normalized | Conflicted | Missing | Unmapped |
|---|---|---|---|---|
| PIQ-W22SP-4P-1.1  | 4 | 5 | 2 | 12 |
| PIQ-W22SP-4P-1.5  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-2.2  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-3.0  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-4.0  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-5.5  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-7.5  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-9.2  | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-11   | 4 | 4 | 3 | 12 |
| PIQ-W22SP-4P-15   | 4 | 4 | 3 | 12 |
| PIQ-W22SP-6P-0.75 | 4 | 4 | 3 | 12 |
| PIQ-W22SP-6P-1.1  | 4 | 4 | 3 | 12 |

**Key:**
- **Normalized**: Fields with a resolved canonical value (`rated_voltage`, `rated_speed`, `weight`, `ip_rating`)
- **Conflicted**: Fields where sources disagree (no winner picked)
- **Missing**: Fields with no evidence (`frequency`, `poles`, and one other per product)
- **Unmapped**: Evidence records preserved as-is (torque, inertia, partial-load data, etc.)

### Conflict breakdown for PIQ-W22SP-4P-1.1

| Field | Source A | Value A | Source B | Value B | Action |
|---|---|---|---|---|---|
| `rated_current` | PDF | 2.34 A | CSV | 7.22 A | Preserved as conflict |
| `rated_power` | PDF (kW col) | 1.1 kW | PDF (HP col→kW) | 1.11855 kW | Preserved as conflict |
| `efficiency` | PDF (full load) | 84.8 % | CSV (50% load) | 83.0 % | Preserved as conflict |
| `power_factor` | PDF (full load) | 0.80 | CSV (50% load) | 0.59 | Preserved as conflict |
| `frame_size` | PDF | "90S" | CSV | "L90S" | Preserved as conflict |

## Known Limitations

1. **No `frequency` evidence**: The WEG brochure states the frequency in a header section not captured as per-product evidence by Phase 1. Phase 1 should be augmented to extract the "50 Hz" global parameter. Frequencies are currently `Missing` for all products.
2. **No `poles` evidence**: Poles are encoded in the product ID (e.g. `4P`) but not extracted as an evidence field by Phase 1. A manifest-level inference step could populate this in Phase 3.
3. **Partial-load efficiency not a canonical field**: The CSV captures 50%-load efficiency (83.0%), but Phase 0's canonical schema has only one `efficiency` field. This causes persistent conflicts between CSV and PDF full-load efficiency. Phase 3 should resolve by load-point disambiguation.
4. **HP→kW precision conflict**: The HP column creates a nominal conflict (`1.5 HP × 0.7457 = 1.11855 kW ≠ 1.1 kW`). This is a real rounding artifact of the dual-unit brochure table.

## Handoff to Phase 3 — Validation

Phase 3 receives as input from Phase 2:
- `normalized_product.json` per product
- `NormalizationOutcome` per field (`normalized` / `conflict` / `missing`)
- `ConflictRecord` per conflict with both evidence sources preserved
- All `EvidenceRef` provenance for trace-back

Phase 3 responsibilities:
- Semantic validation: are values physically plausible?
- Conflict resolution: which evidence source is authoritative?
- Cross-field consistency: does power × 1000 / (√3 × voltage × PF × efficiency) ≈ current?
- Missing value inference from context (e.g. poles from product ID)
