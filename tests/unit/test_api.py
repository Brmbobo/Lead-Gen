"""
Unit tests for Lead-Gen API layer.

Tests cover:
- Health endpoints
- Lead CRUD operations
- Workflow management
- Settings endpoints
- Middleware functionality
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from lead_gen.api.main import create_app, app
from lead_gen.api.schemas import (
    LeadStatusEnum,
    LeadSourceEnum,
    WorkflowStatusEnum,
    HealthStatus,
)
from lead_gen.api.dependencies import get_lead_store, LeadStore


# Use the pre-created app for tests
client = TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_returns_healthy(self):
        """Test basic health check returns healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_health_check_includes_correlation_id(self):
        """Test health check includes correlation ID."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "correlation_id" in data
        assert data["correlation_id"] is not None

    def test_health_check_with_custom_correlation_id(self):
        """Test health check uses provided correlation ID."""
        custom_id = "test-correlation-123"
        response = client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == custom_id

    def test_readiness_check_returns_services(self):
        """Test readiness check returns service status."""
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "services" in data
        assert isinstance(data["services"], list)
        assert len(data["services"]) > 0

    def test_readiness_check_includes_expected_services(self):
        """Test readiness check includes all expected services."""
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        service_names = [s["name"] for s in data["services"]]

        # Should check these services
        assert "google_places" in service_names
        assert "openai" in service_names
        assert "hunter" in service_names
        assert "google_sheets" in service_names


class TestLeadEndpoints:
    """Tests for lead management endpoints."""

    def setup_method(self):
        """Reset lead store before each test."""
        store = get_lead_store()
        store._leads.clear()

    def test_list_leads_empty(self):
        """Test listing leads returns empty list initially."""
        response = client.get("/api/v1/leads")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_create_lead(self):
        """Test creating a new lead."""
        lead_data = {
            "name": "Test Business",
            "phone": "+421901234567",
            "email": "test@example.com",
            "business_type": "dentist",
            "source": "manual",
        }

        response = client.post("/api/v1/leads", json=lead_data)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Business"
        assert data["data"]["phone"] == "+421901234567"
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["status"] == "new"
        assert "id" in data["data"]

    def test_create_lead_minimal(self):
        """Test creating lead with minimal data."""
        lead_data = {"name": "Minimal Business"}

        response = client.post("/api/v1/leads", json=lead_data)

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["name"] == "Minimal Business"
        assert data["data"]["source"] == "manual"

    def test_create_lead_validation_error(self):
        """Test creating lead fails with invalid data."""
        lead_data = {"name": ""}  # Empty name should fail

        response = client.post("/api/v1/leads", json=lead_data)

        assert response.status_code == 422  # Validation error

    def test_get_lead_by_id(self):
        """Test getting a lead by ID."""
        # Create a lead first
        create_response = client.post(
            "/api/v1/leads",
            json={"name": "Test Business"},
        )
        lead_id = create_response.json()["data"]["id"]

        # Get the lead
        response = client.get(f"/api/v1/leads/{lead_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == lead_id
        assert data["data"]["name"] == "Test Business"

    def test_get_lead_not_found(self):
        """Test getting non-existent lead returns 404."""
        response = client.get("/api/v1/leads/non-existent-id")

        assert response.status_code == 404

    def test_update_lead_status(self):
        """Test updating lead status."""
        # Create a lead first
        create_response = client.post(
            "/api/v1/leads",
            json={"name": "Test Business"},
        )
        lead_id = create_response.json()["data"]["id"]

        # Update status
        response = client.put(
            f"/api/v1/leads/{lead_id}",
            json={"status": "contacted"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "contacted"

    def test_update_lead_tags(self):
        """Test updating lead tags."""
        # Create a lead first
        create_response = client.post(
            "/api/v1/leads",
            json={"name": "Test Business"},
        )
        lead_id = create_response.json()["data"]["id"]

        # Update tags
        response = client.put(
            f"/api/v1/leads/{lead_id}",
            json={"tags": ["priority", "dental"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tags"] == ["priority", "dental"]

    def test_update_lead_not_found(self):
        """Test updating non-existent lead returns 404."""
        response = client.put(
            "/api/v1/leads/non-existent-id",
            json={"status": "contacted"},
        )

        assert response.status_code == 404

    def test_delete_lead(self):
        """Test deleting a lead."""
        # Create a lead first
        create_response = client.post(
            "/api/v1/leads",
            json={"name": "Test Business"},
        )
        lead_id = create_response.json()["data"]["id"]

        # Delete the lead
        response = client.delete(f"/api/v1/leads/{lead_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's deleted
        get_response = client.get(f"/api/v1/leads/{lead_id}")
        assert get_response.status_code == 404

    def test_delete_lead_not_found(self):
        """Test deleting non-existent lead returns 404."""
        response = client.delete("/api/v1/leads/non-existent-id")

        assert response.status_code == 404

    def test_list_leads_with_pagination(self):
        """Test listing leads with pagination."""
        # Create multiple leads
        for i in range(25):
            client.post(
                "/api/v1/leads",
                json={"name": f"Business {i}"},
            )

        # Get first page
        response = client.get("/api/v1/leads?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] == 3
        assert data["has_next"] is True
        assert data["has_previous"] is False

        # Get second page
        response = client.get("/api/v1/leads?page=2&page_size=10")
        data = response.json()
        assert len(data["items"]) == 10
        assert data["has_next"] is True
        assert data["has_previous"] is True

    def test_list_leads_filter_by_status(self):
        """Test filtering leads by status."""
        # Create leads with different statuses
        client.post("/api/v1/leads", json={"name": "New Business"})

        create_response = client.post(
            "/api/v1/leads",
            json={"name": "Contacted Business"},
        )
        lead_id = create_response.json()["data"]["id"]
        client.put(f"/api/v1/leads/{lead_id}", json={"status": "contacted"})

        # Filter by contacted status
        response = client.get("/api/v1/leads?status=contacted")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "contacted"

    def test_list_leads_filter_by_has_email(self):
        """Test filtering leads by email presence."""
        # Create leads with and without email
        client.post(
            "/api/v1/leads",
            json={"name": "With Email", "email": "test@example.com"},
        )
        client.post(
            "/api/v1/leads",
            json={"name": "Without Email"},
        )

        # Filter by has_email=true
        response = client.get("/api/v1/leads?has_email=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "test@example.com"

    def test_export_leads_csv(self):
        """Test exporting leads to CSV."""
        # Create some leads
        client.post(
            "/api/v1/leads",
            json={"name": "Export Test", "email": "test@example.com"},
        )

        response = client.post(
            "/api/v1/leads/export",
            json={"format": "csv"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "Export Test" in response.text
        assert "test@example.com" in response.text

    def test_export_leads_json(self):
        """Test exporting leads to JSON."""
        # Create some leads
        client.post(
            "/api/v1/leads",
            json={"name": "Export Test"},
        )

        response = client.post(
            "/api/v1/leads/export",
            json={"format": "json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1


class TestWorkflowEndpoints:
    """Tests for workflow management endpoints."""

    def test_list_workflows(self):
        """Test listing available workflows."""
        response = client.get("/api/v1/workflows")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0

    def test_list_workflows_contains_expected_fields(self):
        """Test workflow list contains expected fields."""
        response = client.get("/api/v1/workflows")

        data = response.json()
        workflow = data["data"][0]

        assert "id" in workflow
        assert "name" in workflow
        assert "description" in workflow
        assert "steps" in workflow
        assert "status" in workflow
        assert "enabled" in workflow

    def test_get_workflow_by_id(self):
        """Test getting workflow by ID."""
        # First get list to know a valid ID
        list_response = client.get("/api/v1/workflows")
        workflow_id = list_response.json()["data"][0]["id"]

        response = client.get(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == workflow_id

    def test_get_workflow_not_found(self):
        """Test getting non-existent workflow returns 404."""
        response = client.get("/api/v1/workflows/non-existent-workflow")

        assert response.status_code == 404

    def test_run_workflow(self):
        """Test running a workflow."""
        # Get a valid workflow ID
        list_response = client.get("/api/v1/workflows")
        workflow_id = list_response.json()["data"][0]["id"]

        response = client.post(
            f"/api/v1/workflows/{workflow_id}/run",
            json={"dry_run": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data
        assert "workflow_id" in data
        assert data["workflow_id"] == workflow_id

    def test_run_workflow_dry_run(self):
        """Test running workflow in dry run mode."""
        list_response = client.get("/api/v1/workflows")
        workflow_id = list_response.json()["data"][0]["id"]

        response = client.post(
            f"/api/v1/workflows/{workflow_id}/run",
            json={"dry_run": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"  # Dry run completes immediately

    def test_run_workflow_not_found(self):
        """Test running non-existent workflow returns 404."""
        response = client.post(
            "/api/v1/workflows/non-existent/run",
            json={},
        )

        assert response.status_code == 404

    def test_get_workflow_status(self):
        """Test getting workflow status."""
        list_response = client.get("/api/v1/workflows")
        workflow_id = list_response.json()["data"][0]["id"]

        response = client.get(f"/api/v1/workflows/{workflow_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert "status" in data

    def test_stop_workflow_not_running(self):
        """Test stopping a workflow that isn't running."""
        list_response = client.get("/api/v1/workflows")
        workflow_id = list_response.json()["data"][0]["id"]

        response = client.post(f"/api/v1/workflows/{workflow_id}/stop")

        assert response.status_code == 404  # No running execution


