# ProductIQ Phase 6 — Frontend & Presentation Layer

## 1. Overview

**ProductIQ Phase 6** delivers an enterprise-grade presentation, exploration, and human-in-the-loop review interface over the completed Phase 0–5 intelligence pipeline. The frontend is built with **Next.js (App Router)**, **TypeScript**, **Tailwind CSS**, **shadcn/ui** design patterns, **Lucide React** icons, and **Recharts** data visualizations, communicating with the Python intelligence layer via a dedicated **FastAPI** service bridge.

---

## 2. Architectural Blueprint

```
                      ┌─────────────────────────────────────────────────┐
                      │             Next.js 14 UI (App Router)          │
                      │  • Dashboard Overview (/)                       │
                      │  • Product Catalog (/products)                  │
                      │  • Spec & Evidence Inspector (/products/[id])   │
                      │  • Human Review Queue (/reviews)                │
                      │  • Batch Intelligence (/batch)                  │
                      │  • Pipeline Ingest Engine (/ingest)             │
                      └────────────────────────┬────────────────────────┘
                                               │ HTTP / JSON API (Port 8000)
                                               ▼
                      ┌─────────────────────────────────────────────────┐
                      │         FastAPI Backend Service Bridge          │
                      │         (productiq/api/app.py & endpoints)      │
                      └────────┬───────────────┬────────────────┬───────┘
                               │               │                │
            ┌──────────────────┴──┐     ┌──────┴──────────┐   ┌─┴────────────────┐
            │   Product Service   │     │  Trust Service  │   │  Review Service  │
            └──────────┬──────────┘     └──────┬──────────┘   └──┬───────────────┘
                       │                       │                 │
                       ▼                       ▼                 ▼
          ┌──────────────────────────────────────────────────────────────────────┐
          │               Phase 0–5 Domain Models & Processed Data               │
          │  • NormalizedProduct (Phase 2)    • ValidationReport (Phase 3)       │
          │  • ProductEnrichment (Phase 4)    • ProductTrustReport (Phase 5)     │
          │  • 1,837 Evidence Records         • 62 Structured Review Items       │
          └──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Design System & Typography

### Typography
- **IBM Plex Sans**: Headings, labels, body text, navigation, dialogs, button actions.
- **IBM Plex Mono**: SKU IDs, technical values, canonical units, confidence numbers, formula strings, timestamps.

### Palette
- **Brand Dark (`#4D3A4D`)**: Navigation sidebar, major headlines, dark cards.
- **Brand Accent (`#BE5CA9`)**: Primary action buttons, active navigation states, highlights.
- **Brand Muted (`#D59CC5`)**: Secondary UI accents, logo subtext, subtle borders.
- **Brand Surface (`#F8F6F8`)**: Main background canvas with neutral white content surfaces.

### Semantic Trust Status Colors
- **VERIFIED / TRUSTED**: Emerald Green (`#16A34A`)
- **INFERRED / UNVERIFIED**: Amber (`#D97706`)
- **CONFLICTED**: Rose Red (`#DC2626`)
- **UNKNOWN / MISSING**: Neutral Gray (`#6B7280`)
- **UNSUPPORTED**: Royal Purple (`#9333EA`)

---

## 4. REST API Endpoints (`productiq/api/app.py`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status check. |
| `GET` | `/api/products` | Returns summarized list of all 12 motor products with search & status filters. |
| `GET` | `/api/products/{id}` | Full unified technical specifications, trust report, evidence records, and claims. |
| `GET` | `/api/products/{id}/trust` | Trust evaluation, score breakdown, and review queue for a single product. |
| `GET` | `/api/products/{id}/evidence` | Raw evidence records from PDF, CSV, and Web extraction. |
| `GET` | `/api/products/{id}/enrichment` | Grounded AI enrichment text, applications, keywords, and claims. |
| `GET` | `/api/batch/summary` | Dataset-wide intelligence metrics, trust distributions, and publishability readiness. |
| `GET` | `/api/reviews` | List of 62 review items with filter by severity, issue_type, and status. |
| `GET` | `/api/reviews/{id}` | Single review item details. |
| `POST` | `/api/reviews/{id}/resolve` | Submit human engineering resolution for a conflict. |
| `POST` | `/api/ingest/demo-run` | Triggers ingestion pipeline simulation. |

---

## 5. Screen Breakdown

### 1. Dashboard (`/`)
- Real dataset metrics: 12 motors processed, 100% completeness, 0.4133 avg trust score, 62 review items.
- Visualizations: Trust Status Donut, Catalog Readiness Donut, Severity Bar Chart, SKU Score Histogram.
- Quick Jump to canonical demo conflict `PIQ-W22SP-4P-1.1`.

### 2. Products Catalog (`/products`)
- Data table with sorting by power, trust score, and SKU.
- Filter by `All`, `Conflicted`, `Review Required`.
- Direct links to individual product inspector.

### 3. Product Detail (`/products/[id]`)
- **Trust Score Gauge**: Circular radial visualization with mathematical formula breakdown.
- **Critical Specs Grid**: Top technical parameters with semantic status badges.
- **Conflict Comparator**: Prominent side-by-side card comparing PDF (`2.34 A`) vs CSV (`7.22 A`) with zero arbitrary winner chosen.
- **Specifications Table**: 11 canonical fields with expandable evidence drawers showing page numbers, raw strings, and physics validation findings.
- **Grounded AI Claims**: Structured claims tagged with trust status and evidence linkage.

### 4. Batch Intelligence (`/batch`)
- Dataset completeness analytics.
- Conflict density across the 12-motor dataset.
- Export batch intelligence JSON artifact.

### 5. Review Queue (`/reviews`)
- Filter by `All Flags (62)`, `Conflicts (52)`, `Warnings (10)`, `Resolved`.
- Interactive `ReviewResolveModal` enabling domain engineers to select authoritative sources, input justification, and mark items as resolved.

### 6. Data Ingestion Engine (`/ingest`)
- Drag & drop document intake simulator for PDFs, CSVs, and Web URLs.
- Multi-stage pipeline progress visualizer.
- **Extraction Precision Analysis**: Side-by-side comparison between Standard Parsers (missed columns, lost units) and ProductIQ Engine (canonical units, 100% provenance).

---

## 6. How to Run Locally

### Start FastAPI Backend Bridge:
```bash
python scripts/run_api.py --port 8000
```

### Start Next.js Frontend:
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in any modern desktop browser.

---

## 7. Verification

Run the dedicated Phase 6 verification audit:
```bash
python scripts/verify_phase6.py
```
Expected output: **All 20 checks passed.**
