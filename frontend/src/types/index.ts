// ── Auth ──────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ── Cases ─────────────────────────────────────────────────────────────────────
export type CaseStatus = "open" | "in_progress" | "closed" | "archived";

export interface Case {
  id: string;
  case_number: string;
  title: string;
  description: string | null;
  victim_name: string | null;
  victim_contact: string | null;
  reported_amount_usd: number | null;
  status: CaseStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  tags: string[];
  wallet_count: number;
  transaction_count: number;
}

export interface CaseCreate {
  title: string;
  description?: string;
  victim_name?: string;
  victim_contact?: string;
  reported_amount_usd?: number;
  tags?: string[];
}

export interface CaseListResponse {
  items: Case[];
  total: number;
  page: number;
  page_size: number;
}

// ── Wallets ───────────────────────────────────────────────────────────────────
export type WalletType = "suspect" | "victim" | "intermediary" | "exchange" | "unknown";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface Wallet {
  id: string;
  case_id: string;
  address: string;
  chain: string;
  wallet_type: WalletType;
  label: string | null;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  transaction_count: number;
  total_received_usd: number;
  total_sent_usd: number;
  first_seen: string | null;
  last_seen: string | null;
  is_seed: boolean;
  created_at: string;
}

// ── Graph ─────────────────────────────────────────────────────────────────────
export interface GraphNode {
  id: string;
  address: string;
  label: string | null;
  node_type: WalletType;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  transaction_count: number;
  total_volume_usd: number;
  is_seed: boolean;
  chain: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  tx_hash: string;
  amount_eth: number;
  amount_usd: number;
  timestamp: string;
  is_suspicious: boolean;
  risk_flags: string[];
  hop_number: number | null;
}

export interface GraphResponse {
  case_id: string;
  seed_wallet: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  suspicious_paths: string[][];
  statistics: {
    node_count: number;
    edge_count: number;
    max_fan_out: number;
    max_fan_in: number;
    total_volume_usd: number;
    suspicious_edge_count: number;
    first_transaction: string | null;
    last_transaction: string | null;
    duration_hours: number;
    is_dag: boolean;
    seed_betweenness_centrality: number;
  };
  generated_at: string;
}

// ── Risk ──────────────────────────────────────────────────────────────────────
export interface FeatureContribution {
  feature: string;
  value: number;
  normalized_value: number;
  weight: number;
  contribution: number;
  description: string;
  is_suspicious: boolean;
}

export interface RiskEvidence {
  evidence_type: string;
  description: string;
  severity: RiskLevel;
  tx_hashes: string[];
}

export interface RiskAnalysis {
  wallet_address: string;
  case_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  feature_contributions: FeatureContribution[];
  evidence: RiskEvidence[];
  confidence: number;
  uncertainty_notes: string[];
  analyzed_at: string;
  transaction_count: number;
  total_volume_usd: number;
}

// ── VASP ──────────────────────────────────────────────────────────────────────
export interface VaspEvidence {
  evidence_type: string;
  description: string;
  confidence_impact: number;
  source: string;
  verified_at: string | null;
}

export interface VaspAttribution {
  wallet_address: string;
  case_id: string;
  likely_entity: string | null;
  entity_category: string | null;
  confidence: number;
  supporting_evidence: VaspEvidence[];
  contradicting_evidence: VaspEvidence[];
  alternative_hypotheses: Array<{ entity: string; confidence: number; notes: string }>;
  last_verified: string | null;
  source: string;
  disclaimer: string;
  analyzed_at: string;
}

// ── Reports ───────────────────────────────────────────────────────────────────
export type ReportFormat = "pdf" | "json" | "csv";

export interface Report {
  id: string;
  case_id: string;
  format: ReportFormat;
  file_path: string | null;
  generated_at: string;
  download_url: string | null;
}

// ── System Health ─────────────────────────────────────────────────────────────
export interface ServiceHealth {
  name: string;
  status: "healthy" | "degraded" | "down";
  latency_ms: number | null;
  message: string | null;
}

export interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  services: ServiceHealth[];
  timestamp: string;
}

// ── Transactions ──────────────────────────────────────────────────────────────
export interface Transaction {
  id: string;
  tx_hash: string;
  from_address: string;
  to_address: string;
  amount_eth: number;
  amount_usd: number;
  timestamp: string;
  chain: string;
  is_suspicious: boolean;
  risk_flags: string[];
  hop_number: number | null;
  block_number: number | null;
}
