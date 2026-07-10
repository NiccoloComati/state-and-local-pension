"""Evaluation harness: load a ground-truth workbook sheet as a canonical grid
and score a candidate grid against it.

Canonical grid = {"row_labels": [str], "col_labels": [str], "cells": [[number|"*"|None]]}

No ML anywhere. Any extractor (text+LLM, VLM, TATR) is scored the same way.
"""
import os
import shutil
import tempfile

import openpyxl

# Rows whose first cell starts with one of these end the data block
# (learned from the phx tier sheets, which carry TOTAL/CALCULATIONS blocks).
STOP_MARKERS = ("TOTAL", "CALCULATIONS", "NOTES", "SOURCE")


def load_truth(workbook_path, sheet_name):
    """Read a collection-workbook sheet into a canonical grid.

    Layout assumption (city collection template): first row = header
    (A1 = corner label, B1.. = column labels), column A = row labels,
    data block ends at the first blank/marker row.

    Copies the workbook to a temp file first (OneDrive/Excel locks).
    """
    tmp = os.path.join(tempfile.gettempdir(), "_harness_copy.xlsx")
    shutil.copy(workbook_path, tmp)
    wb = openpyxl.load_workbook(tmp, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
        try:
            os.remove(tmp)
        except OSError:
            pass

    if not rows:
        raise ValueError(f"sheet {sheet_name} is empty")

    header = rows[0]
    col_labels = [_label(v) for v in header[1:] if v is not None]
    ncols = len(col_labels)

    row_labels, cells = [], []
    for r in rows[1:]:
        first = r[0]
        if first is None or (isinstance(first, str) and not first.strip()):
            break
        if isinstance(first, str) and first.strip().upper().startswith(STOP_MARKERS):
            break
        row_labels.append(_label(first))
        cells.append([_cell(v) for v in r[1:ncols + 1]])

    return {"row_labels": row_labels, "col_labels": col_labels, "cells": cells}


def _label(v):
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def _cell(v):
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if s in ("-", "–", "—"):  # printed dash = empty cell
            return None
        if s == "*":
            return "*"
        try:
            return float(s)
        except ValueError:
            return s
    if isinstance(v, (int, float)):
        return float(v)
    return str(v)


def score(truth, cand, close_rel=0.01, zero_equals_empty=False):
    """Cell-by-cell comparison of candidate grid vs truth grid.

    Alignment is positional; label mismatches are reported separately.
    zero_equals_empty: treat 0 and null as equivalent (sensible for COUNT
    targets, where collectors variously typed 0 or left blanks for "no
    members"; NOT for rate targets, where 0 is a real value).
    Returns a dict with counts, accuracy, and a capped mismatch list.
    """
    report = {
        "shape_truth": (len(truth["cells"]), len(truth["col_labels"])),
        "shape_cand": (len(cand.get("cells", [])),
                       len(cand.get("col_labels", []))),
        "label_mismatches": [],
        "exact": 0, "close": 0, "wrong": 0,
        "missing_in_cand": 0, "extra_in_cand": 0, "star_ok": 0,
        "mismatches": [],
    }

    for kind in ("row_labels", "col_labels"):
        t, c = truth[kind], cand.get(kind, [])
        for i in range(max(len(t), len(c))):
            tv = t[i] if i < len(t) else "(none)"
            cv = c[i] if i < len(c) else "(none)"
            if _norm(tv) != _norm(cv):
                report["label_mismatches"].append(f"{kind}[{i}]: truth={tv!r} cand={cv!r}")

    nrows = len(truth["cells"])
    ncols = len(truth["col_labels"])
    for i in range(nrows):
        for j in range(ncols):
            t = truth["cells"][i][j] if j < len(truth["cells"][i]) else None
            c = None
            if i < len(cand.get("cells", [])) and j < len(cand["cells"][i]):
                c = cand["cells"][i][j]

            if t is None and c is None:
                continue
            if zero_equals_empty and \
               (t is None or (_isnum(t) and t == 0)) and \
               (c is None or (_isnum(c) and c == 0)):
                if t is not None:      # truth had an explicit 0: count the match
                    report["exact"] += 1
                continue
            if t is None and c is not None:
                report["extra_in_cand"] += 1
                _mm(report, i, j, t, c, truth)
            elif t is not None and c is None:
                report["missing_in_cand"] += 1
                _mm(report, i, j, t, c, truth)
            elif t == "*" or c == "*":
                if t == c:
                    report["star_ok"] += 1
                else:
                    report["wrong"] += 1
                    _mm(report, i, j, t, c, truth)
            else:
                tf, cf = float(t), float(c)
                if tf == cf or (tf != 0 and abs(cf - tf) / abs(tf) < 1e-9):
                    report["exact"] += 1
                elif tf != 0 and abs(cf - tf) / abs(tf) < close_rel:
                    report["close"] += 1
                    _mm(report, i, j, t, c, truth)
                else:
                    report["wrong"] += 1
                    _mm(report, i, j, t, c, truth)

    filled = sum(1 for row in truth["cells"] for v in row if v is not None)
    scored = report["exact"] + report["star_ok"]
    report["truth_filled_cells"] = filled
    report["accuracy"] = round(scored / filled, 4) if filled else None
    return report


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _norm(s):
    return str(s).strip().lower().replace(" ", "")


def _mm(report, i, j, t, c, truth, cap=25):
    if len(report["mismatches"]) < cap:
        rl = truth["row_labels"][i] if i < len(truth["row_labels"]) else i
        cl = truth["col_labels"][j] if j < len(truth["col_labels"]) else j
        report["mismatches"].append(f"[age {rl} x svc {cl}] truth={t!r} cand={c!r}")


def print_report(report):
    print(f"  truth shape {report['shape_truth']}  candidate shape {report['shape_cand']}")
    if report["label_mismatches"]:
        print(f"  label mismatches: {len(report['label_mismatches'])}")
        for m in report["label_mismatches"][:6]:
            print(f"    {m}")
    print(f"  exact={report['exact']}  close(<1%)={report['close']}  wrong={report['wrong']}"
          f"  missing={report['missing_in_cand']}  extra={report['extra_in_cand']}"
          f"  star_ok={report['star_ok']}")
    print(f"  ACCURACY (exact+star / {report['truth_filled_cells']} filled truth cells):"
          f" {report['accuracy']}")
    if report["mismatches"]:
        print("  mismatches:")
        for m in report["mismatches"]:
            print(f"    {m}")
