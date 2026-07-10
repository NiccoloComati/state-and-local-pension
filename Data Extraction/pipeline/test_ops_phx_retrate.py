"""Executor verification for the rung-2 ops: transpose + overlap_weighted +
percent conversion, on the ACTUAL Phoenix AV retirement-rate table (p.50,
section B.5), hand-transcribed source-native.

Two undocumented human judgment calls live in this sheet (found 2026-07-10 by
diffing the verified source against the workbook; phx_log.txt only says
"broken out and averaged if needed"):
  J1 - the printed age-70 row (100% everywhere) is IGNORED: the workbook's
       col 70 carries the 66-69 rates instead.
  J2 - service bins 31+ all copy the '>31' column (consistent with reading
       '25-31' as [25,30] / '>31' as [31, inf)), not the literal-label
       blend ('25-31'=[25,31], '>31'=[32, inf) would 50/50-blend row 31-32).

This test runs BOTH span readings:
  literal spans  -> verifies the blend MECHANICS exactly (12-19 row: 3/8, 5/8
                    weights -> 0.140625 at 54, 0.178125 at 60, 0.22 at 63...)
                    and that ALL mismatches vs the workbook are confined to
                    row '31-32' + col '70' (the two judgment calls).
  human spans    -> reproduces the workbook everywhere except col 70 (J1).

Run: python pipeline/test_ops_phx_retrate.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

WORKBOOK = os.path.join(os.path.dirname(HERE), "..", "Data", "Plans", "Cities",
                        "phx_modeldata", "phx_data19_gen.xlsx")

# p.50 B.5 "Probability of Retirement" - transcribed source-native (percent)
SRC_ROWS = ["50-51", "52", "53", "54", "55-58", "59", "60", "61", "62",
            "63", "64", "65", "66-69", "70"]
SRC_COLS = ["<15", "15-24", "25-31", ">31"]
RATES = [
    [0.00,   0.00,  40.00, 40.00],
    [0.00,   0.00,  35.00, 40.00],
    [0.00,   0.00,  32.50, 32.50],
    [0.00,  22.50,  27.50, 32.50],
    [0.00,  22.50,  22.50, 32.50],
    [0.00,  22.50,  22.50, 42.50],
    [10.00, 22.50,  27.50, 42.50],
    [17.00, 22.50,  32.50, 42.50],
    [17.00, 30.00,  32.50, 42.50],
    [17.00, 25.00,  32.50, 42.50],
    [17.00, 25.00,  37.50, 42.50],
    [30.00, 32.50,  40.00, 42.50],
    [25.00, 32.50,  40.00, 42.50],
    [100.00, 100.00, 100.00, 100.00],
]

TABLE = {"page": 50, "title": "5. Retirement rates. Probability of Retirement",
         "row_labels": SRC_ROWS, "col_labels": SRC_COLS, "cells": RATES,
         "printed_row_totals": None, "printed_col_totals": None,
         "values_unit": "percent"}

# source age-bin spans (printed labels are unambiguous here)
AGE_SPANS = {"50-51": [50, 51], "52": [52, 52], "53": [53, 53], "54": [54, 54],
             "55-58": [55, 58], "59": [59, 59], "60": [60, 60], "61": [61, 61],
             "62": [62, 62], "63": [63, 63], "64": [64, 64], "65": [65, 65],
             "66-69": [66, 69], "70": [70, None]}


def build_maps(svc_spans):
    """row_map (service targets <- source service cols, post-transpose) and
    col_map (age targets <- source age rows, post-transpose)."""
    spec = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Ret_Rate"]
    row_map = []
    for tgt, t_span in spec["target_row_spans"].items():
        srcs = [s for s in SRC_COLS
                if ops._overlap_years(t_span, svc_spans[s]) > 0]
        row_map.append({"target": tgt, "sources": srcs, "op": "overlap_weighted",
                        "weights_table": None,
                        "source_spans": [svc_spans[s] for s in srcs]})
    col_map = []
    for tgt, t_span in spec["target_col_spans"].items():
        srcs = [s for s in SRC_ROWS
                if ops._overlap_years(t_span, AGE_SPANS[s]) > 0]
        col_map.append({"target": tgt, "sources": srcs, "op": "overlap_weighted",
                        "source_spans": [AGE_SPANS[s] for s in srcs]})
    return spec, row_map, col_map


def run(name, svc_spans):
    spec, row_map, col_map = build_maps(svc_spans)
    derived = ops.execute([TABLE], row_map, col_map, transpose=True,
                          target_row_spans=spec["target_row_spans"],
                          target_col_spans=spec["target_col_spans"],
                          to_decimal=True)
    truth = harness.load_truth(WORKBOOK, "Ret_Rate")
    report = harness.score(truth, derived)
    print(f"--- {name} ---")
    harness.print_report(report)
    return derived, report


def cell(derived, svc, age):
    return derived["cells"][derived["row_labels"].index(svc)][derived["col_labels"].index(age)]


def main():
    # 1) literal reading of the printed labels
    literal = dict(zip(SRC_COLS, [[None, 14], [15, 24], [25, 31], [32, None]]))
    derived, report = run("literal spans ('25-31'=[25,31], '>31'=[32,inf))", literal)

    # blend mechanics, verified to the decimal (ml_extraction_handoff rung 2)
    assert cell(derived, "12-19", "54") == 0.140625, cell(derived, "12-19", "54")
    assert cell(derived, "12-19", "60") == 0.178125
    assert cell(derived, "12-19", "61") == 0.204375
    assert cell(derived, "12-19", "62") == 0.25125
    assert abs(cell(derived, "12-19", "63") - 0.22) < 1e-12
    assert cell(derived, "12-19", "65") == 0.315625
    assert cell(derived, "12-19", "66") == 0.296875
    assert cell(derived, "5-11", "60") == 0.10
    assert cell(derived, "20-24", "62") == 0.30
    assert cell(derived, "25-29", "52") == 0.35
    # all mismatches vs the workbook must be the two judgment calls
    for m in report["mismatches"]:
        assert "[age 31-32 x" in m or "x svc 70]" in m, f"unexpected mismatch: {m}"
    print("mechanics verified: blends exact; mismatches confined to row 31-32 + col 70 (J1/J2)")
    print()

    # 2) the human collector's implied reading
    human = dict(zip(SRC_COLS, [[None, 14], [15, 24], [25, 30], [31, None]]))
    derived, report = run("human-implied spans ('25-31'=[25,30], '>31'=[31,inf))", human)
    for m in report["mismatches"]:
        assert "x svc 70]" in m, f"unexpected mismatch: {m}"
    n70 = sum(1 for m in report["mismatches"] if "x svc 70]" in m)
    assert report["wrong"] == n70 == 9, report["wrong"]
    print("human-implied spans reproduce the workbook everywhere except col 70 (J1: the")
    print("workbook ignores the AV's printed 100%-at-70 row and carries the 66-69 rates)")
    print()
    print("PASS: transpose + overlap_weighted + percent conversion verified on phx B.5")


if __name__ == "__main__":
    main()
