# Sagard Challenge

Extracts financial KPIs from portfolio company PDFs and outputs a structured CSV.


## Assumptions 
- All PDF's contain a table with the key KPI's
- AI Assistance was permitted
- CSV File was permissible as a minimum MVP

## Approach

- Use AI Assistance to first parse through all of the PDF's to find the KPI's that all of the PDF's contain
- After the pattern was noticed we  then needed to create a ingestion workflow
- **Ingestion Pipeline:** Table extraction → alias/label normalisation → text regex fallback
- After normalization happens we then map it to a schema which contains the mandatory fields as well as optional fields in case the PDF does not contain certain data
- This schema can be built upon and used in different services if we were to pass this through an API etc.

### File Overview

| File | Purpose |
|------|---------|
| `main.py` | Entry point — discovers PDFs, orchestrates extraction, computes derived metrics, and writes `output.csv` |
| `extraction.py` | PDF parsing logic — uses pdfplumber to extract table rows and full text from each file, then maps them to a `PortfolioRecord` |
| `parsers.py` | Low-level parsing utilities — splits merged table rows into key/value pairs, normalises metric labels, maps aliases to canonical field names, and parses numeric strings (e.g. `$8.4M`, `($0.68M)`, `78%`) |
| `schema.py` | Defines the `PortfolioRecord` dataclass (mandatory + optional fields) and `COMPANY_META` (sector and currency lookup by company name) |
| `metrics.py` | Computes derived metrics after all records are loaded — QoQ/YoY revenue growth, net new ARR, cash runway, burn multiple, ARR per FTE, revenue per FTE |
| `output.csv` | Final output — one row per PDF with all extracted and derived fields |


## Setup

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
pip install pdfplumber
```

## Usage

1. Drop your portfolio PDF files into the `pdfs/` folder.
2. Run:

```bash
python main.py
```

Results are written to `output.csv` in the project root.

## Output

A CSV with One row per PDF with fields: `company`, `sector`, `currency`, `period`, `revenue`, `gross_margin_pct`, `headcount`, `arr`, `nrr_pct`, `logo_churn_pct`, `cash`, `monthly_burn`, plus derived metrics (`revenue_qoq_pct`, `revenue_yoy_pct`, `net_new_arr`, `arr_qoq_pct`, `cash_runway_months`, `burn_multiple`, `arr_per_fte`, `rev_per_fte`).

