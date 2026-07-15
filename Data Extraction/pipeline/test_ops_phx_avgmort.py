"""Full Avg_Mort executor test - the rung-3 ladder case end to end, on the
ACTUAL Phoenix tables, hand-transcribed source-native:
  - p.48 sample mortality rates (pre/post-retirement + post-disability, M/W,
    5-year sample ages 20-90, percent)
  - actives counts by age (Exhibit F.3 printed row totals)
  - retiree counts by age (pp.41-43 distribution, '90 & Up' as printed)

The collector's verified recipe (phx_log + ml_extraction_handoff, checked to
the decimal 2026-07-07) falls out of ONE group_weighted column entry:
  Death_Prob <- group_weighted(Pre-M, Pre-W, Post-M, Post-W),
                weights [actives, actives, retirees, retirees]
- M/F simple average: same weight table for a population's two sex columns.
- ages 20-49 pre-only: the retiree table has no bins below 50 -> weight 0.
- ages 50-69 blend: both tables cover them (bin fracs cancel).
- ages 70+ post-only: the actives 'Over 65' bin is DECLARED clipped to
  [65, 69] (the collector's implicit judgment, stated in notes per the target
  rule) so active weight vanishes beyond 69.
- 5-year bands: each sample row's declared span ([50, 54] for '50') maps it
  onto its band's single-age target rows.
- rows 95-119: beyond the printed sample table -> empty (the workbook carries
  the age-90 value forward - register entry 2 class, the ONLY residual).

Run: python pipeline/test_ops_phx_avgmort.py
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

SAMPLE_AGES = ["20", "25", "30", "35", "40", "45", "50", "55",
               "60", "65", "70", "75", "80", "85", "90"]
MAIN = {
    "page": 48, "title": "Sample Probability of Death (pre/post retirement, post-disability)",
    "row_labels": SAMPLE_AGES,
    "col_labels": ["Pre-M", "Pre-W", "Post-M", "Post-W", "Dis-M", "Dis-W"],
    "row_spans": [[a, a + 4] for a in range(20, 95, 5)],
    "cells": [
        [0.024, 0.016, 0.019, 0.013, 0.580, 0.190],
        [0.032, 0.020, 0.023, 0.018, 0.663, 0.192],
        [0.041, 0.023, 0.032, 0.026, 0.599, 0.237],
        [0.050, 0.036, 0.053, 0.047, 0.760, 0.394],
        [0.065, 0.049, 0.096, 0.089, 1.011, 0.580],
        [0.090, 0.065, 0.193, 0.184, 1.581, 0.869],
        [0.130, 0.091, 0.420, 0.425, 1.762, 1.021],
        [0.206, 0.140, 0.540, 0.423, 2.011, 1.345],
        [0.322, 0.207, 0.742, 0.496, 2.480, 1.769],
        [0.468, 0.295, 0.970, 0.674, 3.250, 2.211],
        [0.631, 0.405, 1.573, 1.098, 4.200, 2.848],
        [0.843, 0.581, 2.607, 1.903, 5.623, 4.084],
        [1.175, 0.918, 4.629, 3.271, 7.952, 6.196],
        [8.340, 5.952, 8.340, 5.952, 11.688, 9.347],
        [14.360, 11.010, 14.360, 11.010, 17.508, 13.685],
    ],
    "printed_row_totals": None, "printed_col_totals": None,
    "values_unit": "percent",
}

# Exhibit F.3 printed per-age totals; 'Over 65' declared CLIPPED to [65, 69]
# (the collector's implicit judgment - active membership beyond 69 negligible)
ACTIVES = {
    "page": 38, "title": "Active Member Counts by Age (Exhibit F.3 totals)",
    "row_labels": ["Under 20", "20-24", "25-29", "30-34", "35-39", "40-44",
                   "45-49", "50-54", "55-59", "60-64", "Over 65"],
    "col_labels": ["Count"],
    "row_spans": [[None, 19], [20, 24], [25, 29], [30, 34], [35, 39],
                  [40, 44], [45, 49], [50, 54], [55, 59], [60, 64], [65, 69]],
    "cells": [[4], [150], [442], [642], [876], [1075], [1334],
              [1312], [1187], [665], [254]],
    "printed_row_totals": None, "printed_col_totals": None,
}

RETIREES = {
    "page": 41, "title": "Retirees and Beneficiaries by Age",
    "row_labels": ["50-54", "55-59", "60-64", "65-69", "70-74", "75-79",
                   "80-84", "85-89", "90 & Up"],
    "col_labels": ["Count"],
    "row_spans": [[50, 54], [55, 59], [60, 64], [65, 69], [70, 74],
                  [75, 79], [80, 84], [85, 89], [90, None]],
    "cells": [[168], [594], [1178], [1499], [1193], [689], [390], [186], [116]],
    "printed_row_totals": None, "printed_col_totals": None,
}


def main():
    spec = json.load(open(os.path.join(HERE, "targets.json"),
                          encoding="utf-8"))["Avg_Mort"]
    bands = {a: str(a - a % 5) for a in range(20, 95)}     # 95+ unprinted
    row_map = []
    for tgt in spec["grid"]["row_labels"]:
        src = bands.get(int(tgt))
        row_map.append({"target": tgt,
                        "sources": [src] if src else [],
                        "op": "overlap_weighted", "weights_table": None,
                        "source_spans": [[int(src), int(src) + 4]] if src else []})
    col_map = [{"target": "Death_Prob",
                "sources": ["Pre-M", "Pre-W", "Post-M", "Post-W"],
                "op": "group_weighted", "weights_tables": [1, 1, 2, 2]}]

    derived = ops.execute([MAIN, ACTIVES, RETIREES], row_map, col_map,
                          target_row_spans=spec["target_row_spans"],
                          to_decimal=True)

    truth = harness.load_truth(WORKBOOK, "Avg_Mort")
    report = harness.score(truth, derived)
    harness.print_report(report)

    def cell(age):
        return derived["cells"][derived["row_labels"].index(age)][0]

    # the verified recipe values, per segment
    def close(v, x, tol=1e-15):
        return abs(v - x) < tol
    assert close(cell("20"), 0.0002), cell("20")               # pre-only M/W avg
    assert close(cell("47"), 0.000775), cell("47")             # band constancy
    assert cell("50") == 0.0014591621621621621, cell("50")     # the ladder blend
    assert close(cell("55"), 0.0027589107243121843, 1e-17)
    assert close(cell("65"), 0.007581739874500856, 1e-17)      # clipped 65+ bin
    assert cell("69") == cell("65")
    assert close(cell("70"), 0.013355), cell("70")             # post-only
    assert close(cell("94"), 0.12685), cell("94")              # last printed band
    assert cell("95") is None                                  # no extrapolation

    # the ONLY residual class: rows 95-119, where the workbook carries the
    # age-90 value forward (register entry 2)
    assert report["exact"] == 75 and report["missing_in_cand"] == 25, report
    for m in report["mismatches"]:
        assert "cand=None" in m, f"unexpected mismatch: {m}"
    print("PASS: Avg_Mort = one group_weighted column over the p.48 panels;")
    print("ages 20-94 exact (75/75); only residual = the 95+ carry-forward")
    print("convention (register entry 2)")


if __name__ == "__main__":
    main()
