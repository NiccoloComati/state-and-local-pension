"""Deterministic operations executor (Stage B, mechanical part).

The model (Stage A) returns source-native tables plus DECLARED bin mappings;
this module executes them. The model does no arithmetic - every number in the
derived grid is computed here, exactly.

Contract executed:
  source_tables : [{page, title, row_labels, col_labels, cells}]  (index 0 =
                  the main table; others are auxiliaries, e.g. counts used as
                  weights for a wage table)
  row_map       : [{target, sources: [source row labels], op, weights_table}]
                  op: "copy" | "sum" | "share_even" | "weighted_avg"
                  weights_table: index into source_tables (weighted_avg only)
                  share_even splits a printed row bucket evenly across every
                  row_map entry that references it (e.g. '90 & Up' counts
                  split across 90-94/95-99/100+ - the collectors' documented
                  "split the age buckets evenly" convention)
  col_map       : [{target, sources: [source col labels], op, weights_table}]
                  op: "copy" | "sum" | "share_even" | "weighted_avg" | "ratio"
                  weighted_avg merges source COLUMNS of an averages table
                  (weights = the counts table, row-aggregated first)
                  ratio takes exactly two sources [numerator, denominator]:
                  value = numerator/denominator per row (average = total
                  dollars / member count when the source prints totals beside
                  counts). Row share_even divides BOTH columns by the split
                  count, so the ratio reproduces the bucket average exactly.
  derive        : null | {op: "ratio", numerator_table, denominator_table}
                       | {op: "sum", tables: [i, j, ...]}
                  ratio mode: some AVs publish TOTALS (e.g. total salary
                  dollars + member counts) instead of the averages the target
                  wants. Both tables are aggregated with the SAME row/col maps
                  (additive ops only), then divided cell-wise:
                  average = total$/count. The merged-bin average is exact by
                  construction (sum both, then divide).
                  sum mode: some AVs publish the ADDITIVE target separately
                  by employee group. Same-shaped source tables are summed
                  cell-wise first, then the normal maps run once.
  transpose     : bool (default false). The MAIN table (source_tables[0]) is
                  TRANSCRIBED as printed; code transposes it before mapping.
                  With transpose=true, row_map maps the printed COLUMNS onto
                  target rows and col_map maps the printed ROWS onto target
                  columns. Auxiliary tables (weights etc.) are NOT transposed
                  - they are used in their printed orientation.
  group_weighted (rung-3 op, rows and cols): population-weighted blend of
                  group rows/columns (e.g. General/Safety termination rates;
                  pre/post-retirement mortality). Each source gets its own
                  weights table ("weights_tables", aligned with sources) - a
                  transcribed headcount table. The weight for output cell
                  (row r, col c) is looked up in that table at the bin
                  containing (r, c): exact label match, or span containment
                  via the table's declared row_spans/col_spans and the target
                  spans; a partial overlap contributes proportionally
                  (|bin ∩ target| / |bin| of the bin's count). Single-row or
                  single-column weight tables broadcast along the missing
                  axis. value = sum(w_s * v_s) / sum(w_s).
  row_spans / col_spans (per table, optional): numeric [lo, hi] semantics of
                  the table's printed bin labels (null = open end), aligned
                  with row_labels/col_labels. Needed when a weights table's
                  bins must be matched against target coordinates.
  overlap_weighted (rung-2 op, rows and cols): re-grid RATES across
                  non-aligned bins. The map entry carries "source_spans"
                  (numeric [lo, hi] per source label, null = open end); the
                  target bins' spans are fixed template semantics passed in
                  by the caller (targets.json). weight_s = integer-year
                  overlap of the target span with source span s; value =
                  sum(w_s * v_s) / sum(w_s). Rates are intensive: bins fully
                  inside one source bin copy it; spanning bins blend
                  proportionally by years (e.g. target 12-19 across <15 and
                  15-24: 3/8, 5/8). Model judgment about ambiguous printed
                  bin boundaries is DECLARED in the spans - auditable.
  values_unit   : per-table, "percent" -> cells are scaled by 0.01 before
                  mapping when the caller requests decimal output
                  (unit semantics declared by the model; scaling done here).

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


# open span ends (null) are clipped here before overlap arithmetic; only
# open-open overlaps are cap-sensitive, and 120 exceeds any age/service year
SPAN_MAX = 120


def _transpose_table(table):
    """Swap rows and columns of a transcribed table (labels, cells, totals)."""
    cells = table["cells"]
    ncols = len(table["col_labels"])
    t = dict(table)
    t["row_labels"], t["col_labels"] = table["col_labels"], table["row_labels"]
    t["cells"] = [[row[j] if j < len(row) else None for row in cells]
                  for j in range(ncols)]
    t["printed_row_totals"] = table.get("printed_col_totals")
    t["printed_col_totals"] = table.get("printed_row_totals")
    t["row_spans"], t["col_spans"] = table.get("col_spans"), table.get("row_spans")
    return t


def _span_frac(bin_span, q_span):
    """Fraction of a bin's population attributable to the query span,
    assuming uniform distribution within the bin: |bin ∩ query| / |bin|."""
    b_lo = 0 if bin_span[0] is None else bin_span[0]
    b_hi = SPAN_MAX if bin_span[1] is None else bin_span[1]
    q_lo = 0 if q_span[0] is None else q_span[0]
    q_hi = SPAN_MAX if q_span[1] is None else q_span[1]
    overlap = max(0, min(b_hi, q_hi) - max(b_lo, q_lo) + 1)
    width = b_hi - b_lo + 1
    return overlap / width if width > 0 else 0.0


def _axis_match(labels, spans, q_label, q_span, table_title, axis):
    """Match a query coordinate against a table axis.

    Returns [(index, fraction)]. Single-entry axes broadcast (fraction 1).
    Exact label match wins; otherwise spans on both sides are required."""
    if len(labels) == 1:
        return [(0, 1.0)]
    ql = str(q_label).strip()
    for i, lab in enumerate(labels):
        if str(lab).strip() == ql:
            return [(i, 1.0)]
    if not spans or q_span is None:
        raise ValueError(
            f"group_weighted: cannot match {axis} {q_label!r} in weights table "
            f"{table_title!r} - no exact label match and no spans declared "
            f"(the weights table needs {axis}_spans, and the target needs spans)")
    out = [(i, _span_frac(s, q_span)) for i, s in enumerate(spans) if s is not None]
    return [(i, f) for i, f in out if f > 0]


def _group_weight(wt, q_row_label, q_row_span, q_col_label, q_col_span):
    """Population weight for one output coordinate from one weights table:
    sum of the table's counts, proportionally attributed to the query cell."""
    rows = _axis_match(wt["row_labels"], wt.get("row_spans"), q_row_label,
                       q_row_span, wt.get("title", "?"), "row")
    cols = _axis_match(wt["col_labels"], wt.get("col_spans"), q_col_label,
                       q_col_span, wt.get("title", "?"), "col")
    w = 0.0
    for i, fr in rows:
        row = wt["cells"][i]
        for j, fc in cols:
            v = row[j] if j < len(row) else None
            if _num(v):
                w += v * fr * fc
    return w


