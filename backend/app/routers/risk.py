"""Risk analysis router."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import CurrentUser
from app.schemas.schemas import RiskAnalysisResponse
from app.services.risk_service import analyze_wallet_risk

router = APIRouter(prefix="/cases/{case_id}/risk", tags=["Risk"])


@router.post("/{wallet_address}", response_model=RiskAnalysisResponse)
async def analyze_risk(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Run full risk analysis on a wallet within a case."""
    return await analyze_wallet_risk(db, case_id, wallet_address)


@router.get("/{wallet_address}", response_model=RiskAnalysisResponse)
async def get_risk(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get risk analysis (runs fresh if not cached)."""
    return await analyze_wallet_risk(db, case_id, wallet_address)
