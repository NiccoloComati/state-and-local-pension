"""Guard: a derive=ratio whose numerator OR denominator table has EVERY
map-referenced cell null must be REJECTED by validate() - such a table was
transcribed as margins-only and yields an empty output grid (total/None). This
is the 2026-07-27 chi_pol Age_Serv_Wage root cause: derive=ratio was declared
correctly, but the salary (numerator) table had only its 'Total' column filled
(all 90 interior age x service cells null), so every average came out None and
the grid scored 0.0. The guard fires ONLY on all-null (filled==0), so a
legitimately sparse plan - which still fills some interior cells - never trips it.

Run: python pipeline/test_ratio_completeness_guard.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Age_Serv_Wage"]

COLS = ["Under 1", "1-4", "5-9", "Total"]
ROWS = ["Under 20", "20 to 24", "25 to 29"]


def _table(cells):
    return {"page": 1, "title": "t", "row_labels": ROWS, "col_labels": COLS,
            "cells": cells, "printed_row_totals": None, "printed_col_totals": None}


def _result(num_cells, den_cells):
    return {
        "source_tables": [_table(num_cells), _table(den_cells)],
        "row_map": [{"target": "<25", "sources": ["Under 20", "20 to 24"],
                     "op": "sum", "weights_table": None},
                    {"target": "29", "sources": ["25 to 29"],
                     "op": "copy", "weights_table": None}],
        "col_map": [{"target": "4", "sources": ["Under 1", "1-4"], "op": "sum"},
                    {"target": "9", "sources": ["5-9"], "op": "copy"}],
        "derive": {"op": "ratio", "numerator_table": 0, "denominator_table": 1},
        "transpose": False, "notes": "x",
    }


# interior null, only the 'Total' column carries a number (the chi_pol shape)
MARGINS_ONLY = [[None, None, None, 9_000_000],
                [None, None, None, 8_000_000],
                [None, None, None, 7_000_000]]
# a full grid: every interior cell populated
FULL_SALARY = [[900_000, 1_800_000, 2_700_000, 5_400_000],
               [880_000, 1_700_000, 2_500_000, 5_080_000],
               [800_000, 1_600_000, 2_400_000, 4_800_000]]
FULL_COUNT = [[20, 40, 60, 120], [22, 38, 50, 110], [18, 32, 48, 98]]


def _fires(problems):
    return any("EVERY ONE is null" in p for p in problems)


def main():
    # 1) numerator transcribed margins-only -> guard MUST fire
    p = extract.validate(_result(MARGINS_ONLY, FULL_COUNT), SPEC)
    assert _fires(p), f"guard did not fire on a margins-only numerator: {p}"
    print("PASS: numerator with only 'Total' filled -> rejected (guard fires)")

    # 2) denominator transcribed margins-only -> guard MUST fire
    p = extract.validate(_result(FULL_SALARY, MARGINS_ONLY), SPEC)
    assert _fires(p), f"guard did not fire on a margins-only denominator: {p}"
    print("PASS: denominator with only 'Total' filled -> rejected (guard fires)")

    # 3) both tables fully transcribed -> must NOT fire
    p = extract.validate(_result(FULL_SALARY, FULL_COUNT), SPEC)
    assert not _fires(p), f"guard wrongly fired on a full ratio: {p}"
    print("PASS: both tables fully populated -> not flagged (no false positive)")

    # 4) sparse-but-legit: one interior cell filled is enough to clear the guard
    sparse = [[None, None, 2_700_000, 2_700_000],
              [None, None, None, 0], [None, None, None, 0]]
    p = extract.validate(_result(sparse, FULL_COUNT), SPEC)
    assert not _fires(p), f"guard false-positived on a sparse-but-real table: {p}"
    print("PASS: sparse table with any interior data -> not flagged")

    print("ratio-completeness guard verified")


if __name__ == "__main__":
    main()
