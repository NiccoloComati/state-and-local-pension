"""Executor verification: a hand-built Stage-A result carrying the ACTUAL
Phoenix AV tables (pp. 38-39, transcribed source-native) must reproduce the
human workbook exactly through ops.execute(). Run: python pipeline/test_ops_phx.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

SRC_ROWS = ["Under 20", "20-24", "25-29", "30-34", "35-39", "40-44",
            "45-49", "50-54", "55-59", "60-64", "Over 65"]
SRC_COLS = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "Over 30"]

# Exhibit F.3 (p.38): Active Member Counts by Age and Service - as printed
COUNTS = [
    [4,    None, None, None, None, None, None],
    [150,  None, None, None, None, None, None],
    [414,  26,   2,    None, None, None, None],
    [429,  90,   117,  6,    None, None, None],
    [389,  105,  265,  111,  6,    None, None],
    [347,  116,  252,  251,  108,  1,    None],
    [320,  104,  271,  331,  228,  75,   5],
    [240,  90,   229,  285,  257,  170,  41],
    [202,  87,   217,  250,  234,  110,  87],
    [112,  48,   127,  155,  100,  58,   65],
    [32,   10,   59,   49,   42,   28,   34],
]

# Exhibit F.4 (p.39): Active Member Average Salary - as printed ('*' = suppressed)
WAGES = [
    [41626, None,  None,  None,  None,  None,  None],
    [44659, None,  None,  None,  None,  None,  None],
    [50934, 59850, "*",   None,  None,  None,  None],
    [54748, 70411, 65420, 70566, None,  None,  None],
    [56924, 71314, 72895, 75875, 77420, None,  None],
    [60351, 73938, 75698, 79693, 80315, "*",   None],
    [61347, 72990, 72905, 83080, 87018, 93221, 92618],
    [62285, 70283, 72092, 74958, 85475, 89765, 92565],
    [61225, 73067, 68401, 75562, 80684, 83048, 81690],
    [72472, 83369, 71729, 74615, 77256, 88544, 85362],
    # PDF prints 86,309 here; the human workbook has 86,306 (collector typo,
    # found by the pipeline 2026-07-09) - so derived-vs-workbook shows 2
    # "close" cells on this row. That is the workbook being wrong, not us.
    [62261, 88125, 71923, 72105, 77163, 80139, 86309],
]

def table(cells, page, title):
    return {"page": page, "title": title,
            "row_labels": SRC_ROWS, "col_labels": SRC_COLS, "cells": cells}

def row_map(op_merged, weights_table=None):
    m = [{"target": "<25", "sources": ["Under 20", "20-24"],
          "op": op_merged, "weights_table": weights_table}]
    for tgt, src in zip(["29", "34", "39", "44", "49", "54", "59", "64", "70"],
                        SRC_ROWS[2:]):
        m.append({"target": tgt, "sources": [src], "op": "copy", "weights_table": None})
    return m

def col_map(split_op):
    m = []
    for tgt, src in zip(["4", "9", "14", "19", "24", "29"], SRC_COLS[:6]):
        m.append({"target": tgt, "sources": [src], "op": "copy"})
    m.append({"target": "34", "sources": ["Over 30"], "op": split_op})
    m.append({"target": "40", "sources": ["Over 30"], "op": split_op})
    return m

WB = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                  "Data", "Plans", "Cities", "phx_modeldata", "phx_data19_gen.xlsx")

# ---- counts: sum-merge rows, share_even the Over 30 column ----
derived = ops.execute([table(COUNTS, 38, "Exhibit F.3")],
                      row_map("sum"), col_map("share_even"))
truth = harness.load_truth(WB, "Age_Serv_Num")
rep = harness.score(truth, derived)
print("Age_Serv_Num  derived-vs-workbook:")
harness.print_report(rep)
assert rep["accuracy"] == 1.0 and rep["wrong"] == 0 and rep["close"] == 0, "counts FAILED"

# ---- wages: weighted_avg rows (weights = counts table), copy the Over 30 col ----
derived_w = ops.execute([table(WAGES, 39, "Exhibit F.4"), table(COUNTS, 38, "Exhibit F.3")],
                        row_map("weighted_avg", weights_table=1), col_map("copy"))
truth_w = harness.load_truth(WB, "Age_Serv_Wage")
rep_w = harness.score(truth_w, derived_w)
print("\nAge_Serv_Wage  derived-vs-workbook:")
harness.print_report(rep_w)
print(f"\n  spot check <25/0-4: derived={derived_w['cells'][0][0]} (expect 44580.22...)")
assert rep_w["wrong"] == 0 and rep_w["missing_in_cand"] == 0, "wages FAILED"
# the only non-exact cells must be the known workbook typo (86,306 vs PDF 86,309)
assert rep_w["close"] == 2, f"expected exactly the 2 known-typo cells, got {rep_w['close']}"
print("\nEXECUTOR VERIFIED: actual phx source tables + declared ops -> workbook")
