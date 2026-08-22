"""
ProductIQ API Package — Phase 6
================================
FastAPI backend service bridge for frontend UI and external integrations.
"""
from productiq.api.app import app
from productiq.api.service import ProductIQDataBridge

__all__ = ["app", "ProductIQDataBridge"]
