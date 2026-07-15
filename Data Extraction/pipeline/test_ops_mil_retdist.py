"""Executor verification for Retirement on the HARDEST truth shape: Milwaukee.

mil publishes retirees in three group tables (General p.80, Policemen p.81,
Firemen p.82), each Count M/F/Total + MONTHLY Benefits M/F/Total, with '59 &
Under' and '90 & Over' buckets. The workbook recipe (back-solved, verified to
the dollar): sum the three groups, x12 the dollars, avg = dollars/count, and
split each multi-row bucket evenly ('59 & Under' across 50-54/55-59; '90 &
Over' across 90-94/95-99/100 & up - the collector's own note says "split the
age buckets evenly when needed").

Composition under test: derive=sum + row share_even + col ratio +
annualize_monthly, in one declaration.
Run: python pipeline/test_ops_mil_retdist.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

ROWS = ["59 & Under", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89",
        "90 & Over"]
COLS = ["Count - Male", "Count - Female", "Count - Total",
        "Monthly Benefits - Male", "Monthly Benefits - Female",
        "Monthly Benefits - Total"]

# as printed on pp.80-82 (Total rows -> printed_col_totals, checked below)
GENERAL = {
    "cells": [
        [101, 142,  243,  289494, 334937,  624431],
        [625, 635, 1260, 1422994, 918304, 2341298],
        [981, 1056, 2037, 2125266, 1458502, 3583768],
        [935, 837, 1772, 2253026, 1115232, 3368258],
        [460, 488,  948, 1141550, 609682, 1751232],
        [315, 401,  716,  741554, 395963, 1137517],
        [226, 316,  542,  521893, 236066,  757959],
        [160, 255,  415,  294455, 150351,  444806],
    ],
    "totals": [3803, 4130, 7933, 8790232, 5219037, 14009269], "page": 80,
    "title": "SUMMARY OF RETIRED MEMBERS - General Employees",
}
POLICE = {
    "cells": [
        [419,  88, 507, 2205945, 475211, 2681156],
        [231,  53, 284, 1184003, 249492, 1433495],
        [267,  35, 302, 1342759, 173272, 1516031],
        [308,  21, 329, 1608347,  89446, 1697793],
        [233,   0, 233, 1062883,      0, 1062883],
        [143,   2, 145,  556787,   7476,  564263],
        [80,    1,  81,  268361,   1418,  269779],
        [43,    2,  45,  142132,   4776,  146908],
    ],
    "totals": [1724, 202, 1926, 8371217, 1001091, 9372308], "page": 81,
    "title": "SUMMARY OF RETIRED MEMBERS - Policemen",
}
FIRE = {
    "cells": [
        [199, 22, 221, 1006939, 110453, 1117392],
        [203, 15, 218, 1069514,  68163, 1137677],
        [170,  5, 175,  849252,  17982,  867234],
        [156,  2, 158,  827260,   9794,  837054],
        [110,  0, 110,  515637,      0,  515637],
        [67,   0,  67,  294321,      0,  294321],
        [54,   1,  55,  197915,   3925,  201840],
        [41,   0,  41,  136531,      0,  136531],
    ],
    "totals": [1000, 45, 1045, 4897369, 210317, 5107686], "page": 82,
    "title": "SUMMARY OF RETIRED MEMBERS - Firemen",
}


def _table(d):
    return {"page": d["page"], "title": d["title"], "row_labels": ROWS,
            "col_labels": COLS, "cells": d["cells"],
            "printed_col_totals": d["totals"]}


tables = [_table(GENERAL), _table(POLICE), _table(FIRE)]
for k, t in enumerate(tables):
    problems = ops.totals_check(t)
    assert not problems, f"hand transcription table {k}: {problems}"
print("printed totals check: OK on all three group tables")

spec = json.load(open(os.path.join(HERE, "targets.json"),
                      encoding="utf-8"))["Retirement"]

SRC_FOR = {"60-64": "60-64", "65-69": "65-69", "70-74": "70-74",
           "75-79": "75-79", "80-84": "80-84", "85-89": "85-89"}
row_map = []
for tgt in spec["grid"]["row_labels"]:
    if tgt in SRC_FOR:
        row_map.append({"target": tgt, "sources": [SRC_FOR[tgt]],
                        "op": "copy", "weights_table": None})
    elif tgt in ("50-54", "55-59"):
        row_map.append({"target": tgt, "sources": ["59 & Under"],
                        "op": "share_even", "weights_table": None})
    else:   # 90-94 / 95-99 / 100 & over
        row_map.append({"target": tgt, "sources": ["90 & Over"],
                        "op": "share_even", "weights_table": None})
col_map = [
    {"target": "Number", "sources": ["Count - Total"], "op": "copy"},
    {"target": "AverageBenefit",
     "sources": ["Monthly Benefits - Total", "Count - Total"],
     "op": "ratio", "annualize_monthly": True},
]

derived = ops.execute(tables, row_map, col_map,
                      derive={"op": "sum", "tables": [0, 1, 2]})

WB = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                  "Data", "Plans", "Cities", "mil_modeldata", "mil_data19_gen.xlsx")
truth = harness.load_truth(WB, "Retirement")
rep = harness.score(truth, derived, zero_equals_empty=spec["zero_equals_empty"])
print("mil Retirement derived-vs-workbook:")
harness.print_report(rep)

assert rep["exact"] + rep["close"] == 22 and rep["wrong"] == 0, rep
assert rep["missing_in_cand"] == rep["extra_in_cand"] == 0, rep
# the two split buckets: 971/2 in 50-54/55-59, 501/3 in the 90+ rows,
# each with its bucket's annualized average
assert abs(derived["cells"][0][0] - 971 / 2) < 1e-12
assert abs(derived["cells"][0][1] - 53075748 / 971) < 1e-9
assert abs(derived["cells"][10][0] - 501 / 3) < 1e-12
assert abs(derived["cells"][10][1] - 8738940 / 501) < 1e-9
print("\nPASS: derive=sum over three groups + share_even buckets + ratio column"
      "\n      + annualize_monthly reproduce the mil Retirement sheet exactly")
