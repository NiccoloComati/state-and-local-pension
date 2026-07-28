"""chi_ff monthly-in-a-ratio: derive-level annualize + the wage-floor guard.

chi_ff Exhibit B.1 (p.32) prints MONTHLY salary. The model transcribed it
correctly and declared derive=ratio, but every derived average came out exactly
x12 too small, and no COLUMN flag could fix it: ops.execute runs _grid over the
numerator and the denominator with the same col_map, so a column-level
annualize_monthly scales both and cancels on the divide.

Fix under test:
  (a) ops.execute applies `derive.annualize_monthly` to the RATIO RESULT;
  (b) extract.validate() fires a floor guard when the implied average
      (sum numerator / sum denominator) is below the target's
      min_plausible_ratio_value and the flag is absent.

Numbers below are the PRINTED PDF values (Exhibit B.1, ages 20-24 row), and the
expected output is the workbook value - i.e. the fix is checked against the
source, not against itself.
Run: python pipeline/test_monthly_ratio_guard.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402
import ops      # noqa: E402

# --- PDF (Exhibit B.1, p.32): age 20-24 row, monthly salary + member counts ---
# 'Under 1' = 20 members / $99,840 ; '1 - 4' = 20 members / $119,627
SALARY = {"page": 32, "title": "Exhibit B.1 (monthly salary)",
          "row_labels": ["20 - 24"], "col_labels": ["Under 1", "1 - 4"],
          "cells": [[99840, 119627]],
          "printed_row_totals": None, "printed_col_totals": None}
COUNTS = {"page": 32, "title": "Exhibit B.1 (member counts)",
          "row_labels": ["20 - 24"], "col_labels": ["Under 1", "1 - 4"],
          "cells": [[20, 20]],
          "printed_row_totals": None, "printed_col_totals": None}
# target col '4' merges 'Under 1' + '1 - 4' (additive in ratio mode)
ROW_MAP = [{"target": "<25", "sources": ["20 - 24"], "op": "copy", "weights_table": None}]
COL_MAP = [{"target": "4", "sources": ["Under 1", "1 - 4"], "op": "sum"}]
# ($99,840 + $119,627) / (20 + 20) = $5,486.675 per member per MONTH
MONTHLY = (99840 + 119627) / 40
ANNUAL = MONTHLY * 12                      # 65,840.1 - the workbook value


def _result(annualize):
    d = {"op": "ratio", "numerator_table": 0, "denominator_table": 1}
    if annualize:
        d["annualize_monthly"] = True
    return {"source_tables": [json.loads(json.dumps(SALARY)),
                              json.loads(json.dumps(COUNTS))],
            "row_map": json.loads(json.dumps(ROW_MAP)),
            "col_map": json.loads(json.dumps(COL_MAP)),
            "derive": d, "transpose": False, "notes": "monthly salary exhibit"}


def main():
    spec = json.load(open(os.path.join(HERE, "targets.json"),
                          encoding="utf-8"))["Age_Serv_Wage"]

    # 1. executor: the ratio RESULT is annualized (and only when declared)
    got = ops.execute([SALARY, COUNTS], ROW_MAP, COL_MAP,
                      derive={"op": "ratio", "numerator_table": 0,
                              "denominator_table": 1,
                              "annualize_monthly": True})["cells"][0][0]
    assert abs(got - ANNUAL) < 1e-9, (got, ANNUAL)
    assert abs(got - 65840.1) < 1e-6, got          # the workbook/PDF value
    plain = ops.execute([SALARY, COUNTS], ROW_MAP, COL_MAP,
                        derive={"op": "ratio", "numerator_table": 0,
                                "denominator_table": 1})["cells"][0][0]
    assert abs(plain - MONTHLY) < 1e-9, plain      # absent flag = unchanged
    assert abs(got / plain - 12) < 1e-12
    print(f"  executor: monthly {plain:,.2f} -> annualized {got:,.1f} (PDF/workbook 65,840.1)")

    # 2. a COLUMN-level annualize still cancels inside a ratio (why (a) exists)
    col_flagged = [dict(COL_MAP[0], annualize_monthly=True)]
    cancels = ops.execute([SALARY, COUNTS], ROW_MAP, col_flagged,
                          derive={"op": "ratio", "numerator_table": 0,
                                  "denominator_table": 1})["cells"][0][0]
    assert abs(cancels - MONTHLY) < 1e-9, cancels
    print("  column-level flag cancels inside a ratio (unchanged) - as diagnosed")

    # 3. validator: floor guard fires without the flag, silent with it
    probs = extract.validate(_result(annualize=False), spec)
    assert any("annualize_monthly" in x and "MONTHLY" in x for x in probs), probs
    print("  guard fires on the monthly ratio (implied avg "
          f"{MONTHLY:,.0f} < {spec['min_plausible_ratio_value']:,})")
    assert extract.validate(_result(annualize=True), spec) == [], \
        extract.validate(_result(annualize=True), spec)
    print("  guard silent once annualize_monthly is declared")

    # 4. NO false positive on an annual-salary plan (chi_edu-like: ~74k implied)
    annual_salary = dict(json.loads(json.dumps(SALARY)),
                         cells=[[99840 * 12, 119627 * 12]])
    ok = {"source_tables": [annual_salary, json.loads(json.dumps(COUNTS))],
          "row_map": json.loads(json.dumps(ROW_MAP)),
          "col_map": json.loads(json.dumps(COL_MAP)),
          "derive": {"op": "ratio", "numerator_table": 0, "denominator_table": 1},
          "transpose": False, "notes": "annual salary exhibit"}
    assert extract.validate(ok, spec) == [], extract.validate(ok, spec)
    print(f"  no false positive on an ANNUAL exhibit (implied {ANNUAL:,.0f})")

    print("PASS: derive-level annualize reproduces the PDF value; floor guard "
          "fires on monthly, silent on annual")


if __name__ == "__main__":
    main()
