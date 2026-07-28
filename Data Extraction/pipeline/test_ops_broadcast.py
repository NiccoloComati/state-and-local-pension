"""Executor + contract verification for the `broadcast` op (Sep_Rate one-
dimensional rate sources).

Many AVs publish termination/withdrawal rates along ONE dimension only - by
years of service (no age), or by age (no service). The plan's actuary treats
the rate as depending on that single variable, so the faithful target grid
repeats the same rate along the axis the document does not measure. This was
the shape behind most of the 2026-07-28 audit's empty Sep_Rate grids (the
model mapped service columns onto a table that only prints Males/Females, every
lookup missed, the grid came back all-null). See assumption_register.md #4.

Run: python pipeline/test_ops_broadcast.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ops       # noqa: E402
import extract   # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Sep_Rate"]
ROW_SPANS = SPEC["target_row_spans"]
COL_SPANS = SPEC["target_col_spans"]
AGES = SPEC["grid"]["row_labels"]          # 25..70
SVC = SPEC["grid"]["col_labels"]           # 1,2,3,4,6,8,10,11,12,30,40


def _ages_map_empty():
    return [{"target": a, "sources": [], "op": "copy"} for a in AGES]


def _svc_map_empty():
    return [{"target": s, "sources": [], "op": "copy"} for s in SVC]


# ---------------------------------------------------------------- service-only
def test_service_only_copy():
    """Source lists a rate per service year (single 'Rate' column). axis=age:
    every age row is filled with the same service-based rate vector."""
    rates = {"1": 5.0, "2": 4.0, "3": 3.0, "4": 2.5, "6": 2.0, "8": 1.5,
             "10": 1.2, "11": 1.1, "12": 1.0, "30": 0.5, "40": 0.2}
    src = {"page": 71, "title": "Termination Rates",
           "row_labels": SVC, "col_labels": ["Rate"],
           "cells": [[rates[s]] for s in SVC], "values_unit": "percent"}
    col_map = [{"target": s, "sources": [s], "op": "copy"} for s in SVC]
    out = ops.execute([src], _ages_map_empty(), col_map,
                      broadcast={"axis": "age", "series_sources": ["Rate"],
                                 "series_op": "copy"},
                      target_row_spans=ROW_SPANS, target_col_spans=COL_SPANS,
                      to_decimal=True)
    assert out["row_labels"] == AGES and out["col_labels"] == SVC
    expected = [rates[s] / 100.0 for s in SVC]
    # every age row is identical and equals the decimal rate vector
    for r in out["cells"]:
        assert r == expected, (r, expected)
    print("  service-only copy: every age row = the service rate vector (percent->decimal) OK")


def test_service_only_overlap_bucket():
    """A coarse source bucket ('5 - 9' -> [5,9]) blended onto target col '6'
    ([5,6]) via overlap_weighted inside the broadcast varying axis."""
    src = {"page": 71, "title": "Termination Rates",
           "row_labels": ["1", "2", "3", "4", "5 - 9"], "col_labels": ["Rate"],
           "cells": [[5.0], [4.0], [3.0], [2.5], [2.0]], "values_unit": "percent"}
    col_map = [{"target": "1", "sources": ["1"], "op": "copy"},
               {"target": "2", "sources": ["2"], "op": "copy"},
               {"target": "3", "sources": ["3"], "op": "copy"},
               {"target": "4", "sources": ["4"], "op": "copy"},
               {"target": "6", "sources": ["5 - 9"], "op": "overlap_weighted",
                "source_spans": [[5, 9]]}]
    # only cols 1,2,3,4,6 targeted here
    ages = _ages_map_empty()
    out = ops.execute([src], ages, col_map,
                      broadcast={"axis": "age", "series_sources": ["Rate"],
                                 "series_op": "copy"},
                      target_row_spans=ROW_SPANS,
                      target_col_spans={k: COL_SPANS[k] for k in ["1", "2", "3", "4", "6"]},
                      to_decimal=True)
    # target '6'=[5,6] wholly inside source [5,9] -> copies its rate 0.02
    j = out["col_labels"].index("6")
    assert abs(out["cells"][-1][j] - 0.02) < 1e-12, out["cells"][-1][j]
    print("  service-only overlap bucket: '6'<-'5 - 9' rate blended OK")


def test_mean_male_female():
    """Two rate columns (Male/Female) with no headcount table -> simple mean."""
    src = {"page": 54, "title": "General Turnover",
           "row_labels": ["1", "2"], "col_labels": ["Male", "Female"],
           "cells": [[6.0, 4.0], [3.0, 1.0]], "values_unit": "percent"}
    col_map = [{"target": "1", "sources": ["1"], "op": "copy"},
               {"target": "2", "sources": ["2"], "op": "copy"}]
    out = ops.execute([src], _ages_map_empty(), col_map,
                      broadcast={"axis": "age", "series_sources": ["Male", "Female"],
                                 "series_op": "mean"},
                      target_row_spans=ROW_SPANS,
                      target_col_spans={k: COL_SPANS[k] for k in ["1", "2"]},
                      to_decimal=True)
    # (6+4)/2=5 -> 0.05 ; (3+1)/2=2 -> 0.02
    assert abs(out["cells"][0][0] - 0.05) < 1e-12
    assert abs(out["cells"][0][1] - 0.02) < 1e-12
    print("  mean Male/Female: (M+F)/2 per service, broadcast across age OK")


# -------------------------------------------------------------------- age-only
def test_age_only_service_axis():
    """Source lists a withdrawal rate per age (no service). axis=service:
    every service column is filled with the same age-based rate."""
    rate_by_age = {a: 10.0 - i for i, a in enumerate(AGES)}
    src = {"page": 64, "title": "Termination Rates before Retirement",
           "row_labels": AGES, "col_labels": ["Withdrawal"],
           "cells": [[rate_by_age[a]] for a in AGES], "values_unit": "percent"}
    row_map = [{"target": a, "sources": [a], "op": "copy"} for a in AGES]
    out = ops.execute([src], row_map, _svc_map_empty(),
                      broadcast={"axis": "service", "series_sources": ["Withdrawal"],
                                 "series_op": "copy"},
                      target_row_spans=ROW_SPANS, target_col_spans=COL_SPANS,
                      to_decimal=True)
    assert out["row_labels"] == AGES and out["col_labels"] == SVC
    # each age row is CONSTANT across all service columns = that age's rate
    for i, a in enumerate(AGES):
        assert all(abs(v - rate_by_age[a] / 100.0) < 1e-12 for v in out["cells"][i])
    print("  age-only: each age's rate repeated across every service column OK")


def test_impossible_zeroing_still_applies():
    """Broadcast fills every age identically; zero_impossible must still blank
    cells unreachable under the entry-age floor (service > age - 20)."""
    rates = {s: 3.0 for s in SVC}
    src = {"page": 71, "title": "Termination Rates",
           "row_labels": SVC, "col_labels": ["Rate"],
           "cells": [[rates[s]] for s in SVC], "values_unit": "percent"}
    col_map = [{"target": s, "sources": [s], "op": "copy"} for s in SVC]
    out = ops.execute([src], _ages_map_empty(), col_map,
                      broadcast={"axis": "age", "series_sources": ["Rate"],
                                 "series_op": "copy"},
                      target_row_spans=ROW_SPANS, target_col_spans=COL_SPANS,
                      to_decimal=True,
                      zero_impossible_cfg=SPEC["zero_impossible_cells"])
    a25 = out["cells"][AGES.index("25")]
    # at age 25 (max service 5 under entry-age 20), col '40'=[31,40] is impossible
    assert a25[SVC.index("40")] == 0, a25
    # ...but col '1' is reachable at every age
    assert a25[SVC.index("1")] != 0
    # at age 70, col '40' is reachable
    a70 = out["cells"][AGES.index("70")]
    assert a70[SVC.index("40")] != 0
    print("  impossibility zeroing still applies to the broadcast grid OK")


# --------------------------------------------------------------------- validate
def _base_service_only():
    return {"source_tables": [{"page": 71, "title": "Termination Rates",
                               "row_labels": ["1", "2"], "col_labels": ["Rate"],
                               "cells": [[5.0], [4.0]], "values_unit": "percent"}],
            "row_map": [{"target": a, "sources": [], "op": "copy"} for a in AGES],
            "col_map": [{"target": "1", "sources": ["1"], "op": "copy"},
                        {"target": "2", "sources": ["2"], "op": "copy"}],
            "derive": None, "transpose": False,
            "broadcast": {"axis": "age", "series_sources": ["Rate"], "series_op": "copy"},
            "notes": "rates by service only"}


def test_validate_accepts_good():
    p = extract.validate(_base_service_only(), SPEC)
    assert p == [], p
    print("  validate accepts a well-formed service-only broadcast OK")


def test_validate_rejections():
    # transpose + broadcast
    r = _base_service_only(); r["transpose"] = True
    assert any("transpose" in x for x in extract.validate(r, SPEC))
    # varying-axis (col_map) label not a source ROW
    r = _base_service_only(); r["col_map"][0]["sources"] = ["99"]
    assert any("varying axis" in x for x in extract.validate(r, SPEC))
    # series_sources not a column
    r = _base_service_only(); r["broadcast"]["series_sources"] = ["Nope"]
    assert any("series_sources" in x for x in extract.validate(r, SPEC))
    # constant-axis (row_map) has non-empty sources
    r = _base_service_only(); r["row_map"][0]["sources"] = ["1"]
    assert any("EMPTY sources" in x for x in extract.validate(r, SPEC))
    # copy with two series sources
    r = _base_service_only(); r["broadcast"]["series_sources"] = ["Rate", "Rate2"]
    assert any("copy' takes exactly one" in x for x in extract.validate(r, SPEC))
    # derive + broadcast
    r = _base_service_only()
    r["derive"] = {"op": "ratio", "numerator_table": 0, "denominator_table": 0}
    assert any("broadcast cannot be combined with derive" in x for x in extract.validate(r, SPEC))
    print("  validate rejects transpose/derive combos, bad labels, non-empty const OK")


if __name__ == "__main__":
    test_service_only_copy()
    test_service_only_overlap_bucket()
    test_mean_male_female()
    test_age_only_service_axis()
    test_impossible_zeroing_still_applies()
    test_validate_accepts_good()
    test_validate_rejections()
    print("test_ops_broadcast: ALL PASS")
