"""Reports router — generate and download reports."""
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Report, AuditLog, AuditAction
from app.routers.auth import CurrentUser
from app.schemas.schemas import ReportGenerateRequest, ReportOut
from app.services.report_service import generate_report

router = APIRouter(prefix="/cases/{case_id}/reports", tags=["Reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(
    case_id: str,
    data: ReportGenerateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new investigation report."""
    report = await generate_report(db, case_id, data.format, user.id)
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.GENERATE_REPORT,
        resource_id=case_id,
        resource_type="report",
        detail={"format": data.format},
    ))
    await db.flush()
    return ReportOut(
        id=str(report.id),
        case_id=str(report.case_id),
        format=report.format.value if hasattr(report.format, "value") else report.format,
        file_path=report.file_path,
        generated_at=report.generated_at,
        download_url=f"/api/v1/cases/{case_id}/reports/{report.id}/download",
    )


@router.get("", response_model=list[ReportOut])
async def list_reports(case_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.case_id == case_id).order_by(Report.generated_at.desc()))
    reports = result.scalars().all()
    return [
        ReportOut(
            id=str(r.id),
            case_id=str(r.case_id),
            format=r.format.value if hasattr(r.format, "value") else r.format,
            file_path=r.file_path,
            generated_at=r.generated_at,
            download_url=f"/api/v1/cases/{case_id}/reports/{r.id}/download",
        )
        for r in reports
    ]


@router.get("/{report_id}/download")
async def download_report(case_id: str, report_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id, Report.case_id == case_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    fmt = report.format.value if hasattr(report.format, "value") else report.format
    media_types = {"pdf": "application/pdf", "json": "application/json", "csv": "text/csv"}
    return FileResponse(
        path=report.file_path,
        media_type=media_types.get(fmt, "application/octet-stream"),
        filename=os.path.basename(report.file_path),
    )
