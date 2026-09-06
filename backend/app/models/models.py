"""SQLAlchemy ORM models for TRACE-X.

NOTE: Uses String(36) for UUIDs so the same models work on SQLite (dev)
      and PostgreSQL (production) without any dialect-specific imports.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_str() -> str:
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    ARCHIVED = "archived"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_CASE = "create_case"
    VIEW_CASE = "view_case"
    RUN_ANALYSIS = "run_analysis"
    GENERATE_REPORT = "generate_report"
    DELETE_CASE = "delete_case"


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.ANALYST, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cases: Mapped[list["Case"]] = relationship("Case", back_populates="created_by_user", lazy="select")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="select")


# ─── Case ─────────────────────────────────────────────────────────────────────

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    victim_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    victim_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reported_amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.OPEN, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)

    created_by_user: Mapped["User"] = relationship("User", back_populates="cases", lazy="select")
    wallets: Mapped[list["Wallet"]] = relationship("Wallet", back_populates="case", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="case", cascade="all, delete-orphan")


# ─── Wallet ───────────────────────────────────────────────────────────────────

class WalletType(str, enum.Enum):
    SUSPECT = "suspect"
    VICTIM = "victim"
    INTERMEDIARY = "intermediary"
    EXCHANGE = "exchange"
    UNKNOWN = "unknown"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(32), default="ethereum", nullable=False)
    wallet_type: Mapped[WalletType] = mapped_column(Enum(WalletType), default=WalletType.SUSPECT, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel), nullable=True)
    risk_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    vasp_attribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    total_received_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_sent_usd: Mapped[float] = mapped_column(Float, default=0.0)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    graph_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="wallets")
    transactions_from: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.from_address_id", back_populates="from_wallet"
    )
    transactions_to: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.to_address_id", back_populates="to_wallet"
    )

    __table_args__ = (UniqueConstraint("case_id", "address", name="uq_wallet_case_address"),)


# ─── Transaction ──────────────────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    tx_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    from_address_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("wallets.id"), nullable=True)
    to_address_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("wallets.id"), nullable=True)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_eth: Mapped[float] = mapped_column(Float, nullable=False)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    gas_used: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gas_price_gwei: Mapped[float | None] = mapped_column(Float, nullable=True)
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chain: Mapped[str] = mapped_column(String(32), default="ethereum", nullable=False)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_flags: Mapped[list | None] = mapped_column(JSON, default=list)
    hop_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    from_wallet: Mapped["Wallet | None"] = relationship(
        "Wallet", foreign_keys=[from_address_id], back_populates="transactions_from"
    )
    to_wallet: Mapped["Wallet | None"] = relationship(
        "Wallet", foreign_keys=[to_address_id], back_populates="transactions_to"
    )

    __table_args__ = (UniqueConstraint("case_id", "tx_hash", name="uq_tx_case_hash"),)


# ─── Report ───────────────────────────────────────────────────────────────────

class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    generated_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    summary_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="reports")


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")
