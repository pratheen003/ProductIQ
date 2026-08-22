# ProductIQ — Judge Demo & Presentation Guide
## UniHack 2026 / Unilog Hackathon Presentation Manual

---

## 1. 30-Second Elevator Pitch

> **"ProductIQ is an evidence-first product intelligence platform that transforms noisy, fragmented B2B catalog and engineering data into structured, explainable, commerce-ready intelligence.**
> 
> Unlike traditional pipelines that use black-box LLMs to silently guess missing values or overwrite conflicting specs, ProductIQ enforces mathematical physics validation, multi-source conflict detection, and strict zero-fabrication discipline. It delivers verified catalog outputs matching Unilog's exact 252-column delivery format while keeping data quality and provenance completely transparent."

---

## 2. 1-Minute Executive Summary

Industrial distributors and enterprise catalog managers receive product data scattered across PDFs, messy legacy CSVs, and distributor portals. This data is filled with incompatible units, contradictory manufacturer claims, and missing specifications. 

Existing solutions either rely on expensive human curation or naive LLM prompts that hallucinate missing values and silently pick arbitrary winners when data disagrees.

**ProductIQ solves this through two complementary pipelines:**
1. **Industrial Electric Motors Pipeline (`productiq/`):** Full 6-phase multimodal extraction from PDFs, CSVs, and web sources with deterministic electromechanical physics validation, grounded AI enrichment, and human-in-the-loop conflict resolution.
2. **Unilog Catalog Intelligence Pipeline (`productiq_catalog/`):** High-speed batch processing across 1,000 real catalog items with 63-entry decimal-fraction parsing, 39.2% cross-column brand conflict detection, a Dual-Mechanism Evaluation framework (100% fidelity on gold standard $n=2$, 100% vocabulary compliance on $n=1,000$), and native 252-column `.xlsx` delivery format export.

---

## 3. 3-Minute Judge Demo Script (Step-by-Step)

| Step | Action in UI / Code | What Judge Sees | What to Say |
|:---:|---|---|---|
| **1** | Open `/catalog` (Catalog Dashboard) | Live metrics: **100% Approved LOV Compliance**, **39.2% Conflict Detection**, **9,434+ rows/sec** throughput, 4-tier distribution. | *"Here is the Catalog Dashboard evaluating 1,000 real Unilog input rows in 106 milliseconds. Notice that 100% of populated fields conform to verified reference vocabulary with 0% invented values."* |
| **2** | Point to **Conflict Detection Rate (39.2%)** | 392 detected cross-column brand conflicts with sample cards. | *"In the raw input, distributor columns constantly contradict each other (e.g. TREX vs Boise Cascade). ProductIQ catches all 392 conflicts rather than silently picking an arbitrary winner."* |
| **3** | Click **"Explore 1,000 Items"** (`/catalog/products`) | Paginated interactive table with filters for `Verified`, `Inferred`, `Conflicted`, and `Unknown`. | *"Judges can inspect every single row. If we filter by 'Conflicted', we see exact reasons. If we filter by 'Unknown', we see our no-fabrication boundary in action."* |
| **4** | Open a Conflicted Product (`/catalog/products/10`) | Side-by-side display of `E1_Brand`, `Unilog_Brand`, `DIB_Brand`, `Part_Manuf` with warning banner. | *"Here, E1 claims 'DEWALT' while DIB claims 'Black & Decker'. ProductIQ highlights the disagreement and preserves both pieces of evidence for auditability."* |
| **5** | Click **"Gold Standard (n=2)"** (`/catalog/gold-standard`) | Field-by-field verification of Row 1 (`PDSH4816AF`) and Row 2 (`WDTS7024RZ`) with **100.0% Exact Match**. | *"This is Mechanism A. Against the available delivery-format ground truth, our pipeline reproduces the exact manufacturer, brand trademark (FRIGIDAIRE®), product name, and classpath with 100% fidelity."* |
| **6** | Click **"Download Delivery Format (.xlsx)"** | Browser downloads `productiq_delivery_output.xlsx` (604 KB). | *"Per the submission guidelines, we generate the exact 252-column delivery format workbook with frozen headers, fully populated enriched attributes, and genuinely blank unpopulated cells."* |
| **7** | Switch to **Motor Intelligence (`/`)** | Interactive motor specs, efficiency curves, physics gauge, and `rated_current` conflict gate (2.34A PDF vs 7.22A CSV). | *"The same architecture powers deep engineering validation: here on electric motors, deterministic torque-power-speed formulas catch mislabeled torque values before they ever reach customers."* |

