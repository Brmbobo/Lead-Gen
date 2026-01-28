"""
Workflow management endpoints for Lead-Gen API.

Provides:
- List available workflows
- Get workflow configuration
- Execute workflow
- Get execution status
- Stop running workflow
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from lead_gen.api.dependencies import (
    get_correlation_id,
    get_lead_store,
    LeadStore,
)
from lead_gen.api.schemas import (
    APIResponse,
    ErrorResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowStatusEnum,
    WorkflowStatusResponse,
    WorkflowStepSchema,
    StepTypeEnum,
)


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# In-memory execution state (replace with proper queue in production)
_executions: dict[str, dict] = {}


def _get_sample_workflows() -> list[dict]:
    """Get sample workflow configurations."""
    return [
        {
            "id": "slovakia-dentists",
            "name": "Slovakia Dentists",
            "description": "Scrape Slovak dentists, enrich emails, generate outreach",
            "version": "1.0",
            "steps": [
                {
                    "id": "step-1",
                    "name": "scrape_dentists",
                    "type": StepTypeEnum.SCRAPE.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 300,
                },
                {
                    "id": "step-2",
                    "name": "filter_quality",
                    "type": StepTypeEnum.FILTER.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 60,
                },
                {
                    "id": "step-3",
                    "name": "enrich_emails",
                    "type": StepTypeEnum.ENRICH.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 600,
                },
                {
                    "id": "step-4",
                    "name": "generate_messages",
                    "type": StepTypeEnum.GENERATE.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 300,
                },
                {
                    "id": "step-5",
                    "name": "export_to_sheets",
                    "type": StepTypeEnum.EXPORT.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 120,
                },
            ],
            "status": WorkflowStatusEnum.PENDING.value,
            "enabled": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "total_leads_processed": 0,
            "progress_percent": 0.0,
            "error_message": "",
            "tags": ["dentists", "slovakia", "outreach"],
        },
        {
            "id": "bratislava-restaurants",
            "name": "Bratislava Restaurants",
            "description": "Scrape restaurants in Bratislava for marketing campaigns",
            "version": "1.0",
            "steps": [
                {
                    "id": "step-1",
                    "name": "scrape_restaurants",
                    "type": StepTypeEnum.SCRAPE.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 300,
                },
                {
                    "id": "step-2",
                    "name": "export_csv",
                    "type": StepTypeEnum.EXPORT.value,
                    "enabled": True,
                    "status": WorkflowStatusEnum.PENDING.value,
                    "timeout_seconds": 60,
                },
            ],
            "status": WorkflowStatusEnum.PENDING.value,
            "enabled": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "total_leads_processed": 0,
            "progress_percent": 0.0,
            "error_message": "",
            "tags": ["restaurants", "bratislava", "marketing"],
        },
    ]


def _workflow_dict_to_response(workflow: dict) -> WorkflowResponse:
    """Convert workflow dict to response schema."""
    steps = [
        WorkflowStepSchema(
            id=step.get("id", ""),
            name=step.get("name", ""),
            type=step.get("type", StepTypeEnum.SCRAPE),
            enabled=step.get("enabled", True),
            status=step.get("status", WorkflowStatusEnum.PENDING),
            timeout_seconds=step.get("timeout_seconds", 300),
            started_at=step.get("started_at"),
            completed_at=step.get("completed_at"),
            error_message=step.get("error_message", ""),
            output_count=step.get("output_count", 0),
        )
        for step in workflow.get("steps", [])
    ]

    return WorkflowResponse(
        id=workflow.get("id", ""),
        name=workflow.get("name", ""),
        description=workflow.get("description", ""),
        version=workflow.get("version", "1.0"),
        steps=steps,
        status=workflow.get("status", WorkflowStatusEnum.PENDING),
        enabled=workflow.get("enabled", True),
        created_at=workflow.get("created_at", datetime.now(timezone.utc)),
        updated_at=workflow.get("updated_at", datetime.now(timezone.utc)),
        started_at=workflow.get("started_at"),
        completed_at=workflow.get("completed_at"),
        total_leads_processed=workflow.get("total_leads_processed", 0),
        progress_percent=workflow.get("progress_percent", 0.0),
        error_message=workflow.get("error_message", ""),
        tags=workflow.get("tags", []),
    )


@router.get(
    "",
    response_model=APIResponse[list[WorkflowResponse]],
    summary="List workflows",
    description="List all available workflow configurations.",
)
async def list_workflows(
    correlation_id: Annotated[str, Depends(get_correlation_id)],
) -> APIResponse[list[WorkflowResponse]]:
    """
    List all available workflows.

    Returns predefined workflow configurations.
    """
    workflows = _get_sample_workflows()

    logger.info(
        "workflows_listed",
        count=len(workflows),
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=[_workflow_dict_to_response(wf) for wf in workflows],
        correlation_id=correlation_id,
    )


@router.get(
    "/{workflow_id}",
    response_model=APIResponse[WorkflowResponse],
    summary="Get workflow",
    description="Get a workflow configuration by ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def get_workflow(
    workflow_id: str,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
) -> APIResponse[WorkflowResponse]:
    """
    Get a workflow by ID.

    Returns the workflow configuration.
    """
    workflows = _get_sample_workflows()
    workflow = next((wf for wf in workflows if wf["id"] == workflow_id), None)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID '{workflow_id}' not found",
        )

    logger.info(
        "workflow_retrieved",
        workflow_id=workflow_id,
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=_workflow_dict_to_response(workflow),
        correlation_id=correlation_id,
    )


@router.post(
    "/{workflow_id}/run",
    response_model=WorkflowRunResponse,
    summary="Run workflow",
    description="Execute a workflow.",
)
async def run_workflow(
    workflow_id: str,
    request: WorkflowRunRequest,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    lead_store: Annotated[LeadStore, Depends(get_lead_store)],
) -> WorkflowRunResponse:
    """
    Execute a workflow.

    Starts workflow execution in the background.
    Use the status endpoint to track progress.
    """
    workflows = _get_sample_workflows()
    workflow = next((wf for wf in workflows if wf["id"] == workflow_id), None)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID '{workflow_id}' not found",
        )

    # Check if already running
    for exec_id, execution in _executions.items():
        if execution["workflow_id"] == workflow_id and execution["status"] == WorkflowStatusEnum.RUNNING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow '{workflow_id}' is already running",
            )

    # Create execution record
    execution_id = str(uuid4())
    now = datetime.now(timezone.utc)

    execution = {
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "status": WorkflowStatusEnum.RUNNING.value if not request.dry_run else WorkflowStatusEnum.COMPLETED.value,
        "dry_run": request.dry_run,
        "max_leads": request.max_leads,
        "overrides": request.overrides,
        "started_at": now,
        "current_step": workflow["steps"][0]["name"] if workflow["steps"] else None,
        "progress_percent": 0.0,
        "leads_processed": 0,
        "error_message": None,
    }

    _executions[execution_id] = execution

    logger.info(
        "workflow_started",
        workflow_id=workflow_id,
        execution_id=execution_id,
        dry_run=request.dry_run,
        max_leads=request.max_leads,
        correlation_id=correlation_id,
    )

    # In production, this would trigger async execution
    # For now, we just record the execution start

    message = "Workflow execution started"
    if request.dry_run:
        message = "Dry run completed - no changes made"

    return WorkflowRunResponse(
        workflow_id=workflow_id,
        execution_id=execution_id,
        status=WorkflowStatusEnum.RUNNING if not request.dry_run else WorkflowStatusEnum.COMPLETED,
        message=message,
        started_at=now,
        correlation_id=correlation_id,
    )


@router.get(
    "/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get workflow status",
    description="Get the execution status of a workflow.",
)
async def get_workflow_status(
    workflow_id: str,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
) -> WorkflowStatusResponse:
    """
    Get workflow execution status.

    Returns the current status and progress.
    """
    # Find the most recent execution for this workflow
    execution = None
    for exec_data in _executions.values():
        if exec_data["workflow_id"] == workflow_id:
            if execution is None or exec_data["started_at"] > execution["started_at"]:
                execution = exec_data

    if not execution:
        # No execution found - return pending status
        workflows = _get_sample_workflows()
        workflow = next((wf for wf in workflows if wf["id"] == workflow_id), None)

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID '{workflow_id}' not found",
            )

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            execution_id=None,
            status=WorkflowStatusEnum.PENDING,
            current_step=None,
            progress_percent=0.0,
            leads_processed=0,
            correlation_id=correlation_id,
        )

    # Calculate elapsed time
    elapsed = None
    if execution["started_at"]:
        elapsed = (datetime.now(timezone.utc) - execution["started_at"]).total_seconds()

    logger.info(
        "workflow_status_retrieved",
        workflow_id=workflow_id,
        execution_id=execution["execution_id"],
        status=execution["status"],
        correlation_id=correlation_id,
    )

    return WorkflowStatusResponse(
        workflow_id=workflow_id,
        execution_id=execution["execution_id"],
        status=execution["status"],
        current_step=execution.get("current_step"),
        progress_percent=execution.get("progress_percent", 0.0),
        leads_processed=execution.get("leads_processed", 0),
        started_at=execution.get("started_at"),
        elapsed_seconds=elapsed,
        error_message=execution.get("error_message"),
        correlation_id=correlation_id,
    )


@router.post(
    "/{workflow_id}/stop",
    response_model=APIResponse[None],
    summary="Stop workflow",
    description="Stop a running workflow.",
)
async def stop_workflow(
    workflow_id: str,
    correlation_id: Annotated[str, Depends(get_correlation_id)],
) -> APIResponse[None]:
    """
    Stop a running workflow.

    Cancels the workflow execution gracefully.
    """
    # Find running execution
    execution = None
    for exec_data in _executions.values():
        if (
            exec_data["workflow_id"] == workflow_id
            and exec_data["status"] == WorkflowStatusEnum.RUNNING.value
        ):
            execution = exec_data
            break

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No running execution found for workflow '{workflow_id}'",
        )

    # Update status to cancelled
    execution["status"] = WorkflowStatusEnum.CANCELLED.value
    execution["completed_at"] = datetime.now(timezone.utc)

    logger.info(
        "workflow_stopped",
        workflow_id=workflow_id,
        execution_id=execution["execution_id"],
        correlation_id=correlation_id,
    )

    return APIResponse(
        success=True,
        data=None,
        correlation_id=correlation_id,
    )