def _percent_to_decimal(table):
    """Copy of the table with numeric cells (and totals) divided by 100.

    Division (not *0.01) so that e.g. 35.00 -> exactly the double 0.35 a
    human typing '0.35' produces."""
    t = dict(table)
    t["cells"] = [[v / 100 if _num(v) else v for v in row] for row in table["cells"]]
    for key in ("printed_row_totals", "printed_col_totals"):
        tv = table.get(key)
        t[key] = [v / 100 if _num(v) else v for v in tv] if tv else tv
    return t


def _overlap_years(t_span, s_span):
    """Integer-year overlap of two [lo, hi] spans (null = open end)."""
    t_lo = 0 if t_span[0] is None else t_span[0]
    t_hi = SPAN_MAX if t_span[1] is None else t_span[1]
    s_lo = 0 if s_span[0] is None else s_span[0]
    s_hi = SPAN_MAX if s_span[1] is None else s_span[1]
    return max(0, min(t_hi, s_hi) - max(t_lo, s_lo) + 1)


def zero_impossible(grid, row_spans, col_spans, cfg):
    """Zero the cells that cannot contain members under an entry-age floor:
    service low bound > age high bound - min_entry_age. Template convention
    adopted from the collectors' documented practice ('no one starts before
    20') - see assumption_register.md. cfg = {"age_axis": "rows"|"cols",
    "service_axis": ..., "min_entry_age": N}; spans keyed by target label."""
    min_age = cfg["min_entry_age"]
    age_on_rows = cfg["age_axis"] == "rows"
    # mode "upper" (collectors' convention): zero unless the WHOLE service
    # bucket is attainable at that age (svc upper bound > age - min_entry).
    # mode "lower": zero only if NO part is attainable (svc lower bound >).
    mode = cfg.get("mode", "upper")
    for i, r_lab in enumerate(grid["row_labels"]):
        for j, c_lab in enumerate(grid["col_labels"]):
            age_span = (row_spans or {}).get(r_lab) if age_on_rows else (col_spans or {}).get(c_lab)
            svc_span = (col_spans or {}).get(c_lab) if age_on_rows else (row_spans or {}).get(r_lab)
            if not age_span or not svc_span:
                continue
            age_hi = age_span[1]
            svc_bound = svc_span[1] if mode == "upper" else svc_span[0]
            if age_hi is None:
                continue
            if svc_bound is None:      # open service bin
                if mode == "upper":
                    continue           # open end never "fully attainable"-zeroed
                else:
                    svc_bound = svc_span[0]
            if svc_bound is not None and svc_bound > age_hi - min_age:
                grid["cells"][i][j] = 0.0
    return grid


