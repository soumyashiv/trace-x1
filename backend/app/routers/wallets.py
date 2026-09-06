"""Wallets router — add and list wallets for a case."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Wallet, WalletType, Transaction
from app.routers.auth import CurrentUser
from app.schemas.schemas import WalletCreate, WalletOut, TransactionOut

router = APIRouter(prefix="/cases/{case_id}/wallets", tags=["Wallets"])


@router.get("", response_model=list[WalletOut])
async def list_wallets(case_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Wallet).where(Wallet.case_id == case_id))
    return result.scalars().all()


@router.post("", response_model=WalletOut, status_code=status.HTTP_201_CREATED)
async def add_wallet(case_id: str, data: WalletCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(Wallet).where(Wallet.case_id == case_id, Wallet.address == data.address)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet already added to this case")

    type_map = {
        "suspect": WalletType.SUSPECT,
        "victim": WalletType.VICTIM,
        "intermediary": WalletType.INTERMEDIARY,
        "exchange": WalletType.EXCHANGE,
    }
    wallet = Wallet(
        case_id=case_id,
        address=data.address,
        chain=data.chain,
        wallet_type=type_map.get(data.wallet_type, WalletType.SUSPECT),
        label=data.label,
        is_seed=True,
    )
    db.add(wallet)
    await db.flush()
    await db.refresh(wallet)
    return wallet


@router.get("/{wallet_id}", response_model=WalletOut)
async def get_wallet(case_id: str, wallet_id: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Wallet).where(Wallet.id == wallet_id, Wallet.case_id == case_id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet


@router.get("/{wallet_address}/transactions", response_model=list[TransactionOut])
async def get_wallet_transactions(
    case_id: str,
    wallet_address: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.case_id == case_id,
        ).where(
            (Transaction.from_address == wallet_address) | (Transaction.to_address == wallet_address)
        ).order_by(Transaction.timestamp).offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all()
