"""
TRACE-X FastAPI Application — SIH26183
Real-Time Identification of Fraud-Linked Cryptocurrency Exchanges
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.database import create_tables, get_db, AsyncSessionLocal
from app.routers import auth, cases, wallets, graph, risk, vasp, reports
from app.schemas.schemas import SystemHealthResponse, ServiceHealth

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

# ── Rate Limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


# ── Startup / Shutdown ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("tracex_startup", version=settings.app_version, env=settings.environment)

    # Create DB tables
    await create_tables()
    logger.info("database_tables_ready")

    # Seed demo data
    if settings.seed_demo_data:
        await seed_demo_data()

    yield

    logger.info("tracex_shutdown")


async def seed_demo_data() -> None:
    """Seed the demo investigation case on startup if it doesn't already exist."""
    from app.models import User, UserRole, Case, CaseStatus, Wallet, WalletType
    from app.core.security import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            # Create demo users
            for username, role, email, fullname in [
                ("admin", UserRole.ADMIN, "admin@tracex.demo", "System Administrator"),
                ("analyst", UserRole.ANALYST, "analyst@tracex.demo", "Lead Analyst"),
                ("viewer", UserRole.VIEWER, "viewer@tracex.demo", "Report Viewer"),
            ]:
                existing = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
                if not existing:
                    u = User(
                        username=username,
                        email=email,
                        hashed_password=hash_password("tracex123"),
                        full_name=fullname,
                        role=role,
                    )
                    db.add(u)

            await db.flush()

            # Get analyst user for case ownership
            analyst = (await db.execute(select(User).where(User.username == "analyst"))).scalar_one()

            # Create demo case
            existing_case = (await db.execute(
                select(Case).where(Case.case_number == "TXCASE-DEMO-00001")
            )).scalar_one_or_none()

            if not existing_case:
                demo_case = Case(
                    case_number="TXCASE-DEMO-00001",
                    title="SIH26183 Demo: Crypto Fraud Investigation",
                    description=(
                        "Demo investigation: Victim Rajeev Kumar reported a cryptocurrency phishing fraud "
                        "totalling INR 6.5 lakh (approx $7,925 USD). Suspect wallet traced through 4 hops "
                        "to a known exchange. This case uses 100% synthetic data."
                    ),
                    victim_name="Rajeev Kumar (Synthetic)",
                    victim_contact="demo@tracex.sih",
                    reported_amount_usd=7925.0,
                    status=CaseStatus.IN_PROGRESS,
                    created_by=analyst.id,
                    tags=["demo", "sih26183", "phishing"],
                )
                db.add(demo_case)
                await db.flush()
                await db.refresh(demo_case)

                # Add seed wallet
                seed_wallet = Wallet(
                    case_id=demo_case.id,
                    address="0xsuspect000000000000000000000000000000001",
                    chain="ethereum",
                    wallet_type=WalletType.SUSPECT,
                    label="Suspect Wallet (Phishing Operator)",
                    is_seed=True,
                )
                db.add(seed_wallet)

                logger.info("demo_case_seeded", case_id=str(demo_case.id))

            await db.commit()
            logger.info("demo_data_seeded")
        except Exception as e:
            await db.rollback()
            logger.error("demo_seed_failed", error=str(e))


# ── App Instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="TRACE-X API",
    description=(
        "**TRACE-X** — SIH26183: Real-Time Identification of Fraud-Linked Cryptocurrency Exchanges.\n\n"
        "Convert victim-reported wallet addresses into structured investigative intelligence.\n\n"
        "**DISCLAIMER**: All demo data is entirely synthetic. This API does not connect to live blockchains "
        "or government systems in demo mode."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    logger.info("request_start", method=request.method, path=request.url.path, request_id=request_id)
    response = await call_next(request)
    logger.info("request_end", status=response.status_code, request_id=request_id)
    return response


# ── Exception Handlers ─────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(wallets.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(vasp.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


# ── Health endpoints ───────────────────────────────────────────────────────────

@app.get("/health", response_model=SystemHealthResponse, tags=["Health"])
async def health():
    services: list[ServiceHealth] = []

    # DB check
    try:
        import time
        t0 = time.monotonic()
        async with AsyncSessionLocal() as s:
            from sqlalchemy import text
            await s.execute(text("SELECT 1"))
        services.append(ServiceHealth(name="database", status="healthy", latency_ms=round((time.monotonic() - t0) * 1000, 1)))
    except Exception as e:
        services.append(ServiceHealth(name="database", status="down", message=str(e)[:100]))

    # Blockchain provider check
    from app.blockchain import get_provider
    provider = get_provider()
    services.append(ServiceHealth(
        name="blockchain_provider",
        status="healthy",
        message=f"{provider.provider_name} | live={provider.is_live}",
    ))

    overall = "healthy" if all(s.status == "healthy" for s in services) else "degraded"
    return SystemHealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        services=services,
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "TRACE-X API",
        "version": settings.app_version,
        "description": "SIH26183 — Fraud-Linked Cryptocurrency Exchange Identification",
        "docs": "/docs",
        "health": "/health",
    }
