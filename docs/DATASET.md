# ProductIQ Dataset — Provenance and Collection Notes

**Last Updated:** 2026-08-18  
**Phase:** 0  
**Total Motors:** 12  
**Manufacturers:** 1 (WEG)  

---

## Collection Methodology

Phase 0 targets 10–15 real industrial motors with three source types per motor: manufacturer PDF, manufacturer web reference, and legacy-style CSV. The dataset was collected following strict provenance rules:

- **No fabrication.** Every data value must trace to a real manufacturer source.
- **Provenance-first.** CSV data is explicitly labeled as "derived from brochure" — not claimed to be manufacturer-issued.
- **Missing is honest.** Fields absent from the source are left as `Unknown` in the schema, not guessed.

---

## Primary Source

**Document:** WEG W22 Severe Process IE3 Brochure  
**File:** `data/pdf/WEG_W22_Severe_Process_IE3_Brochure.pdf`  
**Original URL:** https://static.weg.net/medias/downloadcenter/hf9/hd0/WEG-w22-severe-process-european-market-50058022-brochure-english-web.pdf  
**Status:** Real manufacturer PDF — downloaded and stored locally.  
**Size:** ~2.5 MB  
**Content:** Technical data tables for WEG W22 Severe Process IE3 motors at 400 V, 50 Hz  

---

## Motor Records

### 4-Pole Motors (400 V, 50 Hz) — Source: Brochure p.5

| Product ID | Model | Rated Power | Speed (rpm) | Efficiency | PF | Current (A) | Weight (kg) | Frame |
|---|---|---|---|---|---|---|---|---|
| PIQ-W22SP-4P-1.1 | W22 SP IE3 (4P) | 1.1 kW | 1455 | 83.0% | 0.59 | 7.22 | 19.5 | L90S |
| PIQ-W22SP-4P-1.5 | W22 SP IE3 (4P) | 1.5 kW | 1450 | 84.0% | 0.58 | 7.4 | 23.0 | 90L |
| PIQ-W22SP-4P-2.2 | W22 SP IE3 (4P) | 2.2 kW | 1435 | 86.5% | 0.60 | 7.4 | 31.5 | 100L |
| PIQ-W22SP-4P-3.0 | W22 SP IE3 (4P) | 3.0 kW | 1440 | 87.0% | 0.60 | 7.8 | 37.5 | L100L |
| PIQ-W22SP-4P-4.0 | W22 SP IE3 (4P) | 4.0 kW | 1450 | 88.7% | 0.60 | 7.0 | 44.0 | 112M |
| PIQ-W22SP-4P-5.5 | W22 SP IE3 (4P) | 5.5 kW | 1465 | 90.0% | 0.67 | 8.5 | 69.0 | 132S |
| PIQ-W22SP-4P-7.5 | W22 SP IE3 (4P) | 7.5 kW | 1465 | 91.0% | 0.68 | 8.5 | 78.0 | 132M |
| PIQ-W22SP-4P-9.2 | W22 SP IE3 (4P) | 9.2 kW | 1475 | 90.0% | 0.66 | 7.2 | 109.0 | 160M |
| PIQ-W22SP-4P-11 | W22 SP IE3 (4P) | 11.0 kW | 1470 | 91.0% | 0.65 | 7.0 | 123.0 | 160M |
| PIQ-W22SP-4P-15 | W22 SP IE3 (4P) | 15.0 kW | 1470 | 91.8% | 0.65 | 7.3 | 145.0 | 160L |

### 6-Pole Motors (400 V, 50 Hz) — Source: Brochure p.6

| Product ID | Model | Rated Power | Speed (rpm) | Efficiency | PF | Current (A) | Weight (kg) | Frame |
|---|---|---|---|---|---|---|---|---|
| PIQ-W22SP-6P-0.75 | W22 SP IE3 (6P) | 0.75 kW | 940 | 76.5% | 0.49 | 5.2 | 22.0 | L90S |
| PIQ-W22SP-6P-1.1 | W22 SP IE3 (6P) | 1.1 kW | 945 | 80.5% | 0.51 | 4.9 | 28.5 | 100L |

---

## Source Types Per Product

| Product ID | PDF | Web URL | CSV |
|---|---|---|---|
| PIQ-W22SP-4P-1.1 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-1.5 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-2.2 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-3.0 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-4.0 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-5.5 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-7.5 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-9.2 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-11 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-4P-15 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-6P-0.75 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |
| PIQ-W22SP-6P-1.1 | ✅ Real | ✅ Catalog ref | ✅ Brochure-derived |

---

## Provenance Classification

| Classification | Count | Explanation |
|---|---|---|
| `real_source_collected` | 12 | All 12 motors |
| `real_source_identified_not_downloadable` | 0 | None |
| `source_unavailable` | 0 | None |
| `synthetic_development_fallback` | 0 | None — zero synthetic data used |

---

## Known Data Gaps (intentionally preserved as Unknown)

These fields are **not present** in the brochure table rows and must remain `Unknown` until Phase 1 extraction can source them:

- **`rated_voltage`** — Specified as 400 V in the table header but not per-row. Phase 1 should capture this as a table-wide constant.
- **`frequency`** — Specified as 50 Hz globally, not per-row. Same treatment as voltage.
- **`ip_rating`** — The brochure describes "Severe Process" sealing (IP56+) in prose, not in the performance table. Phase 1 must extract from text sections.
- **`poles`** — Can be inferred from product_id naming convention and table section (IV pole = 4, VI pole = 6), but requires explicit extraction logic in Phase 1.

---

## Web References

All 12 web references point to the official WEG W22 catalog family page:  
`https://www.weg.net/catalog/weg/CI/en/Electric-Motors/Low-Voltage-IEC-Motors/Three-Phase/W22/`

**Note:** These are catalog-family URLs, not per-product deep links. Phase 1 should resolve exact product URLs from the WEG catalog API or sitemap during web extraction.

---

## CSV Provenance Note

The file `data/csv/legacy_motors.csv` is a **legacy-style representation derived from the cited WEG brochure rows**. It is NOT a manufacturer-issued WEG legacy CSV file. This distinction is explicitly documented in `data/dataset_manifest.json` under each product's `csv.note` field. 

In the schema, values extracted from this CSV must be labeled `status=Inferred` (not `Verified`), since the CSV is a transcription of the PDF data, not an independent source.

---

## Phase 1 Dataset Expansion Recommendation

For Phase 1, add motors from at least one additional manufacturer to enable cross-manufacturer conflict detection:

**Recommended additions:**
- ABB IE3 motors (M2BAX or M3BP series) — ABB publishes machine-readable catalogs
- Siemens SIMOTICS General Purpose motors — Siemens provides downloadable datasheets
- SEW-Eurodrive DR series — readily available PDFs

This will create the first real-world conflict scenarios where, for example, two manufacturers measure efficiency under slightly different test conditions (IEC 60034-2-1 vs. older standards), exercising the `Conflicted` status path for the first time.
