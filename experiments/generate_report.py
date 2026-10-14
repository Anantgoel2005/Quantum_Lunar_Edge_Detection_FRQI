"""Generate a data-driven report from corrected CSVs only."""
import csv
from collections import defaultdict
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "corrected" / "tables"


def generate_report():
    lines = ["# Corrected experiment results", "",
             "NEQR-Gradient is a hybrid NEQR reconstruction followed by a classical forward gradient.",
             "QHED uses four circuits with the stated shots per circuit. Historical outputs are in results/tables.",
             "Trial standard deviations measure sampling variation, not uncertainty over independent source images.", ""]
    for path in sorted(RESULTS_DIR.glob("*.csv")):
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue
        lines += ["## " + path.stem.replace("_", " "), "", f"Rows: {len(rows)}", ""]
        if "f1_exact_mean" in rows[0]:
            groups = defaultdict(list)
            for row in rows:
                groups[(row.get("dataset", "experiment"), row["method"], row.get("size", "all"))].append(float(row["f1_exact_mean"]))
            lines += ["| Dataset | Method | Size | Entries | Mean exact F1 |", "| --- | --- | --- | ---: | ---: |"]
            lines += [f"| {dataset} | {method} | {size} | {len(vals)} | {np.mean(vals):.4f} |" for (dataset, method, size), vals in groups.items()]
        elif "false_positive_pixels_mean" in rows[0]:
            groups = defaultdict(list)
            for row in rows:
                groups[(row["method"], row["size"])].append(float(row["false_positive_pixels_mean"]) / int(row["pixels"]))
            lines += ["| Method | Size | Rim-free patches | Mean false positive pixel fraction |", "| --- | --- | ---: | ---: |"]
            lines += [f"| {method} | {size} | {len(vals)} | {np.mean(vals):.4f} |" for (method, size), vals in groups.items()]
        else:
            fields = list(rows[0])
            lines += ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
            lines += ["| " + " | ".join(row[field] for field in fields) + " |" for row in rows]
        lines += [""]
    destination = PROJECT_ROOT / "report" / "corrected_results_report.md"
    destination.write_text("\n".join(lines), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    generate_report()
