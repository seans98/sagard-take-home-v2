import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PortfolioRecord:
    # Identity
    company: str
    sector: str
    currency: str
    period: str
    # Core financials (mandatory)
    revenue: float
    gross_margin_pct: float
    headcount: int
    # SaaS metrics (optional)
    arr: Optional[float] = None
    nrr_pct: Optional[float] = None
    logo_churn_pct: Optional[float] = None
    # Balance sheet (optional)
    cash: Optional[float] = None
    monthly_burn: Optional[float] = None
    # Derived (computed after all records loaded)
    revenue_qoq_pct: Optional[float] = None
    revenue_yoy_pct: Optional[float] = None
    net_new_arr: Optional[float] = None
    arr_qoq_pct: Optional[float] = None
    cash_runway_months: Optional[float] = None
    burn_multiple: Optional[float] = None
    arr_per_fte: Optional[float] = None
    rev_per_fte: Optional[float] = None
    # Provenance
    source_file: str = ""
    notes: str = ""

    MANDATORY = {"company", "sector", "currency", "period",
                 "revenue", "gross_margin_pct", "headcount"}


COMPANY_META = {
    "NovaCloud":   ("NovaCloud Analytics",     "B2B SaaS – Observability",      "USD"),
    "MediSight":   ("MediSight",               "Healthcare SaaS",               "USD"),
    "LendBridge":  ("LendBridge",              "Specialty Finance / Fintech",   "USD"),
    "PeopleFlow":  ("PeopleFlow",              "HR SaaS (Vertical)",            "GBP"),
    "FleetLink":   ("FleetLink / ApexFreight", "Digital Freight Marketplace",   "USD"),
    "ApexFreight": ("FleetLink / ApexFreight", "Digital Freight Marketplace",   "USD"),
    "TalentVault": ("TalentVault",             "Talent Intelligence SaaS",      "USD"),
    "CarbonTrack": ("CarbonTrack",             "ESG / Carbon Accounting SaaS",  "USD"),
    "ClearPay":    ("ClearPay",                "B2B Payments / Reconciliation", "USD"),
    "ConstructIQ": ("ConstructIQ",             "Construction SaaS",             "USD"),
}


def company_meta(fname: str) -> tuple:
    base = os.path.basename(fname)
    for prefix, meta in COMPANY_META.items():
        if base.startswith(prefix):
            return meta
    return ("Unknown", "Unknown", "USD")
