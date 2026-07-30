"""Regressions for the two CODE bugs that crashed 15 of round 3's 42 cells.

Both were our faults, not model failures, and both aborted a whole cell instead
of routing into the retry loop that exists precisely for these cases.

1. `_evaluate` returned `totals` as the int 0 on the unparseable-JSON path while
   every other path returns a list; the caller does len(totals) to rank
   best-of-N candidates -> "object of type 'int' has no len()" killed 12 cells
   (aus_pol/bos/chi_edu/chi_pol/clt_ff x2/hou_gen x2/lax_gen/mil/nyc_edu/sf,
   across all six sheets).
2. validate() checked share_even arity with `len(srcs) > 1`, so an EMPTY sources
   list passed validation and the executor raised "share_even takes one source"
   -> 3 cells. `copy` with no sources stays legal: that is how "the document
   publishes nothing for this target" is declared.

Run: python pipeline/test_round3_crash_guards.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402

SPEC = json.load(open(os.path.join(HERE, "targets.json"), encoding="utf-8"))["Sep_Rate"]


def test_unparseable_response_returns_list_totals():
    """The bug: totals came back as 0, so len(totals) blew up."""
    result, fatal, totals, allp = extract._evaluate("this is not JSON at all", SPEC)
    assert result is None
    assert fatal and "not parseable" in fatal[0]
    assert isinstance(totals, list), f"totals must be a list, got {type(totals).__name__}"
    # the actual crash site: ranking a candidate
    key = (len(fatal), 10.0, len(totals))
    assert key == (1, 10.0, 0), key
    print("  unparseable JSON -> totals is a list, ranking key computes OK")


def test_all_evaluate_paths_agree_on_types():
    """Every _evaluate return path must give (result|None, list, list, list)."""
    cases = {"unparseable": "{{{ not json",
             "valid-shape-but-empty": json.dumps(
                 {"source_tables": [], "row_map": [], "col_map": [],
                  "derive": None, "transpose": False, "notes": "x"})}
    for name, text in cases.items():
        result, fatal, totals, allp = extract._evaluate(text, SPEC)
        assert isinstance(fatal, list), (name, type(fatal))
        assert isinstance(totals, list), (name, type(totals))
        assert isinstance(allp, list), (name, type(allp))
    print("  every _evaluate path returns list-typed problem collections")


def _res(op, sources):
    return {"source_tables": [{"page": 1, "title": "T",
                               "row_labels": ["a"], "col_labels": ["b"],
                               "cells": [[1.0]]}],
            "row_map": [{"target": "25", "sources": sources, "op": op}],
            "col_map": [{"target": "1", "sources": ["b"], "op": "copy"}],
            "derive": None, "transpose": False, "notes": "n"}


def test_share_even_empty_rejected():
    p = extract.validate(_res("share_even", []), SPEC)
    assert any("share_even" in x and "exactly one source" in x for x in p), p
    print("  share_even with EMPTY sources is now rejected by validate")


def test_share_even_multi_still_rejected():
    p = extract.validate(_res("share_even", ["a", "b"]), SPEC)
    assert any("takes exactly one" in x for x in p), p
    print("  share_even with >1 source still rejected")


def test_copy_empty_still_allowed():
    """copy+[] is the legal 'no data for this target' declaration - must NOT fire."""
    p = extract.validate(_res("copy", []), SPEC)
    assert not any("share_even" in x for x in p), p
    assert not any("exactly one source" in x for x in p), p
    print("  copy with EMPTY sources still allowed (no-data declaration)")




# ---------------------------------------------------------- empty-axis guard
def _axis_res(row_srcs, col_srcs, broadcast=None):
    return {"source_tables": [{"page": 1, "title": "T", "row_labels": ["a"],
                               "col_labels": ["b"], "cells": [[1.0]]}],
            "row_map": [{"target": "25", "sources": row_srcs, "op": "copy"}],
            "col_map": [{"target": "1", "sources": col_srcs, "op": "copy"}],
            "derive": None, "transpose": False, "broadcast": broadcast,
            "notes": "n"}


def _fires(res, spec=SPEC):
    return any("NOT ONE of the" in x for x in extract.validate(res, spec))


def test_empty_axis_rejected():
    """phx Ret_Rate round 3: right table transcribed, every row_map entry given
    empty sources -> all-null grid, 0.8624 -> 0.00. Nine round-3 cells were
    scored on grids with no non-zero value at all (one of them 1.00, because
    zero_equals_empty matches truth-0 against cand-None)."""
    assert _fires(_axis_res([], ["b"])), "empty row_map axis must be rejected"
    assert _fires(_axis_res(["a"], [])), "empty col_map axis must be rejected"
    print("  an axis naming no sources at all is rejected")


def test_populated_axes_allowed():
    assert not _fires(_axis_res(["a"], ["b"]))
    print("  normally-mapped extraction still passes")


def test_broadcast_constant_axis_exempt():
    """broadcast fills one axis identically, so THAT axis is legitimately
    empty - but the varying axis must still name sources."""
    ok = _axis_res([], ["b"], broadcast={"axis": "age",
                                         "series_sources": ["b"], "series_op": "copy"})
    assert not _fires(ok), "broadcast's constant axis must be exempt"
    bad = _axis_res([], [], broadcast={"axis": "age",
                                       "series_sources": ["b"], "series_op": "copy"})
    assert _fires(bad), "broadcast with BOTH axes empty derives nothing"
    print("  broadcast: constant axis exempt, both-empty still rejected")


if __name__ == "__main__":
    test_unparseable_response_returns_list_totals()
    test_all_evaluate_paths_agree_on_types()
    test_share_even_empty_rejected()
    test_share_even_multi_still_rejected()
    test_copy_empty_still_allowed()
    test_empty_axis_rejected()
    test_populated_axes_allowed()
    test_broadcast_constant_axis_exempt()
    print("test_round3_crash_guards: ALL PASS")