def _sum_tables(source_tables, indices):
    """Cell-wise sum of same-shaped additive source tables."""
    if not indices:
        raise ValueError("derive=sum needs at least one source table index")
    base = source_tables[indices[0]]
    row_labels = base["row_labels"]
    col_labels = base["col_labels"]
    for i in indices[1:]:
        t = source_tables[i]
        if t["row_labels"] != row_labels or t["col_labels"] != col_labels:
            raise ValueError("derive=sum tables must have identical row/col labels")

    cells = []
    for r in range(len(row_labels)):
        out_row = []
        for c in range(len(col_labels)):
            vals = []
            for i in indices:
                row = source_tables[i]["cells"][r]
                vals.append(row[c] if c < len(row) else None)
            nums = [v for v in vals if _num(v)]
            out_row.append(sum(nums) if nums else ("*" if "*" in vals else None))
        cells.append(out_row)

    out = dict(base)
    out["title"] = " + ".join(source_tables[i].get("title", f"table {i}")
                              for i in indices)
    out["cells"] = cells
    out["printed_row_totals"] = None
    out["printed_col_totals"] = None
    return out


def execute(source_tables, row_map, col_map, derive=None, transpose=False,
            target_row_spans=None, target_col_spans=None, to_decimal=False,
            zero_impossible_cfg=None):
    """Return the derived canonical grid. Raises ValueError on bad specs.

    derive={"op": "ratio", "numerator_table": i, "denominator_table": j}
    aggregates BOTH tables with the same maps (additive ops only) and divides
    cell-wise (average = total$/count). derive={"op": "sum", "tables": [...]}
    sums same-shaped additive tables cell-wise before mapping.
    transpose: transpose the MAIN table before mapping (aux tables stay as
    printed; see module doc).
    target_*_spans: {target_label: [lo, hi]} template bin semantics, required
    by overlap_weighted entries (from targets.json, NOT model-declared).
    to_decimal: scale tables declaring values_unit=="percent" by 0.01."""
    prepped = []
    for k, t in enumerate(source_tables):
        if to_decimal and t.get("values_unit") == "percent":
            t = _percent_to_decimal(t)
        if transpose and k == 0:   # main table only; aux tables stay as printed
            t = _transpose_table(t)
        prepped.append(t)
    source_tables = prepped

    # overlap_weighted source sets are COMPUTED from the declared spans, not
    # trusted from the model (audit notes available via resolve_overlap_sources)
    row_map, _ = resolve_overlap_sources(row_map, target_row_spans)
    col_map, _ = resolve_overlap_sources(col_map, target_col_spans)

    if derive:
        op = derive.get("op")
        if op not in ("ratio", "sum"):
            raise ValueError(f"unknown derive op {op!r}")
        if op == "ratio":
            for m, kind in ((row_map, "row"), (col_map, "col")):
                for e in m:
                    if e["op"] in ("weighted_avg", "group_weighted", "ratio"):
                        raise ValueError(
                            f"{kind} {e['target']}: {e['op']} is not allowed in ratio "
                            "mode (both tables aggregate additively, then divide)")
            num = _grid(source_tables, derive["numerator_table"], row_map, col_map,
                        target_row_spans, target_col_spans)
            den = _grid(source_tables, derive["denominator_table"], row_map, col_map,
                        target_row_spans, target_col_spans)
            cells = []
            for nrow, drow in zip(num["cells"], den["cells"]):
                out_row = []
                for nv, dv in zip(nrow, drow):
                    if nv == "*" or dv == "*":
                        out_row.append("*")
                    elif _num(nv) and _num(dv) and dv != 0:
                        out_row.append(nv / dv)
                    else:
                        out_row.append(None)
                cells.append(out_row)
            out = {"row_labels": num["row_labels"],
                   "col_labels": num["col_labels"], "cells": cells}
        else:
            for m, kind in ((row_map, "row"), (col_map, "col")):
                for e in m:
                    if e["op"] in ("weighted_avg", "group_weighted"):
                        raise ValueError(
                            f"{kind} {e['target']}: {e['op']} is not allowed in sum "
                            "mode (sum mode is for additive tables)")
            summed = _sum_tables(source_tables, derive["tables"])
            out = _grid([summed], 0, row_map, col_map,
                        target_row_spans, target_col_spans)
    else:
        out = _grid(source_tables, 0, row_map, col_map,
                    target_row_spans, target_col_spans)
    if zero_impossible_cfg:
        out = zero_impossible(out, target_row_spans, target_col_spans,
                              zero_impossible_cfg)
    return out


