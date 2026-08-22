"""
ProductIQ API Service Layer — Phase 6
======================================
Queries domain artifacts across Phases 1–5 to assemble unified DTOs.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from productiq.api.models import (
    SpecificationDTO,
    ClaimDTO,
    ConflictSourceDTO,
    ConflictRecordDTO,
    ReviewItemDTO,
    EvidenceRecordDTO,
    ProductSummaryDTO,
    ProductDetailDTO,
    BatchSummaryDTO,
    ReviewResolutionRequestDTO,
    ReviewResolutionResponseDTO,
)
from productiq.trust.service import ProductTrustAnalyzer, BatchTrustAnalyzer

logger = logging.getLogger("productiq.api")


class ProductIQDataBridge:
    """
    Data bridge connecting the FastAPI endpoints to Phase 0–5 artifacts and models.
    """

    def __init__(self, data_dir: Optional[Path | str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent.parent / "data"
        self.processed_dir = self.data_dir / "processed"
        self.trust_analyzer = ProductTrustAnalyzer()
        self.batch_analyzer = BatchTrustAnalyzer(analyzer=self.trust_analyzer)
        self._resolutions_file = self.processed_dir / "_review_resolutions.json"
        self._resolutions: Dict[str, Dict[str, Any]] = self._load_resolutions()

    def _load_resolutions(self) -> Dict[str, Dict[str, Any]]:
        if self._resolutions_file.exists():
            try:
                with open(self._resolutions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_resolutions(self) -> None:
        try:
            with open(self._resolutions_file, "w", encoding="utf-8") as f:
                json.dump(self._resolutions, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save review resolutions: {e}")

    def _build_conflict_sources(self, field_name: str, norm_data: Dict[str, Any]) -> List[ConflictSourceDTO]:
        """
        Extract N structured conflict sources from normalized field records.
        """
        sources: List[ConflictSourceDTO] = []
        seen = set()

        field_norm = norm_data.get("fields", {}).get(field_name, {})
        
        # 1. From explicit conflict records
        for conf in field_norm.get("conflicts", []):
            for s_key, v_key, u_key in [("source_a", "value_a", "unit_a"), ("source_b", "value_b", "unit_b")]:
                s_info = conf.get(s_key)
                if isinstance(s_info, dict):
                    stype = s_info.get("source_type", "pdf").lower()
                    raw_val = s_info.get("raw_value")
                    val = conf.get(v_key, s_info.get("parsed_value"))
                    unit = conf.get(u_key, s_info.get("raw_unit"))
                    loc = s_info.get("section")
                    if not loc:
                        if s_info.get("page"):
                            loc = f"Page {s_info['page']} (Table)"
                        elif s_info.get("row"):
                            col_info = f" ({s_info.get('column')})" if s_info.get("column") else ""
                            loc = f"Row {s_info['row']}{col_info}"
                        elif s_info.get("url"):
                            loc = s_info["url"]

                    source_name = (
                        "PDF Brochure (Official)" if stype == "pdf"
                        else "Legacy CSV (ERP Database)" if stype == "csv"
                        else f"{stype.upper()} Catalog"
                    )

                    sig = (stype, str(raw_val), str(val))
                    if sig not in seen:
                        seen.add(sig)
                        sources.append(ConflictSourceDTO(
                            source_id=s_info.get("source_id", ""),
                            source_type=stype,
                            source_name=source_name,
                            value=val,
                            unit=unit,
                            raw_value=str(raw_val) if raw_val is not None else None,
                            location=loc,
                            confidence=s_info.get("confidence", 0.9),
                        ))

        # 2. From evidence refs if not already captured
        if not sources:
            for eref in field_norm.get("evidence_refs", []):
                stype = eref.get("source_type", "pdf").lower()
                raw_val = eref.get("raw_value")
                val = eref.get("parsed_value")
                unit = eref.get("raw_unit")
                loc = eref.get("section")
                if not loc:
                    if eref.get("page"):
                        loc = f"Page {eref['page']}"
                    elif eref.get("row"):
                        loc = f"Row {eref['row']}"

                source_name = (
                    "PDF Brochure (Official)" if stype == "pdf"
                    else "Legacy CSV (ERP Database)" if stype == "csv"
                    else f"{stype.upper()} Catalog"
                )

                sig = (stype, str(raw_val), str(val))
                if sig not in seen:
                    seen.add(sig)
                    sources.append(ConflictSourceDTO(
                        source_id=eref.get("source_id", ""),
                        source_type=stype,
                        source_name=source_name,
                        value=val,
                        unit=unit,
                        raw_value=str(raw_val) if raw_val is not None else None,
                        location=loc,
                        confidence=eref.get("confidence", 0.9),
                    ))

        return sources

    def get_all_products(self) -> List[ProductSummaryDTO]:
        """
        Return list of product summaries for all available processed motors.
        """
        product_dirs = sorted([
            d for d in self.processed_dir.iterdir()
            if d.is_dir() and d.name.startswith("PIQ-")
        ])

        summaries: List[ProductSummaryDTO] = []
        for pdir in product_dirs:
            pid = pdir.name
            detail = self.get_product_detail(pid)
            if not detail:
                continue

            power = None
            voltage = None
            speed = None
            poles = None
            frame = None

            if "rated_power" in detail.specifications and detail.specifications["rated_power"].canonical_value is not None:
                power = float(detail.specifications["rated_power"].canonical_value)
            if "rated_voltage" in detail.specifications and detail.specifications["rated_voltage"].canonical_value is not None:
                voltage = float(detail.specifications["rated_voltage"].canonical_value)
            if "rated_speed" in detail.specifications and detail.specifications["rated_speed"].canonical_value is not None:
                speed = float(detail.specifications["rated_speed"].canonical_value)
            if "poles" in detail.specifications and detail.specifications["poles"].canonical_value is not None:
                try:
                    poles = int(detail.specifications["poles"].canonical_value)
                except (ValueError, TypeError):
                    pass
            if "frame_size" in detail.specifications and detail.specifications["frame_size"].canonical_value is not None:
                frame = str(detail.specifications["frame_size"].canonical_value)

            summaries.append(ProductSummaryDTO(
                product_id=detail.product_id,
                manufacturer=detail.manufacturer,
                model=detail.model,
                category=detail.category,
                trust_score=detail.trust_score,
                overall_trust_status=detail.overall_trust_status,
                overall_publishability=detail.overall_publishability,
                review_items_count=len(detail.review_queue),
                conflicts_count=len(detail.unresolved_conflicts),
                publishable_attributes_count=len(detail.publishable_attributes),
                restricted_attributes_count=len(detail.restricted_attributes),
                rated_power_kw=power,
                rated_voltage_v=voltage,
                rated_speed_rpm=speed,
                poles=poles,
                frame_size=frame,
                summary_reason=detail.summary_reason,
            ))

        return summaries

    def get_product_detail(self, product_id: str) -> Optional[ProductDetailDTO]:
        """
        Assemble unified ProductDetailDTO from Phase 0–5 artifacts.
        """
        pdir = self.processed_dir / product_id
        if not pdir.exists():
            return None

        # Load normalization
        norm_file = pdir / "normalized_product.json"
        norm_data: Dict[str, Any] = {}
        if norm_file.exists():
            try:
                with open(norm_file, "r", encoding="utf-8") as f:
                    norm_data = json.load(f)
            except Exception:
                pass

        # Load trust report
        trust_file = pdir / "trust_report.json"
        trust_data: Dict[str, Any] = {}
        if trust_file.exists():
            try:
                with open(trust_file, "r", encoding="utf-8") as f:
                    trust_data = json.load(f)
            except Exception:
                pass
        if not trust_data:
            report = self.trust_analyzer.analyze(product_id, self.data_dir, save_output=True)
            trust_data = report.to_dict()

        # Load enrichment
        enrich_file = pdir / "enrichment.json"
        enrich_data = {}
        if enrich_file.exists():
            try:
                with open(enrich_file, "r", encoding="utf-8") as f:
                    enrich_data = json.load(f)
            except Exception:
                pass

        # Load evidence records
        evidence_records: List[EvidenceRecordDTO] = []
        for src_type in ["pdf", "csv", "web"]:
            efile = pdir / f"{src_type}_evidence.json"
            if efile.exists():
                try:
                    with open(efile, "r", encoding="utf-8") as f:
                        edata = json.load(f)
                        raw_list = edata.get("evidence") or edata.get("records") or []
                        for r in raw_list:
                            evidence_records.append(EvidenceRecordDTO(
                                source_id=r.get("source_id", ""),
                                source_type=r.get("source_type", src_type),
                                product_id=r.get("product_id", product_id),
                                attribute=r.get("attribute", ""),
                                raw_value=str(r.get("raw_value", "")),
                                raw_unit=r.get("raw_unit"),
                                parsed_value=r.get("parsed_value"),
                                method=r.get("method", ""),
                                confidence=r.get("confidence", 1.0),
                                page=r.get("page"),
                                row=r.get("row"),
                                column=r.get("column"),
                                url=r.get("url"),
                                section=r.get("section"),
                                evidence_text=r.get("evidence_text"),
                            ))
                except Exception:
                    pass

        # Build specifications dictionary
        specifications: Dict[str, SpecificationDTO] = {}
        for fname, fdata in trust_data.get("attribute_trust", {}).items():
            specifications[fname] = SpecificationDTO(
                field=fdata.get("field", fname),
                canonical_value=fdata.get("canonical_value"),
                canonical_unit=fdata.get("canonical_unit"),
                trust_status=fdata.get("trust_status", "MISSING"),
                publishability=fdata.get("publishability", "NOT_PUBLISHABLE"),
                validation_status=fdata.get("validation_status"),
                is_conflicted=fdata.get("is_conflicted", False),
                evidence_sources=fdata.get("evidence_sources", []),
                confidence_score=fdata.get("confidence_score", 1.0),
                reason=fdata.get("reason", ""),
                validation_rule_ids=fdata.get("validation_rule_ids", []),
            )

        # Build claims list
        claims: List[ClaimDTO] = []
        for cdata in trust_data.get("claim_trust", []):
            claims.append(ClaimDTO(
                claim_text=cdata.get("claim_text", ""),
                category=cdata.get("category", "general"),
                claim_type=cdata.get("claim_type", "INFERRED"),
                trust_status=cdata.get("trust_status", "UNVERIFIED"),
                publishability=cdata.get("publishability", "PUBLISHABLE_WITH_WARNING"),
                supporting_fields=cdata.get("supporting_fields", []),
                evidence_sources=cdata.get("evidence_sources", []),
                confidence=cdata.get("confidence", 1.0),
                reason=cdata.get("reason", ""),
            ))

        # Build structured unresolved conflicts list (supporting N sources)
        unresolved_conflicts: List[ConflictRecordDTO] = []
        for conf in trust_data.get("unresolved_conflicts", []):
            c_field = conf.get("field") or conf.get("canonical_field") or ""
            sources = self._build_conflict_sources(c_field, norm_data)
            unresolved_conflicts.append(ConflictRecordDTO(
                field=c_field,
                canonical_field=c_field,
                description=conf.get("description", ""),
                action_needed=conf.get("action_needed", ""),
                recommended_action=conf.get("action_needed", "Requires physical nameplate verification."),
                sources=sources,
                conflicting_values=conf.get("conflicting_values"),
            ))

        # Build review queue
        review_queue: List[ReviewItemDTO] = []
        for rdata in trust_data.get("review_queue", []):
            rid = rdata.get("review_id", "")
            tname = rdata.get("target_name", "")
            res_info = self._resolutions.get(rid, {})
            status = "RESOLVED" if res_info else "OPEN"
            
            # Extract sources if this is a conflict
            conf_sources: List[ConflictSourceDTO] = []
            if rdata.get("issue_type") == "CONFLICT" and tname:
                conf_sources = self._build_conflict_sources(tname, norm_data)

            review_queue.append(ReviewItemDTO(
                review_id=rid,
                product_id=product_id,
                target_type=rdata.get("target_type", "attribute"),
                target_name=tname,
                severity=rdata.get("severity", "MEDIUM"),
                issue_type=rdata.get("issue_type", "WARNING"),
                description=rdata.get("description", ""),
                conflicting_values=rdata.get("conflicting_values"),
                conflicting_sources=conf_sources,
                validation_rule_id=rdata.get("validation_rule_id"),
                affected_claims=rdata.get("affected_claims", []),
                recommended_action=rdata.get("recommended_action", ""),
                status=status,
                resolution_note=res_info.get("resolution_note"),
                resolved_value=res_info.get("resolved_value"),
                resolved_by=res_info.get("resolved_by"),
            ))

        return ProductDetailDTO(
            product_id=product_id,
            manufacturer=trust_data.get("manufacturer", "WEG"),
            model=trust_data.get("model", "W22 Severe Process IE3"),
            category="Industrial Electric Motor",
            trust_score=trust_data.get("trust_score", 0.0),
            trust_score_formula=trust_data.get("trust_score_formula", ""),
            trust_score_breakdown=trust_data.get("trust_score_breakdown", {}),
            overall_trust_status=trust_data.get("overall_trust_status", "UNVERIFIED"),
            overall_publishability=trust_data.get("overall_publishability", "REVIEW_REQUIRED"),
            summary_reason=trust_data.get("summary_reason", ""),
            specifications=specifications,
            claims=claims,
            review_queue=review_queue,
            unresolved_conflicts=unresolved_conflicts,
            publishable_attributes=trust_data.get("publishable_attributes", []),
            restricted_attributes=trust_data.get("restricted_attributes", []),
            evidence_records=evidence_records,
            commercial_summary=enrich_data.get("commercial_summary", ""),
            technical_description=enrich_data.get("technical_description", ""),
            target_applications=enrich_data.get("target_applications", []),
            search_keywords=enrich_data.get("search_keywords", []),
        )

    def get_batch_summary(self) -> BatchSummaryDTO:
        """
        Return dataset-wide intelligence metrics and distributions.
        """
        products = self.get_all_products()

        trust_dist: Dict[str, int] = {"TRUSTED": 0, "CONFLICTED": 0, "REVIEW_REQUIRED": 0, "UNVERIFIED": 0, "UNSUPPORTED": 0}
        pub_dist: Dict[str, int] = {"PUBLISHABLE": 0, "PUBLISHABLE_WITH_WARNING": 0, "REVIEW_REQUIRED": 0, "NOT_PUBLISHABLE": 0}
        sev_dist: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        total_review_items = 0
        conflicted_count = 0
        trusted_count = 0
        review_req_count = 0
        pub_count = 0
        pub_warn_count = 0
        not_pub_count = 0

        score_sum = 0.0

        for p in products:
            score_sum += p.trust_score
            total_review_items += p.review_items_count

            # Status distributions
            ts = p.overall_trust_status
            trust_dist[ts] = trust_dist.get(ts, 0) + 1
            if ts == "CONFLICTED":
                conflicted_count += 1
            elif ts == "TRUSTED":
                trusted_count += 1
            elif ts == "REVIEW_REQUIRED":
                review_req_count += 1

            ps = p.overall_publishability
            pub_dist[ps] = pub_dist.get(ps, 0) + 1
            if ps == "PUBLISHABLE":
                pub_count += 1
            elif ps == "PUBLISHABLE_WITH_WARNING":
                pub_warn_count += 1
            elif ps == "NOT_PUBLISHABLE":
                not_pub_count += 1

        # Load all reviews to calculate severity distribution
        all_reviews = self.get_all_reviews()
        for r in all_reviews:
            sev = r.severity.upper()
            sev_dist[sev] = sev_dist.get(sev, 0) + 1

        avg_score = score_sum / max(1, len(products))

        return BatchSummaryDTO(
            total_products=len(products),
            trusted_count=trusted_count,
            review_required_count=review_req_count,
            conflicted_count=conflicted_count,
            publishable_count=pub_count,
            publishable_with_warning_count=pub_warn_count,
            not_publishable_count=not_pub_count,
            avg_trust_score=round(avg_score, 4),
            total_review_items=total_review_items,
            trust_distribution=trust_dist,
            publishability_distribution=pub_dist,
            severity_distribution=sev_dist,
            products=products,
            generated_at="2026-08-20T12:00:00Z",
        )

    def get_all_reviews(
        self,
        severity: Optional[str] = None,
        issue_type: Optional[str] = None,
        status: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> List[ReviewItemDTO]:
        """
        Aggregate all review items across products with optional filtering.
        """
        product_dirs = sorted([
            d for d in self.processed_dir.iterdir()
            if d.is_dir() and d.name.startswith("PIQ-")
        ])

        all_items: List[ReviewItemDTO] = []
        for pdir in product_dirs:
            pid = pdir.name
            if product_id and pid != product_id:
                continue

            detail = self.get_product_detail(pid)
            if not detail:
                continue

            for item in detail.review_queue:
                if severity and item.severity.upper() != severity.upper():
                    continue
                if issue_type and item.issue_type.upper() != issue_type.upper():
                    continue
                if status and item.status.upper() != status.upper():
                    continue
                all_items.append(item)

        return all_items

    def get_review(self, review_id: str) -> Optional[ReviewItemDTO]:
        """
        Retrieve a single review item by ID.
        """
        all_reviews = self.get_all_reviews()
        for item in all_reviews:
            if item.review_id == review_id:
                return item
        return None

    def resolve_review(
        self,
        review_id: str,
        resolution: ReviewResolutionRequestDTO,
    ) -> ReviewResolutionResponseDTO:
        """
        Apply a human resolution to a review item and persist it.
        """
        # Find which product owns this review_id
        parts = review_id.split("-")
        product_id = ""
        for p in self.get_all_products():
            if p.product_id in review_id:
                product_id = p.product_id
                break

        self._resolutions[review_id] = {
            "review_id": review_id,
            "product_id": product_id,
            "selected_source": resolution.selected_source,
            "resolved_value": resolution.resolved_value,
            "resolution_note": resolution.resolution_note,
            "resolved_by": resolution.reviewer,
            "resolved_at": "2026-08-20T12:00:00Z",
        }
        self._save_resolutions()

        return ReviewResolutionResponseDTO(
            success=True,
            review_id=review_id,
            product_id=product_id,
            status="RESOLVED",
            resolved_value=resolution.resolved_value,
            message="Review item marked as RESOLVED by engineer.",
        )
