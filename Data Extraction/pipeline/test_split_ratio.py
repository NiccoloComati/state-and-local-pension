"""Retirement AverageBenefit: the ratio SPLIT form + the dollars/dollars guard.

chi_ff Exhibit D.1 (p.37) prints, per age band:
    Male Number | Male Annual Payments | Female Number | Female Annual Payments
and NO Total column. The target wants one average annual benefit, i.e.
(all dollars) / (all counts). The 2-source col ratio cannot say that, so:
  - chi_ff and chi_gen declared ratio(Male $, Female $) -> dollars/dollars.
    Both PASSED the contract and shipped: chi_ff's AverageBenefit column came
    out 4.44, 12.91, 15.88, 34.19, 66.44, 109.20 - scored "production".
  - phi hit the same wall and CRASHED on the arity rule after 8 attempts.
Same gap, opposite symptoms.

Under test:
  (a) ops.execute supports numerator_sources / denominator_sources (each side
      summed, then divided);
  (b) validate() rejects the split form when it is half-declared or when
      'sources' is not the union;
  (c) validate() catches a dollars/dollars ratio from the DATA (implied average
      far below the target's min_plausible_ratio_value) - so this cannot ship
      silently again;
  (d) the archived chi_ff artifact that shipped is now rejected.

Numbers are the PRINTED PDF values, and the expected output is recomputed from
them - the fix is checked against the source, not against itself.
Run: python pipeline/test_split_ratio.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402
import harness  # noqa: E402
import ops      # noqa: E402

# --- PDF (chi_ff Exhibit D.1, p.37): the first three populated age bands ---
D1 = {"page": 37, "title": "Exhibit D.1 - Service Retirement Annuitants",
      "row_labels": ["50 - 54", "55 - 59", "60 - 64"],
      "col_labels": ["Male Number", "Male Annual Payments",
                     "Female Number", "Female Annual Payments"],
      "cells": [[28, 1785714, 8, 402441],
                [432, 36048214, 37, 2791446],
                [865, 76032267, 58, 4787391]],
      "printed_row_totals": None, "printed_col_totals": None}
ROW_MAP = [{"target": t, "sources": [s], "op": "copy", "weights_table": None}
           for t, s in (("50-54", "50 - 54"), ("55-59", "55 - 59"),
                        ("60-64", "60 - 64"))]
DOLLARS = ["Male Annual Payments", "Female Annual Payments"]
COUNTS = ["Male Number", "Female Number"]
# what the exhibit actually says: (all dollars) / (all members)
EXPECTED = [(1785714 + 402441) / (28 + 8),
            (36048214 + 2791446) / (432 + 37),
            (76032267 + 4787391) / (865 + 58)]


def _good():
    return {"source_tables": [copy.deepcopy(D1)],
            "row_map": copy.deepcopy(ROW_MAP),
            "col_map": [
                {"target": "Number", "sources": COUNTS, "op": "sum"},
                {"target": "AverageBenefit", "sources": DOLLARS + COUNTS,
                 "op": "ratio", "numerator_sources": DOLLARS,
                 "denominator_sources": COUNTS}],
            "derive": None, "transpose": False,
            "notes": "Exhibit D.1 prints counts and annual payments per sex with "
                     "no Total column; both sides pooled."}


def _shipped():
    """What chi_ff/chi_gen actually declared - dollars over dollars."""
    return {"source_tables": [copy.deepcopy(D1)],
            "row_map": copy.deepcopy(ROW_MAP),
            "col_map": [
                {"target": "Number", "sources": COUNTS, "op": "sum"},
                {"target": "AverageBenefit", "sources": DOLLARS, "op": "ratio"}],
            "derive": None, "transpose": False, "notes": "as shipped"}


def expect(result, must_mention, label, spec=None):
    problems = extract.validate(copy.deepcopy(result), spec)
    assert any(must_mention in pb for pb in problems), \
        f"{label}: expected a problem mentioning {must_mention!r}, got {problems}"
    print(f"  rejected as expected - {label}")


def main():
    spec = json.load(open(os.path.join(HERE, "targets.json"),
                          encoding="utf-8"))["Retirement"]
    floor = spec["min_plausible_ratio_value"]

    # 1. executor: each side is summed, THEN divided
    g = ops.execute([D1], ROW_MAP, _good()["col_map"])
    for i, (lab, want) in enumerate(zip(["50-54", "55-59", "60-64"], EXPECTED)):
        got = g["cells"][i][1]
        assert abs(got - want) < 1e-9, (lab, got, want)
    assert g["cells"][0][0] == 36 and g["cells"][1][0] == 469
    print(f"  executor: split ratio -> {EXPECTED[0]:,.0f} / {EXPECTED[1]:,.0f} / "
          f"{EXPECTED[2]:,.0f} per member (counts 36 / 469 / 923)")

    # the shipped declaration reproduces the nonsense it shipped (regression
    # anchor: this is what the guard has to catch)
    bad = ops.execute([D1], ROW_MAP, _shipped()["col_map"])
    assert abs(bad["cells"][0][1] - 1785714 / 402441) < 1e-9
    print(f"  the shipped ratio(Male $, Female $) yields "
          f"{bad['cells'][0][1]:,.2f} - not an average of anything")

    # 2. the honest declaration validates clean
    assert extract.validate(_good(), spec) == [], extract.validate(_good(), spec)
    print("  the split declaration validates cleanly")

    # 3. half-declared / mismatched split forms are rejected
    half = _good()
    half["col_map"][1].pop("denominator_sources")
    expect(half, "SPLIT form", "numerator_sources without denominator_sources", spec)
    mism = _good()
    mism["col_map"][1]["sources"] = DOLLARS          # not the union
    expect(mism, "union", "sources not the union of the two sides", spec)
    misplaced = _good()
    misplaced["col_map"][0]["numerator_sources"] = DOLLARS
    expect(misplaced, "only belong on a 'ratio'", "split keys on a non-ratio col", spec)

    # 4. THE GUARD: dollars/dollars is caught from the data
    expect(_shipped(), "DENOMINATOR is not a member count",
           "the shipped dollars/dollars ratio", spec)
    implied = sum(r[1] for r in D1["cells"]) / sum(r[3] for r in D1["cells"])
    print(f"  guard fires: implied average {implied:,.2f} << floor {floor:,}")

    # 5. no false positive: a plain, correct 2-source ratio stays silent
    two = {"source_tables": [copy.deepcopy(D1)],
           "row_map": copy.deepcopy(ROW_MAP),
           "col_map": [{"target": "Number", "sources": ["Male Number"], "op": "copy"},
                       {"target": "AverageBenefit",
                        "sources": ["Male Annual Payments", "Male Number"],
                        "op": "ratio"}],
           "derive": None, "transpose": False, "notes": "males only"}
    assert extract.validate(two, spec) == [], extract.validate(two, spec)
    print(f"  no false positive on a correct $/count ratio "
          f"({sum(r[1] for r in D1['cells']) / sum(r[0] for r in D1['cells']):,.0f})")

    # 6. the ARCHIVED artifact that shipped is now rejected
    run = harness.find_run("chi_ff_Retirement_20260727_142929")
    with open(os.path.join(run, "extraction.json"), encoding="utf-8") as fh:
        shipped = json.load(fh)
    probs = extract.validate(shipped, spec)
    assert any("DENOMINATOR is not a member count" in x for x in probs), probs
    print("  the archived chi_ff extraction.json is now a contract violation")

    print("PASS: split ratio reproduces the exhibit; dollars/dollars is caught "
          "from the data and can no longer ship")


if __name__ == "__main__":
    main()