def resolve_overlap_sources(map_entries, target_spans):
    """Recompute each overlap_weighted entry's source set from the POOLED span
    declarations. The model's genuine judgment is what each printed bin MEANS
    (its span); WHICH bins overlap which target is then pure arithmetic, so it
    is computed here rather than trusted from the model (live phx Ret_Rate
    run 2026-07-13: the model declared all spans correctly but mapped target
    '12-19' to '<15' only, missing its 15-24 overlap - a whole error class
    this removes). Returns (resolved_entries, audit_notes). Idempotent."""
    pool = {}
    for e in map_entries:
        if e.get("op") == "overlap_weighted":
            for s, sp in zip(e["sources"], e.get("source_spans") or []):
                key = str(s).strip()
                if key in pool and list(pool[key]) != list(sp):
                    raise ValueError(f"inconsistent spans declared for source bin "
                                     f"{s!r}: {pool[key]} vs {sp}")
                pool[key] = list(sp)
    if not pool or not target_spans:
        return map_entries, []

    out, notes = [], []
    for e in map_entries:
        if e.get("op") != "overlap_weighted" or e["target"] not in target_spans:
            out.append(e)
            continue
        t_span = target_spans[e["target"]]
        comp = [(lab, sp) for lab, sp in pool.items() if _overlap_years(t_span, sp) > 0]
        if not comp:
            notes.append(f"{e['target']}: pooled spans do not cover it; "
                         "keeping model-declared sources")
            out.append(e)
            continue
        declared = sorted(str(s).strip() for s in e["sources"])
        if declared != sorted(lab for lab, _ in comp):
            notes.append(f"{e['target']}: model declared sources {declared} but "
                         f"spans imply {sorted(l for l, _ in comp)}; using span-computed")
        out.append(dict(e, sources=[lab for lab, _ in comp],
                        source_spans=[sp for _, sp in comp]))
    return out, notes


def _overlap_combine(entry, vals, target_spans):
    """overlap_weighted: proportional-by-years blend of source bin values."""
    if not entry["sources"]:          # declared empty = no data for this target
        return None
    spans = entry.get("source_spans")
    if not spans or len(spans) != len(entry["sources"]):
        raise ValueError(f"{entry['target']}: overlap_weighted needs source_spans "
                         "aligned with sources")
    if not target_spans or entry["target"] not in target_spans:
        raise ValueError(f"{entry['target']}: no target span provided for "
                         "overlap_weighted (targets.json target_*_spans)")
    t_span = target_spans[entry["target"]]
    num, den = 0.0, 0.0
    for v, s_span in zip(vals, spans):
        if not _num(v):
            continue
        w = _overlap_years(t_span, s_span)
        if w > 0:
            num += v * w
            den += w
    return (num / den) if den else ("*" if "*" in vals else None)


