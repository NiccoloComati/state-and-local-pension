"""A mapped source label that does not exist silently empties the grid.

ops._get looks a source label up with `str(l).strip()` against the table's own
labels and returns None when there is no match. Nothing validated that the
label existed, so a map naming bins the exhibit does not print produced an
all-null grid without a single error. Auditing every archived derived.json
turned this up as the most destructive gap found so far - 17 of 92 current
cells reference labels that are not there:

  Sep_Rate  12 of 16 plans. The target wants age x SERVICE, and several AVs
            publish termination rates by age only, split by sex ('Males' /
            'Females'). The model mapped target service columns '1','2','3'...
            onto a table with no service dimension, so every real cell came
            back null and the grid held nothing but the executor's
            impossibility zeros.
  Ret_Rate  aus (31 labels), bos (8), chi_gen (9)
  Avg_Mort  chi_edu (12), dal (7 - and its table 0 is the DISABILITY mortality
            exhibit, giving q(20) = 0.035)
  also      mil Age_Serv_Wage (8), sd Retirement (9)

Run: python pipeline/test_label_existence.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_derived as audit  # noqa: E402
import extract  # noqa: E402
import harness  # noqa: E402
import ops      # noqa: E402

SPECS = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))


def base():
    """A table printing rates by AGE only, split by sex - the real shape behind
    the Sep_Rate wipeout (aus, dal, hou_pol, lax_gen all print this)."""
    return {
        "source_tables": [{
            "page": 40, "title": "Termination rates",
            "row_labels": ["25", "30", "35"], "col_labels": ["Males", "Females"],
            "cells": [[0.11, 0.16], [0.08, 0.12], [0.05, 0.09]],
            "printed_row_totals": None, "printed_col_totals": None,
            "values_unit": "percent"}],
        "row_map": [{"target": t, "sources": [t], "op": "copy",
                     "weights_table": None} for t in ("25", "30", "35")],
        "col_map": [{"target": "1", "sources": ["Males"], "op": "copy"}],
        "derive": None, "transpose": False, "notes": "n"}


def main():
    spec = SPECS["Sep_Rate"]

    # a map naming only real labels is accepted
    assert not [x for x in extract.validate(base(), spec) if "do NOT exist" in x]
    print("  a map over real labels validates")

    # the live failure: target SERVICE columns onto a table with no service axis
    bad = base()
    bad["col_map"] = [{"target": c, "sources": [c], "op": "copy"}
                      for c in ("1", "2", "3")]
    msg = next((x for x in extract.validate(copy.deepcopy(bad), spec)
                if "do NOT exist" in x), None)
    assert msg, extract.validate(copy.deepcopy(bad), spec)
    assert "col_map" in msg and "'1'" in msg
    assert "Males" in msg, msg          # tells the model what IS available
    assert "EMPTY sources list" in msg  # and what to do if the axis is absent
    print("  invented service columns rejected; message lists the real labels")

    # and that really does empty the grid (why it must be fatal)
    g = ops.execute(bad["source_tables"], bad["row_map"], bad["col_map"])
    assert all(v is None for row in g["cells"] for v in row), g["cells"]
    print("  executor confirms: every cell of that grid is null")

    # transpose flips which printed axis the maps address
    tr = base()
    tr["transpose"] = True
    tr["row_map"] = [{"target": "25", "sources": ["Males"], "op": "copy",
                      "weights_table": None}]
    tr["col_map"] = [{"target": "1", "sources": ["25"], "op": "copy"}]
    assert not [x for x in extract.validate(tr, spec) if "do NOT exist" in x], \
        extract.validate(tr, spec)
    print("  transpose=true: row_map reads printed COLUMNS, accepted")

    # an empty sources list is the legal way to say "not published"
    absent = base()
    absent["col_map"] = [{"target": "1", "sources": ["Males"], "op": "copy"},
                         {"target": "2", "sources": [], "op": "copy"}]
    assert not [x for x in extract.validate(absent, spec) if "do NOT exist" in x]
    print("  an EMPTY sources list is accepted (bin not published)")

    # ---- the archived artifacts ----------------------------------------
    for run_name, tgt, axis in (
            ("aus_Sep_Rate_20260727_135638", "Sep_Rate", "col_map"),
            ("sd_Retirement_20260727_164911", "Retirement", "row_map"),
            ("mil_Age_Serv_Wage_20260727_161347", "Age_Serv_Wage", "col_map")):
        run = harness.find_run(run_name)
        with open(os.path.join(run, "extraction.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        hit = [x for x in extract.validate(d, SPECS[tgt]) if "do NOT exist" in x]
        assert hit and axis in hit[0], (run_name, hit)
        print(f"  archived {run_name.split('_2026')[0]:24s} now rejected ({axis})")

    # ---- the value auditor agrees the output was empty ------------------
    run = harness.find_run("aus_Sep_Rate_20260727_135638")
    with open(os.path.join(run, "derived.json"), encoding="utf-8") as fh:
        grid = json.load(fh)
    out = []
    audit.check_generic(grid, out)
    audit.CHECKS["Sep_Rate"](grid, out, True)
    codes = [c for _, c, _ in out]
    assert "no-rate-derived" in codes, codes
    print("  audit_derived flags the same cell as no-rate-derived")

    # dal's mortality is the WRONG POPULATION, and shows up as a level error
    run = harness.find_run("dal_Avg_Mort_20260727_150944")
    with open(os.path.join(run, "derived.json"), encoding="utf-8") as fh:
        grid = json.load(fh)
    out = []
    audit.check_mortality(grid, out)
    lvl = next((m for s, c, m in out if c == "mortality-level"), None)
    assert lvl and "q(20)" in lvl, out
    print(f"  audit_derived flags dal Avg_Mort: {lvl[:58]}...")

    print("PASS: invented source labels are now a contract violation, and the "
          "value audit independently catches what they produced")


if __name__ == "__main__":
    main()
