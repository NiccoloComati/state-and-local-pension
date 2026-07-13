"""Executor verification for Sep_Rate: the ACTUAL phx p.49 termination table
(hand-transcribed, source-native) through the declared maps must reproduce the
human workbook wherever the workbook stays inside the printed data.

Known, intentional residuals (assumption_register.md):
- workbook rows 65 and 70 carry the age-60 rates forward beyond the printed
  table (source ages end at 60); we do not extrapolate -> 22 missing cells.
- both collectors' col '1' = source service year 1 (year 0 dropped): encoded
  in the template col spans ([1,1] etc.), so no residual from that here.
Run: python pipeline/test_ops_phx_seprate.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

# phx p.49 SS4 'Termination rates' - as printed (percent)
SRC_ROWS = ["20", "25", "30", "35", "40", "45", "50", "55", "60"]
SRC_COLS = ["0", "1", "2", "3", "4", "5+"]
CELLS = [
    [17.00, 15.00, 9.00, 8.00, 6.25, 5.50],
    [17.00, 15.00, 9.00, 8.00, 6.25, 5.50],
    [15.00, 11.25, 8.00, 6.75, 5.25, 4.50],
    [15.00,  8.75, 7.00, 5.50, 4.50, 3.50],
    [15.00,  7.50, 6.25, 4.50, 4.00, 2.75],
    [15.00,  6.50, 5.50, 4.50, 4.00, 2.25],
    [15.00,  6.50, 5.50, 4.50, 4.00, 2.00],
    [15.00,  6.50, 5.50, 4.50, 4.00, 2.00],
    [15.00,  6.50, 5.50, 4.50, 4.00, 2.00],
]
SRC_SPANS = {"0": [0, 0], "1": [1, 1], "2": [2, 2], "3": [3, 3],
             "4": [4, 4], "5+": [5, None]}

table = {"page": 49, "title": "Termination rates",
         "row_labels": SRC_ROWS, "col_labels": SRC_COLS, "cells": CELLS,
         "values_unit": "percent"}

spec = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Sep_Rate"]

# rows: printed single ages -> copy; 65/70 have no source (no extrapolation)
row_map = []
for tgt in spec["grid"]["row_labels"]:
    row_map.append({"target": tgt,
                    "sources": [tgt] if tgt in SRC_ROWS else [],
                    "op": "copy", "weights_table": None})
# cols: overlap_weighted with the printed spans (the resolver computes the
# actual source sets from the pooled spans; entries just carry them)
col_map = [{"target": tgt, "sources": list(SRC_SPANS), "op": "overlap_weighted",
            "source_spans": [SRC_SPANS[s] for s in SRC_SPANS]}
           for tgt in spec["grid"]["col_labels"]]

derived = ops.execute([table], row_map, col_map,
                      target_row_spans=spec["target_row_spans"],
                      target_col_spans=spec["target_col_spans"],
                      to_decimal=spec["convert_percent_to_decimal"],
                      zero_impossible_cfg=spec["zero_impossible_cells"])

WB = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                  "Data", "Plans", "Cities", "phx_modeldata", "phx_data19_gen.xlsx")
truth = harness.load_truth(WB, "Sep_Rate")
rep = harness.score(truth, derived, zero_equals_empty=spec["zero_equals_empty"])
print("phx Sep_Rate derived-vs-workbook:")
harness.print_report(rep)

# expected residuals, both recorded in assumption_register.md:
# - 22 missing: workbook rows 65/70 carry the age-60 rates beyond the printed table
# - 1 wrong: age-25 x col '6' - the collector kept 0.055 where her own
#   not-fully-attainable zeroing convention (applied everywhere else) implies 0
assert rep["close"] == 0, "unexplained near-misses"
assert rep["missing_in_cand"] == 22, \
    f"expected exactly the 22 carried-forward cells (rows 65/70), got {rep['missing_in_cand']}"
assert rep["wrong"] == 1 and "age 25 x svc 6" in rep["mismatches"][0], \
    f"expected only the age-25/col-6 collector inconsistency, got {rep['mismatches'][:3]}"
print("\nPASS: printed data reproduced exactly; residuals = the two known workbook"
      "\n      items (rows 65/70 carried forward; the age-25/col-6 inconsistency)")
