"""Executor verification for Retirement (retdist): the ACTUAL phx Exhibit F.6
(p.41, hand-transcribed, source-native) through the declared maps must
reproduce the human workbook's Retirement sheet exactly.

The recipe recovered from the truth (all products integer-exact):
- Number      = F.6's SERVICE RETIREE counts (disabled/beneficiaries excluded,
                same population convention as the Avg_Mort weights);
- AverageBenefit = printed TOTAL annual dollars / count -> col op 'ratio'
                (49628.107142857145 x 168 = exactly $8,337,522);
- '<55'       -> template '50-54' (clip, as with Avg_Mort weight bins);
- '90 & Up'   -> rows 90-94/95-99/100 & over via row 'share_even': counts and
                dollars each split /3, so the ratio column reproduces the
                bucket average on every split row (the mil collector's own
                note: "split the age buckets evenly when needed").
Run: python pipeline/test_ops_phx_retdist.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

# phx p.41 Exhibit F.6 'Summary of Members in Pay Status' - as printed
COLS = ["Service Retirees - Number of Members",
        "Service Retirees - Annual Benefit",
        "Disabled Retirees - Number of Members",
        "Disabled Retirees - Annual Benefit",
        "Beneficiaries/QDROs - Number of Members",
        "Beneficiaries/QDROs - Annual Benefit"]
ROWS = ["<55", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84",
        "85-89", "90 & Up"]
CELLS = [
    [168,   8337522, 39,  739093, 73,  1027035],
    [594,  27975555, 39,  675211, 44,  1012484],
    [1178, 46738047, 53,  806213, 58,  1556275],
    [1499, 51740803, 53,  895837, 122, 2576634],
    [1193, 38560397, 24,  330842, 134, 3254087],
    [689,  20062055, 14,  179002, 148, 3534062],
    [390,  10139844, 15,  230576, 139, 2817916],
    [186,   4771025, 7,    85018, 141, 2532783],
    [116,   2381925, 1,    21434, 78,  1359130],
]
table = {"page": 41, "title": "Exhibit F.6 Summary of Members in Pay Status",
         "row_labels": ROWS, "col_labels": COLS, "cells": CELLS}

spec = json.load(open(os.path.join(HERE, "targets.json"),
                      encoding="utf-8"))["Retirement"]

SRC_FOR = {"50-54": "<55", "55-59": "55-59", "60-64": "60-64",
           "65-69": "65-69", "70-74": "70-74", "75-79": "75-79",
           "80-84": "80-84", "85-89": "85-89"}
row_map = []
for tgt in spec["grid"]["row_labels"]:
    if tgt in SRC_FOR:
        row_map.append({"target": tgt, "sources": [SRC_FOR[tgt]],
                        "op": "copy", "weights_table": None})
    else:   # 90-94 / 95-99 / 100 & over share the printed '90 & Up' bucket
        row_map.append({"target": tgt, "sources": ["90 & Up"],
                        "op": "share_even", "weights_table": None})
col_map = [
    {"target": "Number",
     "sources": ["Service Retirees - Number of Members"], "op": "copy"},
    {"target": "AverageBenefit",
     "sources": ["Service Retirees - Annual Benefit",
                 "Service Retirees - Number of Members"], "op": "ratio"},
]

derived = ops.execute([table], row_map, col_map)

WB = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                  "Data", "Plans", "Cities", "phx_modeldata", "phx_data19_gen.xlsx")
truth = harness.load_truth(WB, "Retirement")
rep = harness.score(truth, derived, zero_equals_empty=spec["zero_equals_empty"])
print("phx Retirement derived-vs-workbook:")
harness.print_report(rep)

assert rep["exact"] + rep["close"] == 22 and rep["wrong"] == 0, rep
assert rep["missing_in_cand"] == rep["extra_in_cand"] == 0, rep
# spot-check the split rows: count 116/3, average = the bucket's own average
assert abs(derived["cells"][9][0] - 116 / 3) < 1e-12
assert abs(derived["cells"][10][1] - 2381925 / 116) < 1e-9
print("\nPASS: F.6 service-retiree columns + share_even rows + ratio column"
      "\n      reproduce the phx Retirement sheet (counts, averages, 90+ split)")
