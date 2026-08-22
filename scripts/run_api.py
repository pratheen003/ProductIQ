#!/usr/bin/env python3
"""
ProductIQ API Server Runner — Phase 6
======================================
Starts the Uvicorn ASGI server hosting the ProductIQ REST API on http://127.0.0.1:8000.
"""
import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from productiq.logging_setup import setup_logging
from productiq.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Start ProductIQ FastAPI Backend Service")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument(
	    "--port", 
	    type=int, 
	    default=int(os.environ.get("PORT", 8000)),
    	help="Port number",
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.log_level)

    print("=" * 60)
    print("  ProductIQ Phase 6 — REST API Server")
    print("=" * 60)
    print(f"  URL  : http://{args.host}:{args.port}")
    print(f"  Docs : http://{args.host}:{args.port}/docs")
    print("=" * 60)

    uvicorn.run("productiq.api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
