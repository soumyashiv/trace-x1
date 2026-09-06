"""
Case Service — CRUD operations for investigations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Case, CaseStatus, Wallet, Transaction
from app.schemas.schemas import CaseCreate, CaseOut, CaseUpdate
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _generate_case_number() -> str:
    """Generate a unique case number: TXCASE-YYYYMM-XXXXX"""
    now = datetime.now(timezone.utc)
    suffix = str(uuid.uuid4().int)[:5].upper()
    return f"TXCASE-{now.strftime('%Y%m')}-{suffix}"


async def create_case(db: AsyncSession, data: CaseCreate, user_id: str) -> Case:
    case = Case(
        case_number=_generate_case_number(),
        title=data.title,
        description=data.description,
        victim_name=data.victim_name,
        victim_contact=data.victim_contact,
        reported_amount_usd=data.reported_amount_usd,
        status=CaseStatus.OPEN,
        created_by=str(user_id),
        tags=data.tags,
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    logger.info("case_created", case_id=str(case.id), case_number=case.case_number)
    return case


async def get_case(db: AsyncSession, case_id: str) -> Optional[Case]:
    result = await db.execute(select(Case).where(Case.id == str(case_id)))
    return result.scalar_one_or_none()


async def list_cases(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Case], int]:
    query = select(Case)
    if status:
        query = query.where(Case.status == status)
    query = query.order_by(Case.created_at.desc())

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def update_case(db: AsyncSession, case: Case, data: CaseUpdate) -> Case:
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(case, field, val)
    case.updated_at = datetime.now(timezone.utc)
    if data.status == "closed":
        case.closed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(case)
    return case


async def delete_case(db: AsyncSession, case: Case) -> None:
    await db.delete(case)
    await db.flush()


async def get_case_stats(db: AsyncSession, case_id) -> dict:
    case_id_str = str(case_id)
    wallet_count = (
        await db.execute(select(func.count()).where(Wallet.case_id == case_id_str))
    ).scalar_one()
    transaction_count = (
        await db.execute(select(func.count()).where(Transaction.case_id == case_id_str))
    ).scalar_one()
    return {"wallet_count": wallet_count, "transaction_count": transaction_count}


def case_to_out(case: Case, wallet_count: int = 0, transaction_count: int = 0) -> CaseOut:
    return CaseOut(
        id=str(case.id),
        case_number=case.case_number,
        title=case.title,
        description=case.description,
        victim_name=case.victim_name,
        victim_contact=case.victim_contact,
        reported_amount_usd=case.reported_amount_usd,
        status=case.status.value if hasattr(case.status, "value") else case.status,
        created_by=str(case.created_by),
        created_at=case.created_at,
        updated_at=case.updated_at,
        closed_at=case.closed_at,
        tags=case.tags or [],
        wallet_count=wallet_count,
        transaction_count=transaction_count,
    )
