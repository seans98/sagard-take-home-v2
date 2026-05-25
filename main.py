import csv
import os
from dataclasses import asdict, fields as dc_fields

from schema import PortfolioRecord
from extraction import extract_from_pdf
from metrics import compute_derived


def write_csv(records: list, out_path: str):
    fieldnames = [f.name for f in dc_fields(PortfolioRecord)]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(asdict(r))
    print(f"\n  Wrote {len(records)} records → {out_path}")


def main(pdf_dir: str, out_csv: str):
    pdfs = sorted(
        p for p in os.listdir(pdf_dir)
        if p.endswith(".pdf") and p != "Portfolio_Snapshot_Q2_2025.pdf"
    )

    records = []
    for fname in pdfs:
        rec = extract_from_pdf(os.path.join(pdf_dir, fname))
        if rec:
            print(
                f"  ok  {fname:<42} {rec.period}  "
                f"rev={rec.revenue}  arr={rec.arr}  "
                f"gm={rec.gross_margin_pct}%  nrr={rec.nrr_pct}  hc={rec.headcount}"
                + (f"  [{rec.notes}]" if rec.notes else "")
            )
            records.append(rec)

    records = compute_derived(records)
    write_csv(records, out_csv)


if __name__ == "__main__":
    PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
    OUT_CSV = os.path.join(os.path.dirname(__file__), "output.csv")
    main(PDF_DIR, OUT_CSV)
