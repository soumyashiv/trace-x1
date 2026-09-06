"""Graph router — build and retrieve transaction graph for a case."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import CurrentUser
from app.schemas.schemas import GraphResponse
from app.services.graph_service import build_graph
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/cases/{case_id}/graph", tags=["Graph"])

_redis_client = None


@router.post("/{wallet_address}", response_model=GraphResponse)
async def build_transaction_graph(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    max_hops: int = Query(4, ge=1, le=6),
):
    """Build or refresh the transaction graph for a wallet within a case."""
    from app.models import AuditLog, AuditAction
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.RUN_ANALYSIS,
        resource_id=case_id,
        resource_type="graph",
    ))
    return await build_graph(db, case_id, wallet_address, max_hops=max_hops, redis_client=_redis_client)


@router.get("/{wallet_address}", response_model=GraphResponse)
async def get_graph(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    max_hops: int = Query(4, ge=1, le=6),
):
    """Get cached graph or build fresh."""
    return await build_graph(db, case_id, wallet_address, max_hops=max_hops, redis_client=_redis_client)
