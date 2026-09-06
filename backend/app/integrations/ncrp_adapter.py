"""
NCRP Adapter Stub — National Cybercrime Reporting Portal (India)

IMPORTANT: This is a documented interface stub.
No live NCRP API credentials or access are available.
Real integration requires official API access from the Ministry of Home Affairs.

Interface designed to be drop-in replaceable once access is granted.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class NCRPComplaint:
    complaint_id: str
    victim_name: str
    wallet_address: str
    reported_amount_inr: float
    incident_date: str
    status: str


class NCRPAdapter:
    """
    Mock NCRP adapter.
    Replace the methods below with real HTTP calls to the NCRP API
    once production credentials are obtained.
    """

    async def search_complaints_by_wallet(self, wallet_address: str) -> list[NCRPComplaint]:
        """
        Search NCRP for existing complaints mentioning this wallet address.
        In production: POST /api/complaints/search with wallet address filter.
        """
        # MOCK RESPONSE — replace with real API call
        return [
            NCRPComplaint(
                complaint_id="NCRP-DEMO-001",
                victim_name="Rajeev Kumar (Synthetic)",
                wallet_address=wallet_address,
                reported_amount_inr=652500.0,
                incident_date="2024-11-10",
                status="under_investigation",
            )
        ]

    async def file_complaint_reference(self, case_id: str, complaint_data: dict) -> str:
        """
        File a cross-reference to an existing NCRP complaint.
        In production: POST /api/complaints/{id}/references
        """
        return f"NCRP-REF-{case_id[:8].upper()}"