def _col_span(table, c_label):
    """The declared span of one of a table's columns, if any."""
    spans = table.get("col_spans")
    if not spans:
        return None
    cl = str(c_label).strip()
    for lab, s in zip(table["col_labels"], spans):
        if str(lab).strip() == cl:
            return s
    return None


def _blend(entry, vals, weight_of):
    """Population-weighted blend: sum(w_s*v_s)/sum(w_s) over numeric sources."""
    wts = entry.get("weights_tables")
    if not isinstance(wts, list) or len(wts) != len(entry["sources"]):
        raise ValueError(f"{entry['target']}: group_weighted needs weights_tables "
                         "aligned with sources")
    num, den = 0.0, 0.0
    for s, v, k in zip(entry["sources"], vals, wts):
        if not _num(v):
            continue
        w = weight_of(s, k)
        num += v * w
        den += w
    return (num / den) if den else ("*" if "*" in vals else None)


def _stage1(source_tables, table, row_map, target_spans=None):
    """Row combination for one table -> {(target_row, source_col): value}."""
    ridx, cidx = _index(table["row_labels"]), _index(table["col_labels"])

    # how many share_even targets reference each source row (the split-open-
    # bucket rule, e.g. a printed '90 & Up' row split across 90-94/95-99/100+)
    share_n = {}
    for rm in row_map:
        if rm["op"] == "share_even":
            for s in rm["sources"]:
                share_n[s] = share_n.get(s, 0) + 1

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

        for c_label in table["col_labels"]:
            vals = [_get(table, ridx, cidx, s, c_label) for s in rm["sources"]]
            if op == "copy":
                if len(rm["sources"]) > 1:
                    raise ValueError(f"row {rm['target']}: copy with multiple sources")
                out = vals[0] if vals else None
            elif op == "share_even":
                if len(rm["sources"]) != 1:
                    raise ValueError(f"row {rm['target']}: share_even takes one source")
                v = vals[0]
                out = v / share_n[rm["sources"][0]] if _num(v) else v
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
            elif op == "overlap_weighted":
                out = _overlap_combine(rm, vals, target_spans)
            elif op == "group_weighted":
                q_row_span = (target_spans or {}).get(rm["target"])
                c_span = _col_span(table, c_label)
                out = _blend(rm, vals, lambda s, k: _group_weight(
                    source_tables[k], rm["target"], q_row_span, c_label, c_span))
            else:
                raise ValueError(f"unknown row op {op!r}")
            inter[(rm["target"], str(c_label).strip())] = out
    return inter


def _grid(source_tables, main_index, row_map, col_map,
          target_row_spans=None, target_col_spans=None):
    """Aggregate one source table through the row/col maps."""
    main = source_tables[main_index]

    # how many share_even targets reference each source column
    share_n = {}
    for cm in col_map:
        if cm["op"] == "share_even":
            for s in cm["sources"]:
                share_n[s] = share_n.get(s, 0) + 1

    # ---- stage 1: row combination -> intermediate[target_row][source_col]
    inter = _stage1(source_tables, main, row_map, target_row_spans)

    # row-aggregated weights grids for column weighted_avg. Weights are
    # counts, which are ADDITIVE: any weighted_avg row op degrades to sum
    # when applied to the weights table itself.
    w_inter = {}
    for cm in col_map:
        if cm["op"] == "weighted_avg":
            wt_i = cm.get("weights_table")
            if wt_i is None:
                raise ValueError(f"col {cm['target']}: weighted_avg needs weights_table")
            if wt_i not in w_inter:
                additive = [dict(rm, op=("sum" if rm["op"] == "weighted_avg"
                                         else rm["op"]), weights_table=None)
                            for rm in row_map]
                w_inter[wt_i] = _stage1(source_tables, source_tables[wt_i], additive)

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
            elif op == "ratio":
                if len(cm["sources"]) != 2:
                    raise ValueError(f"col {cm['target']}: ratio takes exactly two "
                                     "sources [numerator, denominator]")
                nv, dv = vals
                if nv == "*" or dv == "*":
                    out = "*"
                elif _num(nv) and _num(dv) and dv != 0:
                    out = nv / dv
                else:
                    out = None
            elif op == "weighted_avg":
                wgrid = w_inter[cm["weights_table"]]
                num, den = 0.0, 0.0
                for s, v in zip(cm["sources"], vals):
                    if not _num(v):
                        continue
                    w = wgrid.get((r, str(s).strip()))
                    if _num(w):
                        num += v * w
                        den += w
                out = (num / den) if den else ("*" if "*" in vals else None)
            elif op == "overlap_weighted":
                out = _overlap_combine(cm, vals, target_col_spans)
            elif op == "group_weighted":
                q_row_span = (target_row_spans or {}).get(r)
                out = _blend(cm, vals, lambda s, k: _group_weight(
                    source_tables[k], r, q_row_span, s, _col_span(main, s)))
            else:
                raise ValueError(f"unknown col op {op!r}")
            # declared monthly -> annual conversion (source prints monthly
            # benefit dollars, target wants annual): x12, adopted collector
            # convention - see assumption_register.md
            if cm.get("annualize_monthly") and _num(out):
                out = out * 12
            row_out.append(out)
        cells.append(row_out)

    return {"row_labels": row_labels, "col_labels": col_labels, "cells": cells}


