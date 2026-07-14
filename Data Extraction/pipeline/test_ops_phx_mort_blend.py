"""group_weighted micro-test on the verified phx Avg_Mort ladder case
(ml_extraction_handoff §1 rung 3, verified cell-by-cell 2026-07-07).

phx AV p.48 prints sex-split sample mortality rates for pre-retirement and
post-retirement populations; the collector built the unisex column as
  ages 50-69: headcount-weighted blend of the two populations, weights =
  the actives and retirees counts she had already extracted (age 50:
  (1312 x 0.001105 + 168 x 0.004225) / 1480 = 0.0014591621621...),
  where 0.001105 = (M+F)/2 of pre-retirement and 0.004225 = (M+F)/2 of post.

One group_weighted col_map entry expresses the whole thing: sources =
[Pre-M, Pre-F, Post-M, Post-F], weights_tables = [actives, actives,
retirees, retirees]. The M/F simple average falls out of scale invariance:
weights [n_a, n_a, n_r, n_r] give
  [n_a(preM+preF) + n_r(postM+postF)] / [2 n_a + 2 n_r]
= [n_a (pre_uni) + n_r (post_uni)] / [n_a + n_r].

Weight tables are single-column (counts by age bin) -> they broadcast across
the column axis; their age bins ('50 to 54') are matched to the target row
('50') via declared row_spans. Run: python pipeline/test_ops_phx_mort_blend.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ops  # noqa: E402

# p.48 sample rates (percent, as printed) - pre- and post-retirement panels,
# transcribed as ONE main table over the shared Attained Ages column
AGES = ["20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70"]
MAIN = {
    "page": 48, "title": "Sample Probability of Death (pre/post retirement)",
    "row_labels": AGES,
    "col_labels": ["Pre-M", "Pre-F", "Post-M", "Post-F"],
    "cells": [
        [0.024, 0.016, 0.019, 0.013],
        [0.032, 0.020, 0.023, 0.018],
        [0.041, 0.023, 0.032, 0.026],
        [0.050, 0.036, 0.053, 0.047],
        [0.065, 0.049, 0.096, 0.089],
        [0.090, 0.065, 0.193, 0.184],
        [0.130, 0.091, 0.420, 0.425],
        [0.206, 0.140, 0.540, 0.423],
        [0.322, 0.207, 0.742, 0.496],
        [0.468, 0.295, 0.970, 0.674],
        [0.631, 0.405, 1.573, 1.098],
    ],
    "printed_row_totals": None, "printed_col_totals": None,
    "values_unit": "percent",
}

# headcounts the collector used as weights (from F.3 actives / retiree table)
ACTIVES = {
    "page": 38, "title": "Active member counts by age (F.3 row totals)",
    "row_labels": ["50 to 54", "55 to 59"], "col_labels": ["Count"],
    "row_spans": [[50, 54], [55, 59]], "col_spans": None,
    "cells": [[1312], [1211]],
    "printed_row_totals": None, "printed_col_totals": None,
}
RETIREES = {
    "page": 41, "title": "Retiree counts by age",
    "row_labels": ["50 to 54", "55 to 59"], "col_labels": ["Count"],
    "row_spans": [[50, 54], [55, 59]], "col_spans": None,
    "cells": [[168], [418]],
    "printed_row_totals": None, "printed_col_totals": None,
}

TARGET_ROW_SPANS = {"50": [50, 50], "55": [55, 55]}


def main():
    row_map = [{"target": a, "sources": [a], "op": "copy", "weights_table": None}
               for a in ("50", "55")]
    col_map = [{"target": "rate",
                "sources": ["Pre-M", "Pre-F", "Post-M", "Post-F"],
                "op": "group_weighted", "weights_tables": [1, 1, 2, 2]}]

    derived = ops.execute([MAIN, ACTIVES, RETIREES], row_map, col_map,
                          target_row_spans=TARGET_ROW_SPANS, to_decimal=True)

    v50 = derived["cells"][0][0]
    expect50 = (1312 * 0.001105 + 168 * 0.004225) / 1480
    print(f"age 50: derived {v50!r}  expected {expect50!r}")
    assert abs(v50 - expect50) < 1e-15, (v50, expect50)

    v55 = derived["cells"][1][0]
    expect55 = (1211 * (0.00206 + 0.00140) / 2 + 418 * (0.00540 + 0.00423) / 2) \
        / (1211 + 418)
    print(f"age 55: derived {v55!r}  expected {expect55!r}")
    assert abs(v55 - expect55) < 1e-15, (v55, expect55)

    print("PASS: group_weighted reproduces the verified phx mortality blend")
    print("(the rung-3 ladder case: cross-population, headcount-weighted, M/F")
    print("simple average absorbed by weight scale invariance)")


if __name__ == "__main__":
    main()
