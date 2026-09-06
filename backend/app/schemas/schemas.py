"""Pydantic schemas for TRACE-X API.
Uses str for IDs to be compatible with both SQLite (String(36)) and PostgreSQL (UUID).
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = "analyst"


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Case ─────────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    victim_name: Optional[str] = Field(None, max_length=255)
    victim_contact: Optional[str] = Field(None, max_length=255)
    reported_amount_usd: Optional[float] = Field(None, ge=0)
    tags: list[str] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    victim_name: Optional[str] = None
    victim_contact: Optional[str] = None
    reported_amount_usd: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    tags: Optional[list[str]] = None


class CaseOut(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str] = None
    victim_name: Optional[str] = None
    victim_contact: Optional[str] = None
    reported_amount_usd: Optional[float] = None
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    tags: list[str] = []
    wallet_count: int = 0
    transaction_count: int = 0

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseOut]
    total: int
    page: int
    page_size: int


# ─── Wallet ───────────────────────────────────────────────────────────────────

class WalletCreate(BaseModel):
    address: str = Field(..., min_length=10, max_length=255)
    chain: str = Field(default="ethereum", max_length=32)
    wallet_type: str = "suspect"
    label: Optional[str] = Field(None, max_length=255)

    @field_validator("address")
    @classmethod
    def normalize_address(cls, v: str) -> str:
        return v.strip().lower()


class WalletOut(BaseModel):
    id: str
    case_id: str
    address: str
    chain: str
    wallet_type: str
    label: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    transaction_count: int = 0
    total_received_usd: float = 0.0
    total_sent_usd: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    is_seed: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Transaction ──────────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: str
    tx_hash: str
    from_address: str
    to_address: str
    amount_eth: float
    amount_usd: float
    timestamp: datetime
    chain: str
    is_suspicious: bool = False
    risk_flags: list[str] = []
    hop_number: Optional[int] = None
    block_number: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Graph ────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    address: str
    label: Optional[str] = None
    node_type: str  # suspect | victim | intermediary | exchange | unknown
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    transaction_count: int = 0
    total_volume_usd: float = 0.0
    is_seed: bool = False
    chain: str = "ethereum"
    metadata: dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    tx_hash: str
    amount_eth: float
    amount_usd: float
    timestamp: datetime
    is_suspicious: bool = False
    risk_flags: list[str] = []
    hop_number: Optional[int] = None


class GraphResponse(BaseModel):
    case_id: str
    seed_wallet: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    suspicious_paths: list[list[str]] = []
    statistics: dict[str, Any] = {}
    generated_at: datetime


# ─── Risk ─────────────────────────────────────────────────────────────────────

class FeatureContribution(BaseModel):
    feature: str
    value: float
    normalized_value: float
    weight: float
    contribution: float
    description: str
    is_suspicious: bool = False


class RiskEvidence(BaseModel):
    evidence_type: str
    description: str
    severity: str  # low | medium | high | critical
    tx_hashes: list[str] = []


class RiskAnalysisResponse(BaseModel):
    wallet_address: str
    case_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str  # low | medium | high | critical
    feature_contributions: list[FeatureContribution]
    evidence: list[RiskEvidence]
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty_notes: list[str] = []
    analyzed_at: datetime
    transaction_count: int
    total_volume_usd: float


# ─── VASP Attribution ─────────────────────────────────────────────────────────

class VaspEvidence(BaseModel):
    evidence_type: str
    description: str
    confidence_impact: float  # positive = supports, negative = contradicts
    source: str
    verified_at: Optional[datetime] = None


class VaspAttributionResponse(BaseModel):
    wallet_address: str
    case_id: str
    likely_entity: Optional[str] = None
    entity_category: Optional[str] = None  # exchange | mixer | defi | unknown
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence: list[VaspEvidence] = []
    contradicting_evidence: list[VaspEvidence] = []
    alternative_hypotheses: list[dict[str, Any]] = []
    last_verified: Optional[datetime] = None
    source: str = "TRACE-X synthetic label database v1"
    disclaimer: str = (
        "This attribution is a probabilistic hypothesis based on available evidence. "
        "It does not constitute a guaranteed identification and must be corroborated "
        "through independent legal and regulatory channels before any action is taken."
    )
    analyzed_at: datetime


# ─── Report ───────────────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    format: str = Field(..., pattern="^(pdf|json|csv)$")
    include_graph: bool = True
    include_risk_details: bool = True
    include_vasp_attribution: bool = True
    include_evidence: bool = True
    include_recommendations: bool = True


class ReportOut(BaseModel):
    id: str
    case_id: str
    format: str
    file_path: Optional[str] = None
    generated_at: datetime
    download_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── System Health ────────────────────────────────────────────────────────────

class ServiceHealth(BaseModel):
    name: str
    status: str  # healthy | degraded | down
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class SystemHealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: list[ServiceHealth]
    timestamp: datetime
