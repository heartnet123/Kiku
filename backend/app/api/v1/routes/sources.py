from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.audit import record_audit_event
from app.core.auth import AuthenticatedMemberContext, require_admin, require_member
from app.domain.knowledge import FileType
from app.schemas.knowledge import RetryResponse, SourceMetricsResponse, SourceResponse, SourceVersionResponse
from app.services.ingestion_pipeline import ingestion_service
from app.services.supabase_storage import storage_service

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["sources"])


@router.get("/sources", response_model=list[SourceResponse])
async def list_workspace_sources(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> list[SourceResponse]:
    docs = storage_service.list_sources(workspace_id)
    return [
        SourceResponse(
            id=doc.id,
            workspace_id=doc.workspace_id,
            title=doc.title,
            file_type=doc.file_type.value if isinstance(doc.file_type, FileType) else str(doc.file_type),
            current_version=doc.current_version,
            status=doc.status.value,
            status_reason=doc.status_reason,
            page=1,
            updated_at=doc.updated_at,
        )
        for doc in docs
    ]


@router.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_source(
    workspace_id: str,
    file: UploadFile = File(...),
    ctx: AuthenticatedMemberContext = Depends(require_admin),
) -> SourceResponse:
    filename = file.filename or "uploaded_file.txt"
    lower_filename = filename.lower()

    if lower_filename.endswith(".md"):
        file_type = FileType.MARKDOWN
    elif lower_filename.endswith(".pdf"):
        file_type = FileType.PDF
    elif lower_filename.endswith(".txt"):
        file_type = FileType.TEXT
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension. Only Markdown (.md), Text (.txt), and PDF (.pdf) files are accepted.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    title = filename.rsplit(".", 1)[0].replace("_", " ").title()
    source_doc, version = storage_service.create_or_update_source(
        workspace_id=workspace_id,
        title=title,
        file_type=file_type,
        file_content=content,
        filename=filename,
    )

    # Process ingestion pipeline (asynchronous ingestion execution)
    ingestion_service.process_source_ingestion(workspace_id, source_doc.id)

    record_audit_event(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        action="SOURCE_UPLOADED",
        target_id=source_doc.id,
        details={"version": version.version_number, "filename": filename, "file_type": file_type.value},
    )

    updated_doc = storage_service.get_source(workspace_id, source_doc.id) or source_doc
    return SourceResponse(
        id=updated_doc.id,
        workspace_id=updated_doc.workspace_id,
        title=updated_doc.title,
        file_type=updated_doc.file_type.value if isinstance(updated_doc.file_type, FileType) else str(updated_doc.file_type),
        current_version=updated_doc.current_version,
        status=updated_doc.status.value,
        status_reason=updated_doc.status_reason,
        page=1,
        updated_at=updated_doc.updated_at,
    )


@router.post("/sources/{source_id}/retry", response_model=RetryResponse)
async def retry_failed_ingestion(
    workspace_id: str,
    source_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_admin),
) -> RetryResponse:
    source_doc = storage_service.get_source(workspace_id, source_id)
    if not source_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge source '{source_id}' not found in workspace '{workspace_id}'.",
        )

    # Run ingestion retry
    updated_doc = ingestion_service.process_source_ingestion(workspace_id, source_id)

    record_audit_event(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        action="SOURCE_INGESTION_RETRIED",
        target_id=source_id,
        details={"status": updated_doc.status.value, "version": updated_doc.current_version},
    )

    return RetryResponse(
        status=updated_doc.status.value,
        message=f"Ingestion retried for '{source_doc.title}'. Current status: {updated_doc.status.value}.",
    )


@router.get("/sources/metrics", response_model=SourceMetricsResponse)
async def get_sources_telemetry(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> SourceMetricsResponse:
    metrics = storage_service.get_metrics(workspace_id)
    return SourceMetricsResponse(
        total_attempts=metrics["total_attempts"],
        ready_count=metrics["ready_count"],
        failed_count=metrics["failed_count"],
        retrying_count=metrics["retrying_count"],
        by_type=metrics["by_type"],
    )


@router.get("/sources/{source_id}/versions", response_model=list[SourceVersionResponse])
async def list_source_versions(
    workspace_id: str,
    source_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> list[SourceVersionResponse]:
    source_doc = storage_service.get_source(workspace_id, source_id)
    if not source_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge source '{source_id}' not found in workspace '{workspace_id}'.",
        )

    versions = storage_service.list_versions(workspace_id, source_id)
    return [
        SourceVersionResponse(
            version_id=v.version_id,
            source_id=v.source_id,
            version_number=v.version_number,
            file_path=v.file_path,
            file_size=v.file_size,
            created_at=v.created_at,
        )
        for v in versions
    ]
