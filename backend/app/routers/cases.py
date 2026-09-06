"""Cases router — CRUD for investigation cases."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import CurrentUser
from app.schemas.schemas import CaseCreate, CaseListResponse, CaseOut, CaseUpdate
from app.services import case_service
from app.models import AuditLog, AuditAction

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.get("", response_model=CaseListResponse)
async def list_cases(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    cases, total = await case_service.list_cases(db, status=status_filter, page=page, page_size=page_size)
    items = []
    for case in cases:
        stats = await case_service.get_case_stats(db, case.id)
        items.append(case_service.case_to_out(case, **stats))
    return CaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(data: CaseCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    case = await case_service.create_case(db, data, user.id)
    db.add(AuditLog(user_id=user.id, action=AuditAction.CREATE_CASE, resource_id=str(case.id), resource_type="case"))
    await db.flush()
    stats = await case_service.get_case_stats(db, case.id)
    return case_service.case_to_out(case, **stats)


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(case_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    case = await case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    db.add(AuditLog(user_id=user.id, action=AuditAction.VIEW_CASE, resource_id=case_id, resource_type="case"))
    await db.flush()
    stats = await case_service.get_case_stats(db, case_id)
    return case_service.case_to_out(case, **stats)


@router.patch("/{case_id}", response_model=CaseOut)
async def update_case(case_id: str, data: CaseUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    case = await case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    case = await case_service.update_case(db, case, data)
    stats = await case_service.get_case_stats(db, case_id)
    return case_service.case_to_out(case, **stats)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    case = await case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    db.add(AuditLog(user_id=user.id, action=AuditAction.DELETE_CASE, resource_id=case_id, resource_type="case"))
    await case_service.delete_case(db, case)
