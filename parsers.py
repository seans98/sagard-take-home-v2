import re
from typing import Optional


# ── Value splitting ───────────────────────────────────────────────────────────
#
# pdfplumber collapses multi-column rows into a single string like:
#   "Annual Recurring Revenue $18.6M $17.1M"
# We scan right-to-left collecting tokens that look like financial values,
# stopping at the first token that isn't a number/unit.

VALUE_TOKEN_RE = re.compile(
    r"""^
    \(?            # optional opening paren  (negative values like ($0.75M))
    [+\-\$]?       # optional sign or dollar sign
    [\d,]+         # integer digits, possibly comma-separated
    \.?\d*         # optional decimal part
    (?:M|k|B|bps|%|x)?  # optional unit suffix
    \)?            # optional closing paren
    $""",
    re.VERBOSE | re.IGNORECASE,
)


def split_key_values(row_str: str, n_values: int = 1) -> tuple:
    """
    Split a merged table row into (key, [val1, val2, ...]).

    Scans right-to-left collecting tokens that match VALUE_TOKEN_RE.
    Stops at the first non-value token.

    Examples:
      'Annual Recurring Revenue $18.6M $17.1M'  →  ('Annual Recurring Revenue', ['$18.6M','$17.1M'])
      'Total Headcount 89'                       →  ('Total Headcount', ['89'])
      'Enterprise Accounts (>$100k ARR) 48 43'  →  ('Enterprise Accounts (>$100k ARR)', ['48','43'])
    """
    tokens = row_str.split()
    collected = []

    for tok in reversed(tokens):
        if VALUE_TOKEN_RE.match(tok):
            collected.insert(0, tok)
        else:
            break

    if len(collected) < n_values:
        return row_str.strip(), []

    n_key_tokens = len(tokens) - len(collected)
    key = " ".join(tokens[:n_key_tokens]).strip()
    return key, collected[-n_values:]


# ── Header / period detection ─────────────────────────────────────────────────

QUARTER_RE = re.compile(r'\b(Q[1-4])\s*(20\d{2})\b', re.IGNORECASE)

MONTH_TO_Q = {
    'jan': 1, 'feb': 1, 'mar': 1,
    'apr': 2, 'may': 2, 'jun': 2,
    'jul': 3, 'aug': 3, 'sep': 3,
    'oct': 4, 'nov': 4, 'dec': 4,
}

HEADER_LABELS = {'metric', 'kpi', 'item', 'platform metric', 'usage metric',
                 'sector', 'pipeline stage', 'stage'}


def parse_period(text: str) -> Optional[str]:
    """Find 'Q2 2025' or 'Quarter ended Jun 30, 2025' in arbitrary text."""
    m = QUARTER_RE.search(text)
    if m:
        return f"{m.group(1).upper()} {m.group(2)}"
    m2 = re.search(
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d+,?\s*(20\d{2})',
        text, re.IGNORECASE
    )
    if m2:
        q = MONTH_TO_Q.get(m2.group(1)[:3].lower())
        return f"Q{q} {m2.group(2)}" if q else None
    return None


def is_header_row(row_str: str) -> bool:
    low = row_str.strip().lower()
    return any(low.startswith(lbl) for lbl in HEADER_LABELS)


# ── Label normalisation ───────────────────────────────────────────────────────
#
# Many PDFs append "(LTM)", "(USD)", "(recognized)" etc. to metric names.
# Stripping these lets a single alias entry cover all variants, e.g.:
#   "NRR (LTM)"              → "NRR"
#   "Total Billings (USD)"   → "Total Billings"

_STRIP_QUALIFIER = re.compile(
    r'\s*\('
    r'(?:ltm|usd|gbp|recognized|gross|net|end of period|qtd|ytd|annualized|platform|lTM)'
    r'\)\s*$',
    re.IGNORECASE,
)


def normalise_label(raw: str) -> str:
    return _STRIP_QUALIFIER.sub('', raw).strip()


# ── Alias map ─────────────────────────────────────────────────────────────────

