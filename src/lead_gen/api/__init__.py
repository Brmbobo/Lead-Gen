"""
FastAPI REST API layer for Lead-Gen.

Provides a complete REST API for:
- Lead management (CRUD operations)
- Workflow execution and monitoring
- Settings management
- Health checks

Usage:
    from lead_gen.api import create_app

    app = create_app()
"""

from lead_gen.api.main import create_app, get_app

__all__ = [
    "create_app",
    "get_app",
]
