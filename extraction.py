import os
from typing import Optional

import pdfplumber

from schema import PortfolioRecord, company_meta
from parsers import (
    QUARTER_RE,
    parse_period, is_header_row,
    split_key_values, map_key,
    parse_numeric, text_fallback,
)


def extract_from_pdf(path: str) -> Optional[PortfolioRecord]:
    co, sector, currency = company_meta(path)
    raw: dict = {}
    period: Optional[str] = None
    full_text_pages = []
    notes_flags = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            full_text_pages.append(page_text)

            if not period:
                period = parse_period(page_text)

            for table in page.extract_tables():
                if not table:
                    continue

                # Detect how many value columns from the header row
                header_str = table[0][0] if table[0] else ""
                n_vals = max(1, len(QUARTER_RE.findall(header_str))) if is_header_row(header_str) else 1

                for row in table:
                    row_str = row[0] if row else ""
                    if not row_str or is_header_row(row_str):
                        continue

                    key, vals = split_key_values(row_str, n_vals)
                    if not vals:
                        continue

                    canonical = map_key(key)
                    if canonical is None:
                        continue

                    num = parse_numeric(vals[0])  # vals[0] = latest period
                    if num is not None and canonical not in raw:
                        raw[canonical] = num

    # Text fallback for fields still missing after table scan
    full_text = "\n".join(full_text_pages)
    still_missing = {"headcount", "gross_margin_pct", "nrr_pct"} - raw.keys()
    for k, v in text_fallback(full_text, still_missing).items():
        raw[k] = v
        notes_flags.append(f"{k} sourced from narrative text")

    # Company-specific adjustments
    if co == "ClearPay" and "cash" in raw:
        # Table value includes ~$6.2M restricted client float (state money-transmitter regs)
        notes_flags.append("cash excluded: includes $6.2M restricted client float")
        del raw["cash"]

    if co == "ConstructIQ" and "monthly_burn" in raw:
        # Label is "Quarterly Net Burn" — convert to monthly
        raw["monthly_burn"] = round(raw["monthly_burn"] / 3, 4)
        notes_flags.append("monthly_burn = quarterly net burn ÷ 3")

    if co == "PeopleFlow" and period == "Q1 2025" and raw.get("revenue") == 4.7:
        # Revenue restated 4.7 → 4.6 per Q2 2025 footnote
        raw["revenue"] = 4.6
        notes_flags.append("revenue restated 4.7→4.6 per Q2 2025 footnote")

    try:
        rec = PortfolioRecord(
            company=co,
            sector=sector,
            currency=currency,
            period=period or "UNKNOWN",
            revenue=raw["revenue"],
            gross_margin_pct=raw["gross_margin_pct"],
            headcount=int(raw["headcount"]),
            arr=raw.get("arr"),
            nrr_pct=raw.get("nrr_pct"),
            logo_churn_pct=raw.get("logo_churn_pct"),
            cash=raw.get("cash"),
            monthly_burn=abs(raw["monthly_burn"]) if "monthly_burn" in raw else None,
            source_file=os.path.basename(path),
            notes="; ".join(notes_flags),
        )
    except KeyError as e:
        print(f"  [SKIP] {os.path.basename(path)} — missing mandatory field: {e}")
        return None

    return rec
