"""Guard: an Age_Serv_Wage extraction whose source_tables[0] is a salary-TOTALS
table (million-dollar cells) with derive!=ratio must be REJECTED by validate(),
so best-of-N/retry declares derive=ratio. This is the 2026-07-27 chi_edu/ff/gen/
pol wage 0.00 root cause (model transcribed totals+counts, notes said
'average=totals/lives', but declared derive=None -> raw totals output).

Run: python pipeline/test_wage_totals_guard.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Age_Serv_Wage"]
assert SPEC.get("max_plausible_value"), "Age_Serv_Wage needs max_plausible_value"

COLS = ["4", "9"]
ROWS = ["<25", "29"]


def _table(cells, title):
    return {"page": 1, "title": title, "row_labels": ROWS, "col_labels": COLS,
            "cells": cells, "printed_row_totals": None, "printed_col_totals": None}


def _result(values_cells, derive):
    # a minimal well-formed extraction: values table at [0], counts at [1]
    return {
        "source_tables": [_table(values_cells, "salary"),
                          _table([[52, 40], [400, 120]], "counts")],
        "row_map": [{"target": r, "sources": [r], "op": "copy", "weights_table": None}
                    for r in ROWS],
        "col_map": [{"target": c, "sources": [c], "op": "copy"} for c in COLS],
        "derive": derive, "transpose": False, "notes": "x",
    }


def _fires(problems):
    return any("salary-TOTALS table" in p for p in problems)


def main():
    # 1) TOTALS table (millions) + derive=None -> guard MUST fire
    totals = [[2_272_208, 1_800_000], [21_000_000, 6_500_000]]
    p = extract.validate(_result(totals, None), SPEC)
    assert _fires(p), f"guard did not fire on a totals table: {p}"
    print("PASS: totals table + derive=None -> rejected (guard fires)")

    # 2) same TOTALS table but derive=ratio -> guard must NOT fire (correct usage)
    ratio = {"op": "ratio", "numerator_table": 0, "denominator_table": 1}
    # ratio mode bans weighted_avg/ratio maps; our copy/sum maps are fine
    p = extract.validate(_result(totals, ratio), SPEC)
    assert not _fires(p), f"guard wrongly fired when derive=ratio: {p}"
    print("PASS: totals table + derive=ratio -> not flagged (correct usage allowed)")

    # 3) a real AVERAGES table (tens of thousands) + derive=None -> must NOT fire
    avgs = [[43_955, 52_800], [58_200, 61_000]]
    p = extract.validate(_result(avgs, None), SPEC)
    assert not _fires(p), f"guard false-positived on real averages: {p}"
    print("PASS: real averages table -> not flagged (no false positive)")

    print("wage-totals guard verified")


if __name__ == "__main__":
    main()
