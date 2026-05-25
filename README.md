# PDF Portfolio Extractor

Extracts financial KPIs from portfolio company PDFs and outputs a structured CSV.

**Pipeline:** Table extraction → alias/label normalisation → text regex fallback

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

One row per PDF with fields: `company`, `sector`, `currency`, `period`, `revenue`, `gross_margin_pct`, `headcount`, `arr`, `nrr_pct`, `logo_churn_pct`, `cash`, `monthly_burn`, plus derived metrics (`revenue_qoq_pct`, `revenue_yoy_pct`, `net_new_arr`, `arr_qoq_pct`, `cash_runway_months`, `burn_multiple`, `arr_per_fte`, `rev_per_fte`).
