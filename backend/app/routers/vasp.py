"""VASP attribution router."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import CurrentUser
from app.schemas.schemas import VaspAttributionResponse
from app.services.vasp_service import attribute_vasp

router = APIRouter(prefix="/cases/{case_id}/vasp", tags=["VASP Attribution"])


@router.post("/{wallet_address}", response_model=VaspAttributionResponse)
async def run_vasp_attribution(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Run VASP attribution for a wallet."""
    return await attribute_vasp(db, case_id, wallet_address)


@router.get("/{wallet_address}", response_model=VaspAttributionResponse)
async def get_vasp_attribution(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get VASP attribution (reruns fresh)."""
    return await attribute_vasp(db, case_id, wallet_address)
