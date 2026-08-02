from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.audit import record_audit_event
from app.core.auth import AuthenticatedMemberContext, require_admin, require_member
from app.domain.knowledge import FileType, KnowledgeSourceDocument
from app.schemas.knowledge import RetryResponse, SourceMetricsResponse, SourceResponse, SourceVersionResponse
from app.services.ingestion_pipeline import IngestionPipelineService
from app.services.supabase_storage import SupabaseStorageService, storage_service

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["sources"])
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _storage(ctx: AuthenticatedMemberContext) -> SupabaseStorageService:
    return (
        SupabaseStorageService(client=ctx.supabase, user_id=ctx.user.id)
        if ctx.supabase is not None
        else storage_service
    )


def _source_response(doc: KnowledgeSourceDocument) -> SourceResponse:
    return SourceResponse(
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


@router.get("/sources", response_model=list[SourceResponse])
async def list_workspace_sources(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> list[SourceResponse]:
    return [_source_response(doc) for doc in _storage(ctx).list_sources(workspace_id)]


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
            status_code=400,
            detail="Unsupported file extension. Only Markdown (.md), Text (.txt), and PDF (.pdf) files are accepted.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 50 MB limit.")

    storage = _storage(ctx)
    title = filename.rsplit(".", 1)[0].replace("_", " ").title()
    source_doc, version = storage.create_or_update_source(
        workspace_id=workspace_id,
        title=title,
        file_type=file_type,
        file_content=content,
        filename=filename,
    )
    updated_doc = IngestionPipelineService(storage=storage).process_source_ingestion(
        workspace_id, source_doc.id
    )
    record_audit_event(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        action="SOURCE_UPLOADED",
        target_id=source_doc.id,
        details={"version": version.version_number, "filename": filename, "file_type": file_type.value},
    )
    return _source_response(updated_doc)


@router.post("/sources/{source_id}/retry", response_model=RetryResponse)
async def retry_failed_ingestion(
    workspace_id: str,
    source_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_admin),
) -> RetryResponse:
    storage = _storage(ctx)
    source_doc = storage.get_source(workspace_id, source_id)
    if not source_doc:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")

    updated_doc = IngestionPipelineService(storage=storage).process_source_ingestion(
        workspace_id, source_id
    )
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
    metrics = _storage(ctx).get_metrics(workspace_id)
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
    storage = _storage(ctx)
    if not storage.get_source(workspace_id, source_id):
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    return [
        SourceVersionResponse(
            version_id=version.version_id,
            source_id=version.source_id,
            version_number=version.version_number,
            file_path=version.file_path,
            file_size=version.file_size,
            created_at=version.created_at,
        )
        for version in storage.list_versions(workspace_id, source_id)
    ]
