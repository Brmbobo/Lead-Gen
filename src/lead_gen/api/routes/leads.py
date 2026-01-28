"""
Lead management endpoints for Lead-Gen API.

Provides CRUD operations for leads:
- List leads with pagination and filtering
- Get lead by ID
- Create new lead
- Update lead status
- Delete lead (GDPR compliance)
- Export leads to CSV/Sheets
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import structlog

from lead_gen.api.dependencies import (
    get_correlation_id,
    get_lead_store,
    get_sheets_service_optional,
    LeadStore,
)
from lead_gen.api.schemas import (
    APIResponse,
    ErrorResponse,
    LeadCreateRequest,
    LeadExportRequest,
    LeadExportResponse,
    LeadFilterParams,
    LeadResponse,
    LeadSourceEnum,
    LeadStatusEnum,
    LeadUpdateRequest,
    PaginatedResponse,
)


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/leads", tags=["Leads"])


def _lead_dict_to_response(lead_dict: dict) -> LeadResponse:
    """Convert internal lead dict to response schema."""
    return LeadResponse(
        id=lead_dict.get("id", ""),
        place_id=lead_dict.get("place_id", ""),
        name=lead_dict.get("name", ""),
        phone=lead_dict.get("phone", ""),
        website=lead_dict.get("website"),
        email=lead_dict.get("email"),
        location=lead_dict.get("location"),
        business_type=lead_dict.get("business_type", ""),
        categories=lead_dict.get("categories", []),
        metrics=lead_dict.get("metrics", {}),
        source=lead_dict.get("source", LeadSourceEnum.MANUAL),
        status=lead_dict.get("status", LeadStatusEnum.NEW),
        quality_score=lead_dict.get("quality_score", 0),
        tags=lead_dict.get("tags", []),
        notes=lead_dict.get("notes", ""),
        scraped_at=lead_dict.get("scraped_at", datetime.now(timezone.utc)),
        status_updated_at=lead_dict.get("status_updated_at", datetime.now(timezone.utc)),
    )


@router.get(
    "",
    response_model=PaginatedResponse[LeadResponse],
    summary="List leads",
    description="List leads with pagination and optional filtering.",
)
async def list_leads(
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: LeadStatusEnum | None = Query(default=None, description="Filter by status"),
    source: LeadSourceEnum | None = Query(default=None, description="Filter by source"),
    business_type: str | None = Query(default=None, description="Filter by business type"),
    min_quality_score: int | None = Query(default=None, ge=0, le=100, description="Minimum quality score"),
    has_email: bool | None = Query(default=None, description="Has email address"),
    has_phone: bool | None = Query(default=None, description="Has phone number"),
    search: str | None = Query(default=None, description="Search in name, email, phone"),
) -> PaginatedResponse[LeadResponse]:
    """
    List leads with pagination and filtering.

    Returns paginated list of leads with metadata.
    """
    # Build filters
    filters = {}
    if status:
        filters["status"] = status.value
    if source:
        filters["source"] = source.value
    if business_type:
        filters["business_type"] = business_type
    if min_quality_score is not None:
        filters["min_quality_score"] = min_quality_score
    if has_email is not None:
        filters["has_email"] = has_email
    if has_phone is not None:
        filters["has_phone"] = has_phone
    if search:
        filters["search"] = search

    offset = (page - 1) * page_size
    leads, total = lead_store.list_leads(filters=filters, offset=offset, limit=page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    logger.info(
        "leads_listed",
        page=page,
        page_size=page_size,
        total=total,
        filters=filters,
        correlation_id=correlation_id,
    )

    return PaginatedResponse(
        items=[_lead_dict_to_response(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
        correlation_id=correlation_id,
    )


@router.get(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    summary="Get lead by ID",
    description="Retrieve a single lead by its ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Lead not found"},
    },
)
async def get_lead(
    lead_id: str,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
) -> APIResponse[LeadResponse]:
    """
    Get a lead by ID.

    Returns the lead if found, 404 otherwise.
    """
    lead = lead_store.get_lead(lead_id)

    if not lead:
        logger.warning(
            "lead_not_found",
            lead_id=lead_id,
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID '{lead_id}' not found",
        )

    logger.info(
        "lead_retrieved",
        lead_id=lead_id,
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=_lead_dict_to_response(lead),
        correlation_id=correlation_id,
    )


@router.post(
    "",
    response_model=APIResponse[LeadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create lead",
    description="Create a new lead manually.",
)
async def create_lead(
    request: LeadCreateRequest,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
) -> APIResponse[LeadResponse]:
    """
    Create a new lead.

    Returns the created lead with generated ID.
    """
    now = datetime.now(timezone.utc)

    lead_data = {
        "id": str(uuid4()),
        "name": request.name,
        "phone": request.phone,
        "website": str(request.website) if request.website else None,
        "email": request.email,
        "business_type": request.business_type,
        "categories": request.categories,
        "location": request.location.model_dump() if request.location else None,
        "tags": request.tags,
        "notes": request.notes,
        "source": request.source.value,
        "status": LeadStatusEnum.NEW.value,
        "quality_score": _calculate_quality_score(request),
        "scraped_at": now,
        "status_updated_at": now,
        "metrics": {},
    }

    lead_id = lead_store.add_lead(lead_data)

    logger.info(
        "lead_created",
        lead_id=lead_id,
        name=request.name,
        source=request.source.value,
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=_lead_dict_to_response(lead_data),
        correlation_id=correlation_id,
    )


@router.put(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    summary="Update lead",
    description="Update lead status and other fields.",
    responses={
        404: {"model": ErrorResponse, "description": "Lead not found"},
    },
)
async def update_lead(
    lead_id: str,
    request: LeadUpdateRequest,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
) -> APIResponse[LeadResponse]:
    """
    Update a lead.

    Updates the specified fields and returns the updated lead.
    """
    lead = lead_store.get_lead(lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID '{lead_id}' not found",
        )

    # Build updates
    updates = {}
    if request.status is not None:
        updates["status"] = request.status.value
        updates["status_updated_at"] = datetime.now(timezone.utc)
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.notes is not None:
        updates["notes"] = request.notes
    if request.email is not None:
        updates["email"] = request.email
    if request.phone is not None:
        updates["phone"] = request.phone

    updated_lead = lead_store.update_lead(lead_id, updates)

    logger.info(
        "lead_updated",
        lead_id=lead_id,
        updates=list(updates.keys()),
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=_lead_dict_to_response(updated_lead),
        correlation_id=correlation_id,
    )


@router.delete(
    "/{lead_id}",
    response_model=APIResponse[None],
    summary="Delete lead",
    description="Delete a lead (GDPR compliance - right to erasure).",
    responses={
        404: {"model": ErrorResponse, "description": "Lead not found"},
    },
)
async def delete_lead(
    lead_id: str,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
) -> APIResponse[None]:
    """
    Delete a lead.

    Implements GDPR Article 17 - Right to erasure.
    Permanently deletes all lead data.
    """
    success = lead_store.delete_lead(lead_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID '{lead_id}' not found",
        )

    logger.info(
        "lead_deleted",
        lead_id=lead_id,
        gdpr_action="erasure",
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=None,
        correlation_id=correlation_id,
    )


@router.post(
    "/export",
    summary="Export leads",
    description="Export leads to CSV, JSON, or Google Sheets.",
)
async def export_leads(
    request: LeadExportRequest,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
):
    """
    Export leads to various formats.

    Supports:
    - CSV: Returns streaming CSV file
    - JSON: Returns JSON array
    - Sheets: Exports to Google Sheets (requires spreadsheet_id)
    """
    # Build filters from request
    filters = {}
    if request.filters:
        if request.filters.status:
            filters["status"] = request.filters.status.value
        if request.filters.source:
            filters["source"] = request.filters.source.value
        if request.filters.business_type:
            filters["business_type"] = request.filters.business_type
        if request.filters.min_quality_score is not None:
            filters["min_quality_score"] = request.filters.min_quality_score
        if request.filters.has_email is not None:
            filters["has_email"] = request.filters.has_email
        if request.filters.has_phone is not None:
            filters["has_phone"] = request.filters.has_phone

    # Get all matching leads (no pagination for export)
    leads, total = lead_store.list_leads(filters=filters, offset=0, limit=10000)

    # Default fields for export
    fields = request.fields or [
        "id", "name", "phone", "email", "website", "business_type",
        "status", "quality_score", "scraped_at"
    ]

    logger.info(
        "leads_export_started",
        format=request.format,
        total_leads=total,
        filters=filters,
        correlation_id=correlation_id,
    )

    if request.format == "csv":
        return _export_csv(leads, fields, correlation_id)
    elif request.format == "json":
        return _export_json(leads, fields, correlation_id)
    elif request.format == "sheets":
        return await _export_sheets(
            leads, fields, request.spreadsheet_id, request.worksheet_name, correlation_id
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format: {request.format}",
        )


def _export_csv(leads: list[dict], fields: list[str], correlation_id: str) -> StreamingResponse:
    """Generate CSV export."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()

    for lead in leads:
        # Flatten nested structures
        row = {}
        for field in fields:
            value = lead.get(field)
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            row[field] = value
        writer.writerow(row)

    output.seek(0)

    logger.info(
        "leads_exported_csv",
        count=len(leads),
        correlation_id=correlation_id,
    )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=leads_export_{correlation_id[:8]}.csv",
            "X-Correlation-ID": correlation_id,
        },
    )