class TestSettingsEndpoints:
    """Tests for settings management endpoints."""

    def test_get_settings(self):
        """Test getting current settings."""
        response = client.get("/api/v1/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "environment" in data["data"]
        assert "rate_limits" in data["data"]
        assert "gdpr" in data["data"]

    def test_settings_secrets_masked(self):
        """Test that settings response masks secrets."""
        response = client.get("/api/v1/settings")

        data = response.json()["data"]

        # Should show whether keys are configured, not the actual values
        assert "google_places_api_key_configured" in data
        assert "openai_api_key_configured" in data
        assert "hunter_api_key_configured" in data
        assert "google_service_account_configured" in data

        # Should be boolean
        assert isinstance(data["google_places_api_key_configured"], bool)

    def test_update_settings(self):
        """Test updating settings."""
        response = client.put(
            "/api/v1/settings",
            json={
                "rate_limits": {
                    "google_places": 30,
                    "openai": 30,
                    "hunter": 15,
                    "sheets": 30,
                }
            },
        )

        # Currently returns success but doesn't persist
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_validate_settings(self):
        """Test validating API keys."""
        response = client.get("/api/v1/settings/validate")

        assert response.status_code == 200
        data = response.json()
        assert "all_valid" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_validate_settings_includes_services(self):
        """Test validate settings checks all services."""
        response = client.get("/api/v1/settings/validate")

        data = response.json()
        service_names = [r["service"] for r in data["results"]]

        assert "google_places" in service_names
        assert "openai" in service_names
        assert "hunter" in service_names
        assert "google_service_account" in service_names


class TestMiddleware:
    """Tests for middleware functionality."""

    def test_correlation_id_generated(self):
        """Test that correlation ID is generated if not provided."""
        response = client.get("/api/v1/health")

        # Should be in response headers
        assert "x-correlation-id" in response.headers
        assert response.headers["x-correlation-id"]

    def test_correlation_id_preserved(self):
        """Test that provided correlation ID is preserved."""
        custom_id = "my-custom-correlation-id"
        response = client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.headers["x-correlation-id"] == custom_id

    def test_request_id_generated(self):
        """Test that request ID is generated."""
        response = client.get("/api/v1/health")

        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"]


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Lead-Gen API"
        assert "version" in data
        assert "docs" in data
        assert "health" in data


class TestOpenAPI:
    """Tests for OpenAPI documentation."""

    def test_openapi_json_available(self):
        """Test OpenAPI JSON is available."""
        response = client.get("/api/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Lead-Gen API"

    def test_docs_available(self):
        """Test Swagger UI docs are available."""
        response = client.get("/api/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "html" in response.text.lower()

    def test_redoc_available(self):
        """Test ReDoc is available."""
        response = client.get("/api/redoc")

        assert response.status_code == 200
        assert "html" in response.text.lower()


class TestLeadStore:
    """Tests for in-memory lead store."""

    def test_add_and_get_lead(self):
        """Test adding and getting a lead."""
        store = LeadStore()
        lead_data = {"name": "Test", "id": "test-id"}

        store.add_lead(lead_data)
        result = store.get_lead("test-id")

        assert result is not None
        assert result["name"] == "Test"

    def test_update_lead(self):
        """Test updating a lead."""
        store = LeadStore()
        store.add_lead({"id": "test-id", "name": "Original"})

        result = store.update_lead("test-id", {"name": "Updated"})

        assert result is not None
        assert result["name"] == "Updated"

    def test_delete_lead(self):
        """Test deleting a lead."""
        store = LeadStore()
        store.add_lead({"id": "test-id", "name": "Test"})

        assert store.delete_lead("test-id") is True
        assert store.get_lead("test-id") is None

    def test_list_leads_with_filters(self):
        """Test listing leads with filters."""
        store = LeadStore()
        store.add_lead({"id": "1", "name": "Test", "status": "new"})
        store.add_lead({"id": "2", "name": "Test 2", "status": "contacted"})

        leads, total = store.list_leads(filters={"status": "new"})

        assert total == 1
        assert leads[0]["id"] == "1"

    def test_list_leads_pagination(self):
        """Test listing leads with pagination."""
        store = LeadStore()
        for i in range(15):
            store.add_lead({"id": str(i), "name": f"Test {i}"})

        leads, total = store.list_leads(offset=5, limit=5)

        assert total == 15
        assert len(leads) == 5
