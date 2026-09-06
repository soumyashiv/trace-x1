# TRACE-X — SIH26183

> **Real-Time Identification of Fraud-Linked Cryptocurrency Exchanges from Victim-Reported Suspect Wallet Addresses through Automated Blockchain Analytics**

[![SIH2026](https://img.shields.io/badge/SIH2026-Problem%2026183-6366f1?style=flat-square)](.)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](.)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square)](.)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square)](.)

---

## ⚠️ Honest Disclaimer

This prototype operates on **100% synthetic demo data**. It does **not**:
- Connect to any live blockchain in demo mode
- Integrate with NCRP or SAHYOG (mock adapters only)
- Guarantee exchange attribution or fund recovery
- Produce legally certified risk determinations

All risk scores and VASP attributions are **probabilistic hypotheses** that require independent forensic corroboration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                     │
│  Login │ Dashboard │ Graph │ Risk │ VASP │ Timeline │ Report │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST / HTTP
┌───────────────────────▼─────────────────────────────────────┐
│                   FastAPI Backend                             │
│  Auth  │  Cases  │  Graph  │  Risk  │  VASP  │  Reports      │
└──┬──┬──┬──────┬──────────────────────────────────────────────┘
   │  │  │      │
   │  │  │   ┌──▼──────────────────────┐
   │  │  │   │  Blockchain Abstraction  │
   │  │  │   │  MockProvider (offline)  │
   │  │  │   │  EVMProvider  (live)     │
   │  │  │   └─────────────────────────┘
   │  │  │
   │  │  └─── Analytics (NetworkX + RiskEngine)
   │  │
   │  └─────── PostgreSQL (SQLAlchemy async)
   │
   └───────── Redis (caching)
```

---

## Quick Start (Docker)

```bash
# 1. Clone
git clone <repo-url>
cd tracex

# 2. Configure
cp .env.example .env
# Edit .env — change passwords if needed. Keep BLOCKCHAIN_PROVIDER=mock for offline demo.

# 3. Start
docker compose up --build

# 4. Access
#   Frontend: http://localhost:3000
#   API docs:  http://localhost:8000/docs
#   Health:    http://localhost:8000/health
```

### Demo Credentials

| Username | Password   | Role    |
|----------|-----------|---------|
| admin    | tracex123 | Admin   |
| analyst  | tracex123 | Analyst |
| viewer   | tracex123 | Viewer  |

---

## Quick Start (Local Dev — No Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Set environment (minimal local config)
set DATABASE_URL=postgresql+asyncpg://tracex:tracexpass@localhost:5432/tracex
set REDIS_URL=redis://localhost:6379/0
set SECRET_KEY=dev-secret-key-at-least-32-chars
set BLOCKCHAIN_PROVIDER=mock
set SEED_DEMO_DATA=true

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# Open http://localhost:3000
```

---

## Demo Walkthrough

1. **Login** — use `analyst / tracex123`
2. **Dashboard** — see the seeded demo case `TXCASE-DEMO-00001`
3. **Click the case** → Investigation Overview
4. **Open Graph** — see the 7-node transaction graph (Victim → Suspect → Burner → Intermediaries → Exchange)
5. Click **"Highlight Path"** — the longest suspicious path is highlighted
6. **Risk Analysis** — view the 11-feature breakdown for the suspect wallet (score ≥ 75 = CRITICAL)
7. **VASP Attribution** — see CryptoExX attribution with 91% confidence + evidence
8. **Timeline** — step through each hop chronologically
9. **Report** — generate PDF/JSON/CSV and download

---

## Core Workflow

```
Investigator → Create Case → Enter Wallet
                                  ↓
                        MockBlockchainProvider (offline)
                        or EVMBlockchainProvider (live)
                                  ↓
                         GraphEngine (NetworkX)
                         ├── Build directed graph
                         ├── Detect suspicious paths
                         └── Extract 14 graph features
                                  ↓
                         RiskEngine (11 weighted signals)
                         ├── risk_score (0-100)
                         ├── risk_level (low/medium/high/critical)
                         ├── feature_contributions (each signal)
                         ├── evidence (human-readable)
                         └── confidence + uncertainty_notes
                                  ↓
                         VaspService (evidence-backed attribution)
                         ├── likely_entity
                         ├── confidence
                         ├── supporting_evidence[]
                         └── contradicting_evidence[]
                                  ↓
                         ReportService → PDF / JSON / CSV
```

---

## Risk Engine Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| known_risk_label_count | 18% | Labels from risk database |
| suspicious_edge_count | 12% | Flagged transactions |
| burstiness | 10% | Transaction timing irregularity |
| transfer_velocity | 10% | USD/hour movement rate |
| tx_frequency | 9% | Transactions per hour |
| hop_depth | 8% | Distance from seed wallet |
| out_degree (fan-out) | 8% | Distinct outbound counterparties |
| total_volume | 7% | Total USD moved |
| value_concentration | 7% | HHI concentration index |
| in_degree (fan-in) | 6% | Distinct inbound counterparties |
| tx_count | 6% | Total transaction count |
| fan_in_out_ratio | 6% | Aggregation/dispersal indicator |

Every feature contribution is individually reported in the API response.

---

## API Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/cases` | List investigations |
| POST | `/api/v1/cases` | Create investigation |
| GET | `/api/v1/cases/{id}` | Case details |
| POST | `/api/v1/cases/{id}/wallets` | Add wallet |
| POST | `/api/v1/cases/{id}/graph/{addr}` | Build transaction graph |
| POST | `/api/v1/cases/{id}/risk/{addr}` | Run risk analysis |
| POST | `/api/v1/cases/{id}/vasp/{addr}` | Run VASP attribution |
| POST | `/api/v1/cases/{id}/reports` | Generate report |
| GET | `/api/v1/cases/{id}/reports/{rid}/download` | Download report |
| GET | `/health` | System health |
| GET | `/docs` | Swagger UI |

---

## Database Schema

```
users           — investigator accounts (JWT auth, role-based)
cases           — investigation records (case number, victim, status)
wallets         — traced wallet addresses (type, risk score, VASP attribution)
transactions    — individual blockchain transactions (from, to, amount, flags)
reports         — generated reports (format, file path, metadata)
audit_logs      — immutable action log (who did what, when, from where)
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v

# Expected: 35+ tests covering:
#   - Risk engine (11 tests)
#   - Graph engine (13 tests)
#   - Mock blockchain provider (11 tests)
```

---

## Integration Interfaces

The following interfaces are documented but use mock connectors:

- **NCRP** — National Cybercrime Reporting Portal (adapter stub: `blockchain/base.py`)
- **SAHYOG** — LEA coordination portal (adapter documented in architecture notes)
- **Etherscan / Alchemy** — tx history indexer (placeholder in `evm_provider.py`)

---

## Project Structure

```
tracex/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, startup, routing
│   │   ├── config.py             # All settings via env vars
│   │   ├── database.py           # Async SQLAlchemy
│   │   ├── models/               # ORM models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── blockchain/           # Provider abstraction
│   │   │   ├── base.py           # BlockchainProvider ABC
│   │   │   ├── mock_provider.py  # Offline deterministic demo
│   │   │   └── evm_provider.py   # Live Web3.py adapter
│   │   ├── analytics/
│   │   │   ├── graph_engine.py   # NetworkX graph construction
│   │   │   └── risk_engine.py    # Transparent risk scoring
│   │   ├── services/             # Business logic
│   │   └── routers/              # FastAPI route handlers
│   ├── seed/demo_data.json       # Deterministic demo dataset
│   └── tests/                    # pytest test suite
├── frontend/
│   └── src/
│       ├── app/                  # Next.js App Router pages
│       ├── components/           # Reusable UI components
│       ├── lib/api.ts            # Typed API client
│       └── types/index.ts        # TypeScript type definitions
├── docker-compose.yml
└── .env.example
```

---

## Security Controls

| Control | Implementation |
|---------|----------------|
| Authentication | JWT HS256, 8h expiry, httpOnly cookie |
| Authorization | Role model: ADMIN / ANALYST / VIEWER |
| Input validation | Pydantic on all inputs |
| Rate limiting | slowapi (60 req/min default) |
| Audit logging | All actions persisted to `audit_logs` |
| Secrets | All via environment variables |
| CORS | Configurable origin whitelist |
| Privacy | Addresses truncated in logs |

---

## Limitations

- Full EVM tx history requires an indexer (Etherscan/Alchemy API)
- Bitcoin/Solana not implemented — Ethereum/EVM only
- Mixers, bridges, and privacy coins significantly limit traceability (disclosed to user)
- VASP label database is synthetic — not a live Chainalysis/Elliptic integration
- No real-time streaming — polling-based refresh

---

## Future Roadmap

- [ ] Live Etherscan/Alchemy tx history adapter
- [ ] Bitcoin (UTXO model) graph engine
- [ ] Real NCRP complaint cross-reference API
- [ ] ML-based cluster classification (XGBoost)
- [ ] Multi-chain graph (ETH + BSC + Polygon in one view)
- [ ] Mixer/bridge detection heuristics
- [ ] Role-based case assignment workflow
- [ ] WebSocket real-time graph updates
- [ ] STIX/TAXII export for threat intelligence sharing

---

*TRACE-X — Built for SIH2026, Problem Statement 26183 · Synthetic demo only*
