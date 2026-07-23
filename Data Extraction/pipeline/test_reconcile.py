"""Fix #5 regression: best-of-N's plan-total reconciliation signal.

The per-table printed-totals check cannot see a WRONG-TABLE-SET error - mil
transcribed all 12 employer/tier tables (each internally consistent) and
summed them, tripling the General count (27,858 vs 10,974). Only reconciling
the DERIVED grid total against the known plan total (PPD actives_tot) catches
it. This tests `extract._reconcile_penalty`, the signal best-of-N ranks on
(key = contract, reconcile, totals).
Run: python pipeline/test_reconcile.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402


def _candidate(cell_total):
    """A trivial contract-shaped result whose derived grid sums to cell_total
    (one source cell copied straight through)."""
    return {
        "source_tables": [{"page": 1, "title": "t", "row_labels": ["a"],
                           "col_labels": ["x"], "cells": [[cell_total]],
                           "printed_row_totals": None, "printed_col_totals": None}],
        "row_map": [{"target": "a", "sources": ["a"], "op": "copy", "weights_table": None}],
        "col_map": [{"target": "x", "sources": ["x"], "op": "copy"}],
        "derive": None, "transpose": False,
    }


SPEC = {"grid": {"row_labels": ["a"], "col_labels": ["x"]}}


def main():
    # exact match -> no penalty
    assert extract._reconcile_penalty(_candidate(10974), SPEC, 10974) == 0.0
    # within 2% -> still no penalty (never reorder already-correct candidates)
    assert extract._reconcile_penalty(_candidate(10974), SPEC, 11000) == 0.0
    # the mil over-sum (2.54x) -> a large penalty that loses to a reconciling peer
    over = extract._reconcile_penalty(_candidate(27858), SPEC, 10974)
    assert abs(over - 1.5386) < 1e-3, over
    # no reference (non-count target) -> penalty inert
    assert extract._reconcile_penalty(_candidate(27858), SPEC, None) == 0.0
    # unexecutable candidate -> deprioritised, not fatal
    broken = {"source_tables": [], "row_map": [{"target": "a", "sources": ["a"],
              "op": "copy", "weights_table": None}],
              "col_map": [{"target": "x", "sources": ["x"], "op": "copy"}],
              "derive": None, "transpose": False}
    assert extract._reconcile_penalty(broken, SPEC, 10974) == 9.999

    # ranking: a clean-summing candidate beats an over-summing one even when the
    # over-summing one has FEWER printed-totals violations (key orders recon
    # above totals for count targets)
    good = (0, extract._reconcile_penalty(_candidate(10974), SPEC, 10974), 3)  # reconciles, 3 totals
    bad = (0, over, 0)                                                          # over-sums, 0 totals
    assert good < bad, (good, bad)

    print("PASS: reconciliation penalty catches the wrong-table-set double-count "
          "and best-of-N ranks the reconciling candidate first")


if __name__ == "__main__":
    main()
