"""Deterministic operations executor (Stage B, mechanical part).

The model (Stage A) returns source-native tables plus DECLARED bin mappings;
this module executes them. The model does no arithmetic - every number in the
derived grid is computed here, exactly.

Contract executed:
  source_tables : [{page, title, row_labels, col_labels, cells}]  (index 0 =
                  the main table; others are auxiliaries, e.g. counts used as
                  weights for a wage table)
  row_map       : [{target, sources: [source row labels], op, weights_table}]
                  op: "copy" | "sum" | "weighted_avg"
                  weights_table: index into source_tables (weighted_avg only)
  col_map       : [{target, sources: [source col labels], op}]
                  op: "copy" | "sum" | "share_even"

Execution: rows first (source grid -> target_rows x source_cols), then
columns. "share_even" divides a source column's value evenly across all
col_map entries that reference it with share_even (the split-open-bin rule).
Null = cell absent; "*" = suppressed in source, propagated on copy, skipped
in aggregations.
"""


def _index(labels):
    return {str(l).strip(): i for i, l in enumerate(labels)}


def _get(table, ridx, cidx, r_label, c_label):
    i, j = ridx.get(str(r_label).strip()), cidx.get(str(c_label).strip())
    if i is None or j is None:
        return None
    row = table["cells"][i]
    return row[j] if j < len(row) else None


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def execute(source_tables, row_map, col_map):
    """Return the derived canonical grid. Raises ValueError on bad specs."""
    main = source_tables[0]
    m_ridx, m_cidx = _index(main["row_labels"]), _index(main["col_labels"])

    # how many share_even targets reference each source column
    share_n = {}
    for cm in col_map:
        if cm["op"] == "share_even":
            for s in cm["sources"]:
                share_n[s] = share_n.get(s, 0) + 1

    # ---- stage 1: row combination -> intermediate[target_row][source_col]
    inter = {}
    for rm in row_map:
        op = rm["op"]
        weights = None
        if op == "weighted_avg":
            wt_i = rm.get("weights_table")
            if wt_i is None:
                raise ValueError(f"row {rm['target']}: weighted_avg needs weights_table")
            weights = source_tables[wt_i]
            w_ridx, w_cidx = _index(weights["row_labels"]), _index(weights["col_labels"])

        for c_label in main["col_labels"]:
            vals = [_get(main, m_ridx, m_cidx, s, c_label) for s in rm["sources"]]
            if op == "copy":
                if len(rm["sources"]) > 1:
                    raise ValueError(f"row {rm['target']}: copy with multiple sources")
                out = vals[0] if vals else None
            elif op == "sum":
                nums = [v for v in vals if _num(v)]
                out = sum(nums) if nums else ("*" if "*" in vals else None)
            elif op == "weighted_avg":
                num, den = 0.0, 0.0
                for s, v in zip(rm["sources"], vals):
                    if not _num(v):
                        continue
                    w = _get(weights, w_ridx, w_cidx, s, c_label)
                    if _num(w):
                        num += v * w
                        den += w
                out = (num / den) if den else ("*" if "*" in vals else None)
            else:
                raise ValueError(f"unknown row op {op!r}")
            inter[(rm["target"], str(c_label).strip())] = out

    # ---- stage 2: column combination -> derived[target_row][target_col]
    row_labels = [rm["target"] for rm in row_map]
    col_labels = [cm["target"] for cm in col_map]
    cells = []
    for r in row_labels:
        row_out = []
        for cm in col_map:
            op = cm["op"]
            vals = [inter.get((r, str(s).strip())) for s in cm["sources"]]
            if op == "copy":
                if len(cm["sources"]) > 1:
                    raise ValueError(f"col {cm['target']}: copy with multiple sources")
                out = vals[0] if vals else None
            elif op == "sum":
                nums = [v for v in vals if _num(v)]
                out = sum(nums) if nums else ("*" if "*" in vals else None)
            elif op == "share_even":
                if len(cm["sources"]) != 1:
                    raise ValueError(f"col {cm['target']}: share_even takes one source")
                v = vals[0]
                out = v / share_n[cm["sources"][0]] if _num(v) else v
            else:
                raise ValueError(f"unknown col op {op!r}")
            row_out.append(out)
        cells.append(row_out)

    return {"row_labels": row_labels, "col_labels": col_labels, "cells": cells}


def totals_check(table, tol=0.5):
    """Verify the transcription against the table's PRINTED totals (if any).

    A value placed one column off leaves row sums intact but breaks column
    sums - this is the automatic tripwire for the text-layer column-alignment
    failure mode. Returns a list of discrepancy strings (empty = consistent
    or no totals printed).
    """
    problems = []
    cells = table["cells"]

    prt = table.get("printed_row_totals")
    if prt:
        for lab, row, printed in zip(table["row_labels"], cells, prt):
            if printed is None:
                continue
            s = sum(v for v in row if _num(v))
            if abs(s - printed) > tol:
                problems.append(f"row {lab!r}: cells sum to {s:g} but printed total is {printed:g}")

    pct = table.get("printed_col_totals")
    if pct:
        for j, (lab, printed) in enumerate(zip(table["col_labels"], pct)):
            if printed is None:
                continue
            s = sum(row[j] for row in cells if j < len(row) and _num(row[j]))
            if abs(s - printed) > tol:
                problems.append(f"col {lab!r}: cells sum to {s:g} but printed total is {printed:g}")

    return problems


def summarize(row_map, col_map):
    """Human-readable one-liners for the declared operations."""
    lines = []
    for rm in row_map:
        if rm["op"] != "copy" or len(rm["sources"]) != 1 or rm["sources"][0] != rm["target"]:
            w = f" weights=t{rm.get('weights_table')}" if rm["op"] == "weighted_avg" else ""
            lines.append(f"row {rm['target']!r} <- {rm['op']}({', '.join(rm['sources'])}){w}")
    for cm in col_map:
        if cm["op"] != "copy" or len(cm["sources"]) != 1 or cm["sources"][0] != cm["target"]:
            lines.append(f"col {cm['target']!r} <- {cm['op']}({', '.join(cm['sources'])})")
    return lines or ["(pure relabeling, no transformations)"]
