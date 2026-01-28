"""
API route modules for Lead-Gen.

Each module provides a FastAPI router for a specific domain:
- leads: Lead CRUD operations
- workflows: Workflow management
- settings: Application settings
- health: Health check endpoints
"""

from lead_gen.api.routes.leads import router as leads_router
from lead_gen.api.routes.workflows import router as workflows_router
from lead_gen.api.routes.settings import router as settings_router
from lead_gen.api.routes.health import router as health_router

__all__ = [
    "leads_router",
    "workflows_router",
    "settings_router",
    "health_router",
]
