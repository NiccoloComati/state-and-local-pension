"""Contract verification for the 'unavailable' declaration.

Trigger case (mil_Age_Serv_Wage_20260713_164600): Milwaukee's AV publishes no
salary-by-age-and-service exhibit. The model's FIRST answer was the honest one
(source_tables: [], "no data exists to derive average salary by age and
service"), but the validator's non-empty rule rejected it and the retry was
forced to stuff in a placeholder counts table. The contract now lets Stage A
declare the target unavailable: empty maps, null derive, explanatory notes,
optional evidence tables; Stage B derives the empty template grid.

Run: python pipeline/test_unavailable.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402
import ops      # noqa: E402

GOOD = {
    "unavailable": True,
    "source_tables": [
        {"page": 60, "title": "SUMMARY OF ACTIVE MEMBERS (age-only earnings)",
         "row_labels": ["Under 25", "25-29"], "col_labels": ["Average Earnings"],
         "cells": [[40914], [49285]],
         "printed_row_totals": None, "printed_col_totals": None},
    ],
    "row_map": [],
    "col_map": [],
    "derive": None,
    "transpose": False,
    "notes": "The report publishes age-only earnings summaries and age x service "
             "counts, but no salary broken down by both age and service.",
}


def expect(result, must_mention, label):
    problems = extract.validate(copy.deepcopy(result))
    assert any(must_mention in pb for pb in problems), \
        f"{label}: expected a problem mentioning {must_mention!r}, got {problems}"
    print(f"  rejected as expected - {label}")


def main():
    # the honest declaration validates cleanly (with or without evidence tables)
    assert extract.validate(copy.deepcopy(GOOD)) == [], extract.validate(copy.deepcopy(GOOD))
    bare = dict(copy.deepcopy(GOOD), source_tables=[])
    assert extract.validate(bare) == [], extract.validate(bare)
    print("  clean unavailable declarations validate (evidence tables optional)")

    # half-states are rejected: unavailable must not carry maps/derive/blank notes
    bad = copy.deepcopy(GOOD)
    bad["row_map"] = [{"target": "<25", "sources": [], "op": "copy",
                       "weights_table": None}]
    expect(bad, "EMPTY list", "unavailable with a non-empty row_map")
    bad = dict(copy.deepcopy(GOOD), derive={"op": "sum", "tables": [0, 0]})
    expect(bad, "derive to be null", "unavailable with a derive op")
    bad = dict(copy.deepcopy(GOOD), notes="  ")
    expect(bad, "notes stating what the document publishes",
           "unavailable with blank notes")

    # empty source_tables WITHOUT the flag now points the retry at the fix
    bad = dict(copy.deepcopy(GOOD), unavailable=False, source_tables=[],
               row_map=[], col_map=[])
    expect(bad, '"unavailable": true', "empty tables without the flag")

    # the REAL archived first attempt from the Milwaukee wage run must get the
    # same guidance (this is the response the old contract forced to retry
    # into a placeholder)
    run = os.path.join(os.path.dirname(HERE), "runs", "mil_Age_Serv_Wage_20260713_164600")
    with open(os.path.join(run, "record.json"), encoding="utf-8") as fh:
        attempt0 = json.load(fh)["attempts"][0]
    text = next(b["text"] for b in attempt0["response"]["content"]
                if b["type"] == "text")
    problems = extract.validate(extract._parse(text))
    assert any('"unavailable": true' in pb for pb in problems), problems
    print("  archived mil wage attempt-0 now gets the unavailable guidance")

    # stage B: the empty template grid in target shape
    spec = json.load(open(os.path.join(HERE, "targets.json"),
                          encoding="utf-8"))["Age_Serv_Wage"]
    g = ops.empty_grid(spec["grid"]["row_labels"], spec["grid"]["col_labels"])
    assert g["row_labels"] == spec["grid"]["row_labels"]
    assert g["col_labels"] == spec["grid"]["col_labels"]
    assert all(v is None for row in g["cells"] for v in row)
    assert len(g["cells"]) == len(g["row_labels"])
    assert all(len(r) == len(g["col_labels"]) for r in g["cells"])
    print("  empty_grid produces the all-null template-shaped grid")

    print("PASS: unavailable contract - honest declarations accepted, half-states"
          "\n      rejected, the archived mil failure now routes to the fix")


if __name__ == "__main__":
    main()