ALIAS_MAP: dict = {
    "revenue": [
        "recognized revenue", "recognized revenue (usd)",
        "quarterly revenue", "quarterly revenue (recognized)",
        "quarterly recognized revenue",
        "total recognized revenue",
        "gross transaction revenue",
        "platform revenue", "platform revenue (recognized)",
        "net revenue", "net revenue (usd)",
        "total billings", "total billings (usd)",
    ],
    "arr": [
        "annual recurring revenue", "arr", "arr (end of period)",
        "end-of-period arr", "contracted arr",
        "subscription arr (end of period)",
        "contracted annual recurring revenue",
    ],
    "gross_margin_pct": ["gross margin"],
    "nrr_pct": [
        "net dollar retention", "net revenue retention", "nrr", "ndr",
        "net pound retention", "net pound retention – npr", "npr",
    ],
    "logo_churn_pct": [
        "logo churn", "logo churn rate", "annual logo churn",
    ],
    "cash": [
        "cash balance", "cash & equivalents", "cash",
        "cash & restricted cash",
    ],
    "monthly_burn": [
        "monthly net burn", "net burn (monthly)", "quarterly net burn",
        "monthly cash burn",
    ],
    "headcount": ["total headcount", "headcount"],
}

# Reverse lookup: normalised label → canonical field name
_REVERSE: dict = {}
for _canonical, _aliases in ALIAS_MAP.items():
    for _alias in _aliases:
        _REVERSE[normalise_label(_alias).lower()] = _canonical


def map_key(raw_key: str) -> Optional[str]:
    normalised = normalise_label(raw_key).lower().strip()
    return _REVERSE.get(normalised)


# ── Value parsing ─────────────────────────────────────────────────────────────

def parse_numeric(val_str: str) -> Optional[float]:
    """
    Normalise a financial string to a plain float (millions where applicable).

    '$8.4M'    →  8.4
    '($0.75M)' → -0.75   (parentheses = negative)
    '78%'      →  78.0
    '1,420'    →  1420.0
    '$84k'     →  0.084  (k → /1000 to stay in millions)
    '2.3'      →  2.3
    """
    if not val_str:
        return None
    s = val_str.strip()
    negative = s.startswith('(') and s.endswith(')')
    s = s.strip('()').replace('$', '').replace(',', '').replace('+', '').strip()

    unit = ''
    for suffix in ('bps', 'M', 'k', 'K', 'B', '%', 'x'):
        if s.upper().endswith(suffix.upper()):
            unit = suffix.upper()
            s = s[:-len(suffix)].strip()
            break

    try:
        val = float(s)
    except ValueError:
        return None

    if unit == 'K':
        val /= 1000.0   # normalise to millions
    elif unit == 'B':
        val *= 1000.0

    return -val if negative else val


# ── Text regex fallback ───────────────────────────────────────────────────────
#
# Some quarters bury metrics in commentary instead of tables.
# Only runs for fields still missing after table extraction.

TEXT_PATTERNS: dict = {
    # "ended the quarter at 199 employees"  /  "Headcount of 114 is disclosed"
    "headcount": re.compile(
        r'(?:ended\s+(?:the\s+)?(?:quarter|period)\s+(?:at|with)\s+(\d+)\s+employee'
        r'|[Hh]eadcount\s+of\s+(\d+)\b)',
        re.IGNORECASE
    ),
    # "Gross margin came in at 76%"  /  "Gross Margin was 73%"
    "gross_margin_pct": re.compile(
        r'[Gg]ross\s+[Mm]argin\s+(?:came\s+in\s+at|was|of)\s+(\d+(?:\.\d+)?)\s*%',
        re.IGNORECASE
    ),
    # "net dollar retention on a trailing-twelve-month basis reached 119%"
    "nrr_pct": re.compile(
        r'(?:net\s+(?:dollar|revenue|pound)\s+retention|NRR)\s+(?:on\s+a\s+\S+\s+basis\s+)?'
        r'(?:reached|was|of)\s+(\d+(?:\.\d+)?)\s*%',
        re.IGNORECASE
    ),
}


def text_fallback(full_text: str, missing_fields: set) -> dict:
    """Scan narrative text for fields not found in any table."""
    found = {}
    for field_name in missing_fields:
        pattern = TEXT_PATTERNS.get(field_name)
        if not pattern:
            continue
        m = pattern.search(full_text)
        if m:
            raw = next(g for g in m.groups() if g is not None)
            val = parse_numeric(raw)
            if val is not None:
                found[field_name] = val
    return found