def _export_json(leads: list[dict], fields: list[str], correlation_id: str) -> dict:
    """Generate JSON export."""
    # Filter to requested fields
    filtered_leads = []
    for lead in leads:
        filtered = {}
        for field in fields:
            value = lead.get(field)
            if isinstance(value, datetime):
                value = value.isoformat()
            filtered[field] = value
        filtered_leads.append(filtered)

    logger.info(
        "leads_exported_json",
        count=len(leads),
        correlation_id=correlation_id,
    )

    return {
        "success": True,
        "data": filtered_leads,
        "count": len(filtered_leads),
        "correlation_id": correlation_id,
    }


async def _export_sheets(
    leads: list[dict],
    fields: list[str],
    spreadsheet_id: str | None,
    worksheet_name: str,
    correlation_id: str,
) -> LeadExportResponse:
    """Export to Google Sheets."""
    if not spreadsheet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="spreadsheet_id is required for Sheets export",
        )

    sheets_service = await get_sheets_service_optional()
    if not sheets_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sheets service not configured",
        )

    # Prepare data for export
    rows = []
    for lead in leads:
        row = []
        for field in fields:
            value = lead.get(field)
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            row.append(str(value) if value is not None else "")
        rows.append(row)

    # Export to Sheets
    try:
        await sheets_service.write_leads(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=worksheet_name,
            headers=fields,
            rows=rows,
        )
    except Exception as e:
        logger.error(
            "sheets_export_failed",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export to Sheets: {e}",
        )

    logger.info(
        "leads_exported_sheets",
        count=len(leads),
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet_name,
        correlation_id=correlation_id,
    )

    return LeadExportResponse(
        format="sheets",
        exported_count=len(leads),
        spreadsheet_url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        correlation_id=correlation_id,
    )


def _calculate_quality_score(request: LeadCreateRequest) -> int:
    """Calculate quality score for a new lead."""
    score = 0

    if request.name:
        score += 10
    if request.phone:
        score += 20
    if request.email:
        score += 25
    if request.website:
        score += 15
    if request.location:
        score += 10
        if request.location.formatted_address:
            score += 5
    if request.business_type:
        score += 10
    if request.categories:
        score += 5

    return min(100, score)