def empty_grid(row_labels, col_labels):
    """All-null grid in the template shape - the honest derived result when
    Stage A declares the target unavailable in the document. Any transcribed
    evidence tables stay archived in extraction.json for later decisions."""
    return {"row_labels": list(row_labels), "col_labels": list(col_labels),
            "cells": [[None] * len(col_labels) for _ in row_labels]}


def totals_check(table, tol=0.5, rel_tol=1e-5):
    """Verify the transcription against the table's PRINTED totals (if any).

    A value placed one column off leaves row sums intact but breaks column
    sums - this is the automatic tripwire for the text-layer column-alignment
    failure mode. Returns a list of discrepancy strings (empty = consistent
    or no totals printed).

    Tolerance: max(tol, rel_tol*|printed|). The relative term absorbs the
    source's own rounding (AVs print integer dollars per cell but total the
    unrounded values, so printed totals can be off by a few dollars on
    hundreds of millions); a real column shift moves an entire cell value,
    orders of magnitude above it.
    """
    problems = []
    cells = table["cells"]

    def _bad(s, printed):
        return abs(s - printed) > max(tol, rel_tol * abs(printed))

    prt = table.get("printed_row_totals")
    if prt:
        for lab, row, printed in zip(table["row_labels"], cells, prt):
            if printed is None:
                continue
            s = sum(v for v in row if _num(v))
            if _bad(s, printed):
                problems.append(f"row {lab!r}: cells sum to {s!r} but printed total "
                                f"is {printed!r} (diff {s - printed!r})")

    pct = table.get("printed_col_totals")
    if pct:
        for j, (lab, printed) in enumerate(zip(table["col_labels"], pct)):
            if printed is None:
                continue
            s = sum(row[j] for row in cells if j < len(row) and _num(row[j]))
            if _bad(s, printed):
                problems.append(f"col {lab!r}: cells sum to {s!r} but printed total "
                                f"is {printed!r} (diff {s - printed!r})")

    return problems


def summarize(row_map, col_map, derive=None, transpose=False):
    """Human-readable one-liners for the declared operations."""
    lines = []
    if transpose:
        lines.append("transpose: source rows/cols swapped before mapping")
    if derive:
        if derive.get("op") == "ratio":
            lines.append(f"derive: ratio = t{derive.get('numerator_table')} / "
                         f"t{derive.get('denominator_table')} (cell-wise, after mapping)")
        elif derive.get("op") == "sum":
            lines.append("derive: sum = " +
                         " + ".join(f"t{i}" for i in derive.get("tables", [])) +
                         " (cell-wise, before mapping)")

    def _entry(kind, e):
        if e["op"] == "copy" and len(e["sources"]) == 1 and e["sources"][0] == e["target"]:
            return
        extra = ""
        if e["op"] == "weighted_avg":
            extra = f" weights=t{e.get('weights_table')}"
        elif e["op"] == "overlap_weighted":
            spans = e.get("source_spans") or []
            extra = " spans=" + ",".join(f"[{s[0]},{s[1]}]" for s in spans)
        elif e["op"] == "group_weighted":
            extra = " weights=" + ",".join(f"t{k}" for k in e.get("weights_tables", []))
        lines.append(f"{kind} {e['target']!r} <- {e['op']}({', '.join(e['sources'])}){extra}")

    for rm in row_map:
        _entry("row", rm)
    for cm in col_map:
        _entry("col", cm)
    return lines or ["(pure relabeling, no transformations)"]