---

## 4. 5-Minute Technical Deep Dive

```
RAW SOURCES ────────► MULTI-SOURCE EXTRACTION ────────► DETERMINISTIC NORMALIZATION
(PDF, CSV, Web)       • Immutable EvidenceRecord        • Canonical Units (SI & Imperial)
                      • Strict Source Provenance         • 63-Entry Decimal Fractions
                                                                   │
┌──────────────────────────────────────────────────────────────────┘
▼
DETERMINISTIC VALIDATION & CONFLICT DETECTION
• Electromechanical Formulas (T = P*60 / 2*pi*N, Slip, Efficiency)
• Cross-Column Brand Disagreement Flagging (39.2% rate)
• Controlled 4-Tier Trust Status (Verified, Inferred, Conflicted, Unknown)
                               │
┌──────────────────────────────┘
▼
DUAL-MECHANISM EVALUATION & COMMERCE PACKAGING
• Mechanism A: Gold-Standard Proof (100% fidelity on n=2)
• Mechanism B: Volume Rule & Vocabulary Governance (n=1,000)
• Exact 252-Header Delivery Export (.xlsx / .csv) + Next.js UI
```

---

## 5. Frequently Asked Questions (FAQ)

### Q1: "Why is Mechanism A evaluated on only 2 rows? Is 100% accuracy real?"
> **Answer:** *"The 100% score is real, but it is specifically **Pipeline Correctness & Formatting Fidelity on the 2 available gold-standard records** (`PDSH4816AF` and `WDTS7024RZ`), not a statistical predictive accuracy claim across unseen manufacturers. The delivery format file provided in the hackathon dataset contained only 2 populated data rows. We proved that where ground truth exists, our pipeline reproduces exact canonical names, registered trademarks (`®`), classpaths, and UOMs with 100% fidelity, while evaluating volume behavior separately via Mechanism B."*

### Q2: "Why are 60.5% of manufacturer and brand values marked Unknown in the 1,000-row catalog batch?"
> **Answer:** *"Because Unilog's master reference dictionaries (`UniCat_Manufacturer_and_Brand_List.xlsx` and `Unilog_Master_UOM_Standards.xlsx`) were not available in this submission. In accordance with our core no-fabrication principle, when an input brand is outside our verified reference coverage, we explicitly label it `Unknown` with `0.0` confidence rather than hallucinating plausible-sounding company names. In enterprise catalog management, an honest `Unknown` that routes to review is infinitely safer than fabricated data that pollutes search filters."*

### Q3: "Why not just send the raw text to an LLM like GPT-4 or Claude with a prompt?"
> **Answer:** *"LLMs generate fluent prose, but they struggle with deterministic constraints: they silently pick winners when distributor columns disagree, hallucinate plausible-looking dimensions, and output inconsistent UOM formatting (`in.` vs `inch` vs `\"`). ProductIQ uses deterministic rule engines for unit normalization, physics validation, fraction parsing, and conflict detection, reserving LLMs strictly for grounded commercial description synthesis where provenance is preserved."*

### Q4: "How does ProductIQ handle cross-source conflicts?"
> **Answer:** *"Zero silent overwriting. If Source A says 2.34 A and Source B says 7.22 A (or E1 says DEWALT and DIB says Black & Decker), ProductIQ stores both evidence references, marks the field `Conflicted`, locks commercial publishing, and generates a structured review queue item with explicit WHAT, WHY, and EVIDENCE for a human engineer to resolve."*

### Q5: "Does the output file meet the exact delivery format requirements?"
> **Answer:** *"Yes. `productiq_delivery_output.xlsx` contains all **252 column headers** from `Unihack__Expected_Output_-_Delivery_Format.csv` in the exact original sequence. Enriched fields and attribute triples are mapped into their exact columns, while unpopulated columns remain genuinely blank cells rather than fake placeholders."*
