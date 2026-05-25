from typing import Optional


PERIOD_ORDER = ["Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025"]

_YOY_MAP = {
    "Q1 2025": "Q1 2024", "Q2 2025": "Q2 2024",
    "Q3 2025": "Q3 2024", "Q4 2025": "Q4 2024",
}


def _prior(p: str) -> Optional[str]:
    i = PERIOD_ORDER.index(p) if p in PERIOD_ORDER else -1
    return PERIOD_ORDER[i - 1] if i > 0 else None


def _pct(curr, prev) -> Optional[float]:
    if None in (curr, prev) or prev == 0:
        return None
    return round((curr - prev) / abs(prev) * 100, 1)


def compute_derived(records: list) -> list:
    lkp = {(r.company, r.period): r for r in records}
    for r in records:
        prev   = lkp.get((r.company, _prior(r.period) or ""))
        prev_y = lkp.get((r.company, _YOY_MAP.get(r.period, "")))

        r.revenue_qoq_pct = _pct(r.revenue, prev.revenue if prev else None)
        r.revenue_yoy_pct = _pct(r.revenue, prev_y.revenue if prev_y else None)

        if r.arr and prev and prev.arr:
            r.net_new_arr = round(r.arr - prev.arr, 2)
            r.arr_qoq_pct = _pct(r.arr, prev.arr)

        if r.cash and r.monthly_burn and r.monthly_burn > 0:
            r.cash_runway_months = round(r.cash / r.monthly_burn, 1)

        if r.monthly_burn and r.net_new_arr and r.net_new_arr > 0:
            r.burn_multiple = round((r.monthly_burn * 3) / r.net_new_arr, 2)

        if r.arr and r.headcount:
            r.arr_per_fte = round(r.arr / r.headcount * 1000, 1)

        if r.revenue and r.headcount:
            r.rev_per_fte = round(r.revenue / r.headcount * 1000, 1)

    return records
