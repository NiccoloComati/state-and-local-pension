"""Guard: a source table with DUPLICATE row/col labels must be REJECTED by
validate(), because label-based maps resolve a repeated label to the LAST
occurrence silently. This is the 2026-07-27 mil Retirement root cause: the
two-panel table transcribed columns ['Male','Female','Total','Male','Female',
'Total'] (count panel + monthly-$ panel), so `Number <- 'Total'` grabbed the
$ total (~4.9M) and `AverageBenefit=ratio('Total','Total')`=1 x12=12.

Run: python pipeline/test_dup_label_guard.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Retirement"]


def _result(col_labels):
    return {
        "source_tables": [{
            "page": 80, "title": "Retired Members", "row_labels": ["59 & U", "60-64"],
            "col_labels": col_labels,
            "cells": [[101, 142, 243, 289494, 334937, 624431],
                      [80, 90, 170, 200000, 250000, 450000]],
            "printed_row_totals": None, "printed_col_totals": None}],
        "row_map": [{"target": "50-54", "sources": [], "op": "copy", "weights_table": None}],
        "col_map": [{"target": "Number", "sources": ["Total Count"], "op": "copy"},
                    {"target": "AverageBenefit",
                     "sources": ["Total Monthly Benefit", "Total Count"],
                     "op": "ratio", "annualize_monthly": True}],
        "derive": None, "transpose": False, "notes": "x",
    }


def _fires(problems):
    return any("DUPLICATE labels" in p for p in problems)


def main():
    # the mil failure: 'Total' (and Male/Female) repeated across the two panels
    dup = ["Male", "Female", "Total", "Male", "Female", "Total"]
    assert _fires(extract.validate(_result(dup), SPEC)), "guard did not fire on duplicate cols"
    print("PASS: duplicate col labels -> rejected (guard fires)")

    # disambiguated: distinct labels for the count panel vs the $ panel
    distinct = ["Male Count", "Female Count", "Total Count",
                "Male $", "Female $", "Total Monthly Benefit"]
    assert not _fires(extract.validate(_result(distinct), SPEC)), \
        "guard wrongly fired on distinct labels"
    print("PASS: distinct labels -> not flagged (correct transcription allowed)")

    print("duplicate-label guard verified")


if __name__ == "__main__":
    main()
