"""Executor verification for the rung-3 op group_weighted (population-weighted
group blend) on the ACTUAL San Diego tables, hand-transcribed source-native:
  - Table B-2  (p.56): termination rates by service year x {General, Safety}
  - Table A-9  (p.45): General active counts, age bins x service bins
  - Table A-11 (p.46): Safety active counts, same shape

The sd collector's Sep_Rate sheet was reverse-engineered 2026-07-14: she
blended the two group rate columns with JOINT (age-bin x service-bin)
headcounts from A-9/A-11 - e.g. a(25, svc 1-4) = 27/(27+194) = 0.1222,
a(30, svc 10-14) = 38/(38+85) = 0.3089, all confirmed exactly - and mapped
each template service column from a SINGLE source year (col 6 <- year 6),
not the template's [5,6] average (register entry 4 evidence).

group_weighted reproduces this: weight = the group's headcount at the bin
containing the output cell (target age span x source-column span), with
partial bins attributed proportionally (common factors cancel in the blend).

Known non-reproduced residuals (asserted, adjudicated):
  - cols 30/40: the value comes from source year '20+' whose span [20, inf)
    covers several count buckets; the collector instead used only the single
    bucket containing the year 30/40 - a convention difference within
    register entry 4, not an arithmetic error.
  - the collector's own fill conventions beyond the printed data.

Run: python pipeline/test_ops_sd_seprate_blend.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

WORKBOOK = os.path.join(os.path.dirname(HERE), "..", "Data", "Plans", "Cities",
                        "sd_modeldata", "sd_data19_gen.xlsx")

# ---- Table B-2 (p.56), as printed: service rows x [General, Safety], percent
SVC = [str(y) for y in range(20)] + ["20+"]
B2 = {
    "page": 56, "title": "Table B-2 Rates of Termination",
    "row_labels": SVC, "col_labels": ["General", "Safety"],
    "row_spans": [[y, y] for y in range(20)] + [[20, None]],
    "cells": [
        [10.00, 10.00], [9.00, 8.00], [8.50, 6.00], [7.50, 5.00], [6.50, 4.00],
        [5.50, 3.00], [4.50, 2.75], [4.25, 2.50], [4.00, 2.25], [3.25, 2.00],
        [2.75, 1.80], [2.75, 1.80], [2.75, 1.80], [2.75, 1.80], [2.75, 1.80],
        [2.75, 1.60], [2.75, 1.60], [2.75, 1.60], [2.75, 1.60], [2.75, 1.60],
        [2.75, 1.50],
    ],
    "printed_row_totals": None, "printed_col_totals": None,
    "values_unit": "percent",
}

AGE_ROWS = ["Under 25", "25 to 29", "30 to 34", "35 to 39", "40 to 44",
            "45 to 49", "50 to 54", "55 to 59", "60 to 64", "65 to 69", "70 and up"]
AGE_SPANS = [[None, 24], [25, 29], [30, 34], [35, 39], [40, 44],
             [45, 49], [50, 54], [55, 59], [60, 64], [65, 69], [70, None]]
SVC_BINS = ["Under 1", "1 to 4", "5 to 9", "10 to 14", "15 to 19",
            "20 to 24", "25 to 29", "30 to 34", "35 to 39", "40 and up"]
SVC_BIN_SPANS = [[0, 0], [1, 4], [5, 9], [10, 14], [15, 19],
                 [20, 24], [25, 29], [30, 34], [35, 39], [40, None]]

# ---- Table A-9 (p.45): General active member counts
A9 = {
    "page": 45, "title": "Table A-9 Distribution of Active Members - General",
    "row_labels": AGE_ROWS, "col_labels": SVC_BINS,
    "row_spans": AGE_SPANS, "col_spans": SVC_BIN_SPANS,
    "cells": [
        [None, None, None, None, None, None, None, None, None, None],
        [None, 27,   42,   None, None, None, None, None, None, None],
        [1,    37,   115,  38,   2,    None, None, None, None, None],
        [2,    27,   110,  154,  50,   2,    None, None, None, None],
        [None, 24,   97,   164,  151,  51,   3,    None, None, None],
        [3,    25,   81,   107,  202,  166,  60,   6,    None, None],
        [1,    29,   81,   98,   212,  226,  171,  115,  12,   1],
        [3,    16,   52,   92,   147,  107,  75,   53,   6,    None],
        [None, 11,   34,   71,   81,   42,   22,   15,   2,    None],
        [None, 7,    17,   22,   10,   9,    2,    1,    1,    None],
        [1,    None, 6,    8,    1,    None, None, None, None, 1],
    ],
    "printed_row_totals": [None, 69, 193, 345, 490, 650, 946, 551, 278, 69, 17],
    "printed_col_totals": [11, 203, 635, 754, 856, 603, 333, 190, 21, 2],
}

# ---- Table A-11 (p.46): Safety active member counts
A11 = {
    "page": 46, "title": "Table A-11 Distribution of Active Members - Safety",
    "row_labels": AGE_ROWS, "col_labels": SVC_BINS,
    "row_spans": AGE_SPANS, "col_spans": SVC_BIN_SPANS,
    "cells": [
        [45,   15,   None, None, None, None, None, None, None, None],
        [79,   194,  25,   None, None, None, None, None, None, None],
        [24,   127,  116,  85,   None, None, None, None, None, None],
        [8,    57,   93,   208,  34,   None, None, None, None, None],
        [2,    12,   38,   149,  133,  31,   None, None, None, None],
        [1,    6,    17,   53,   113,  165,  29,   None, None, None],
        [None, 1,    2,    21,   49,   87,   69,   8,    None, None],
        [1,    1,    1,    9,    12,   15,   7,    5,    None, None],
        [None, None, 1,    1,    None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None, None],
    ],
    "printed_row_totals": [60, 298, 352, 400, 365, 384, 237, 51, 2, None, None],
    "printed_col_totals": [160, 413, 293, 526, 341, 298, 105, 13, None, None],
}

TARGET_ROW_SPANS = {a: [int(a), int(a)] for a in
                    ["25", "30", "35", "40", "45", "50", "55", "60", "65", "70"]}

# the sd collector's column convention: each template col <- ONE source year
COL_SOURCE = {"1": "1", "2": "2", "3": "3", "4": "4", "6": "6", "8": "8",
              "10": "10", "11": "11", "12": "12", "30": "20+", "40": "20+"}


def main():
    row_map = [{"target": a, "sources": ["General", "Safety"],
                "op": "group_weighted", "weights_table": None,
                "weights_tables": [1, 2]} for a in TARGET_ROW_SPANS]
    col_map = [{"target": c, "sources": [s], "op": "copy"}
               for c, s in COL_SOURCE.items()]

    derived = ops.execute([B2, A9, A11], row_map, col_map, transpose=True,
                          target_row_spans=TARGET_ROW_SPANS,
                          to_decimal=True)

    truth = harness.load_truth(WORKBOOK, "Sep_Rate")
    report = harness.score(truth, derived, zero_equals_empty=True)
    harness.print_report(report)

    # blend arithmetic spot checks (shares confirmed against A-9/A-11 joints)
    def cell(svc, age):
        return derived["cells"][derived["row_labels"].index(age)][
            derived["col_labels"].index(svc)]
    a = 27 / (27 + 194)                       # age 25, svc bucket 1-4
    assert abs(cell("1", "25") - (a * 0.09 + (1 - a) * 0.08)) < 1e-12
    a = 38 / (38 + 85)                        # age 30, svc bucket 10-14
    assert abs(cell("10", "30") - (a * 0.0275 + (1 - a) * 0.018)) < 1e-12
    a = 42 / (42 + 25)                        # age 25, svc bucket 5-9
    assert abs(cell("6", "25") - (a * 0.045 + (1 - a) * 0.0275)) < 1e-12

    # every mismatch must be in the two adjudicated classes: cols 30/40 (the
    # '20+' span vs single-bucket weight convention) - nothing else
    for m in report["mismatches"]:
        assert "x svc 30]" in m or "x svc 40]" in m, f"unexpected mismatch: {m}"
    print("blend verified: joint-count shares exact; residuals confined to the")
    print("cols-30/40 weight-bucket convention (register entry 4)")
    print("PASS: group_weighted reproduces the sd Sep_Rate blend")


if __name__ == "__main__":
    main()
