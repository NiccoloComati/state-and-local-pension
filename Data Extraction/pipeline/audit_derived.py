"""Audit every DERIVED grid for values that cannot be right, without the PDF.

Why this exists: the 2026-07-27 sweep scored chi_ff and chi_gen Retirement as
"production" while their AverageBenefit column held 4.44, 12.91, 15.88 - a
dollars/dollars ratio. sf shipped 1.0 in every row, mil 12.0. Nothing caught it
because the contract was satisfied and no workbook existed to score against.
The numbers themselves were the evidence, and nobody was reading them.

So: run a plausibility pass over the OUTPUT of every cell. Every check here is
PDF-independent - it uses the target's own declared unit and internal
consistency, never a workbook - which is what makes it safe to run over the
whole corpus and trust the hits. A finding is not proof of error; it is a cell
worth opening the PDF for, ranked so the worst come first.

Usage:
  python pipeline/audit_derived.py                 # newest run per (plan,target)
  python pipeline/audit_derived.py --all-runs      # every archived run
  python pipeline/audit_derived.py --csv out.csv
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RUNS = os.path.join(os.path.dirname(HERE), "runs")

# severity: 3 = cannot be right, 2 = almost certainly wrong, 1 = worth a look
SEV = {3: "IMPOSSIBLE", 2: "SUSPECT", 1: "NOTE"}

# Plausible bands for money columns, in ANNUAL dollars. Deliberately wide: the
# point is to catch 4.44 and 12.0, not to police a $19k part-timer.
WAGE_LO, WAGE_HI = 8_000, 500_000
BENEFIT_LO, BENEFIT_HI = 1_200, 400_000
# A mortality rate at these ages cannot sanely exceed this.
MORT_YOUNG_MAX = 0.01      # q at age 25
MORT_MID_MAX = 0.05        # q at age 55


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _vals(grid):
    return [v for row in grid.get("cells", []) if isinstance(row, list)
            for v in row if _num(v)]


def _col(grid, j):
    return [row[j] for row in grid.get("cells", [])
            if isinstance(row, list) and j < len(row)]


def _finding(out, sev, code, msg):
    out.append((sev, code, msg))


# ---------------------------------------------------------------- generic ---
def check_generic(grid, out, broadcast=None):
    cells = grid.get("cells") or []
    total = sum(len(r) for r in cells if isinstance(r, list))
    nums = _vals(grid)
    if total and not nums:
        _finding(out, 3, "empty-grid",
                 f"all {total} cells are null - nothing was derived")
        return
    if not nums:
        return

    fill = len(nums) / total if total else 0
    if 0 < fill < 0.15:
        _finding(out, 1, "sparse",
                 f"only {len(nums)}/{total} cells populated ({fill:.0%})")

    # a whole column identical across >=3 rows is the fingerprint of a
    # degenerate ratio (sf shipped 1.0 everywhere, mil 12.0). 0 and 1 are
    # EXCLUDED: on a rate sheet a column of zeros is the impossibility
    # convention and a column of ones is "everyone retires by this age",
    # both legitimate - flagging them buried the real hits in noise.
    # A `broadcast` grid is CONSTANT BY DESIGN along the axis the document does
    # not measure: axis="age" repeats one service-based rate down every age row,
    # so every column is identical and this check fires on all of them. Round 3
    # produced 57 such false positives on Sep_Rate alone, burying the real hits.
    # Only skip the axis the broadcast actually fills.
    bcast_axis = (broadcast or {}).get("axis")
    if bcast_axis != "age":
        for j, lab in enumerate(grid.get("col_labels") or []):
            col = [v for v in _col(grid, j) if _num(v)]
            if len(col) >= 3 and len(set(col)) == 1 and col[0] not in (0, 1):
                _finding(out, 2, "constant-column",
                         f"column {lab!r} is {col[0]!r} in all {len(col)} populated "
                         "rows - a ratio of a column by itself looks like this")

    if any(v < 0 for v in nums):
        neg = [v for v in nums if v < 0]
        _finding(out, 3, "negative",
                 f"{len(neg)} negative value(s), min {min(neg)!r}")


# ------------------------------------------------------------ per target ---
def check_probability(grid, out, name, zero_impossible=False):
    nums = _vals(grid)
    over = [v for v in nums if v > 1]
    if over:
        _finding(out, 3, "prob>1",
                 f"{len(over)} value(s) above 1.0 (max {max(over):,.4g}) - a "
                 "probability cannot exceed 1; a missing values_unit "
                 "(percent / per_1000) looks exactly like this")
    near = [v for v in nums if 1 >= v > 0.9]
    if near and name != "Ret_Rate":     # Ret_Rate legitimately hits 1.0
        _finding(out, 1, "prob-near-1",
                 f"{len(near)} value(s) in (0.9, 1.0]")
    if nums and all(v == 0 for v in nums):
        # On a zero_impossible target the executor writes 0.0 into the
        # age/service combinations that cannot occur. If those are the ONLY
        # populated cells, the grid carries no actual rate - it is an empty
        # result wearing a convention, not a set of zero rates.
        if zero_impossible:
            _finding(out, 3, "no-rate-derived",
                     f"the only populated cells are the {len(nums)} "
                     "impossibility zeros written by the executor; every real "
                     "age x service cell is null - no rate was derived")
        else:
            _finding(out, 3, "all-zero", "every populated value is 0")


def check_mortality(grid, out):
    check_probability(grid, out, "Avg_Mort")
    by_age = {}
    for lab, row in zip(grid.get("row_labels") or [], grid.get("cells") or []):
        if isinstance(row, list) and row and _num(row[0]):
            m = re.match(r"^\d+$", str(lab).strip())
            if m:
                by_age[int(lab)] = row[0]
    if not by_age:
        return
    # Probe every young/mid age present, not two fixed ones: dal maps age 25 to
    # a label its table does not print, so a single q(25) probe saw None and
    # said nothing while q(20) sat at 0.035 - the table transcribed was
    # "Disability Mortality Rate", the wrong population entirely.
    for lo, hi, cap in ((0, 30, MORT_YOUNG_MAX), (31, 60, MORT_MID_MAX)):
        band = {a: q for a, q in by_age.items() if lo <= a <= hi and q > cap}
        if band:
            a = min(band)
            _finding(out, 2, "mortality-level",
                     f"q({a}) = {band[a]:,.5g} at age {a}, above the plausible "
                     f"{cap:g} ({len(band)} age(s) in {lo}-{hi} exceed it) - "
                     "wrong population (disability/disabled-life table), a "
                     "missing values_unit, or a bad blend")
    # mortality must rise with age; count how badly it fails
    ages = sorted(by_age)
    drops = [(a, b) for a, b in zip(ages, ages[1:]) if by_age[b] < by_age[a]]
    if len(drops) > len(ages) * 0.25:
        _finding(out, 2, "mortality-nonmonotone",
                 f"q falls with age at {len(drops)} of {len(ages) - 1} steps - "
                 "a mortality curve should rise almost everywhere")
    if len(ages) >= 2 and by_age[ages[-1]] < by_age[ages[0]]:
        _finding(out, 3, "mortality-inverted",
                 f"q({ages[-1]}) = {by_age[ages[-1]]:,.5g} is BELOW "
                 f"q({ages[0]}) = {by_age[ages[0]]:,.5g}")


def check_money(grid, out, col_label, lo, hi, what):
    labels = grid.get("col_labels") or []
    if col_label not in labels:
        return
    j = labels.index(col_label)
    col = [v for v in _col(grid, j) if _num(v)]
    if not col:
        return
    low = [v for v in col if 0 < v < lo]
    high = [v for v in col if v > hi]
    if low:
        _finding(out, 3, "money-too-low",
                 f"{what}: {len(low)} value(s) below ${lo:,} (min "
                 f"${min(low):,.2f}) - not a plausible annual figure. A ratio "
                 "whose denominator is not a headcount, or monthly dollars "
                 "reported as annual, lands here")
    if high:
        _finding(out, 3, "money-too-high",
                 f"{what}: {len(high)} value(s) above ${hi:,} (max "
                 f"${max(high):,.0f}) - a TOTAL reported as an average lands here")


def check_counts(grid, out, col_label=None):
    labels = grid.get("col_labels") or []
    if col_label and col_label in labels:
        vals = [v for v in _col(grid, labels.index(col_label)) if _num(v)]
    else:
        vals = _vals(grid)
    if not vals:
        return
    # counts may be fractional after a documented even split, but a grid where
    # MOST values are fractional is not a headcount
    frac = [v for v in vals if abs(v - round(v)) > 1e-6]
    if len(frac) > len(vals) * 0.5:
        _finding(out, 2, "counts-fractional",
                 f"{len(frac)}/{len(vals)} count values are not whole numbers")


CHECKS = {
    "Age_Serv_Num":  lambda g, o, z: check_counts(g, o),
    "Ret_Rate":      lambda g, o, z: check_probability(g, o, "Ret_Rate", z),
    "Sep_Rate":      lambda g, o, z: check_probability(g, o, "Sep_Rate", z),
    "Avg_Mort":      lambda g, o, z: check_mortality(g, o),
    "Retirement":    lambda g, o, z: (
        check_money(g, o, "AverageBenefit", BENEFIT_LO, BENEFIT_HI,
                    "average benefit"),
        check_counts(g, o, "Number")),
}


def check_wage_grid(grid, out):
    """Age_Serv_Wage has no single money column - every cell is an average."""
    vals = _vals(grid)
    low = [v for v in vals if 0 < v < WAGE_LO]
    high = [v for v in vals if v > WAGE_HI]
    if low:
        _finding(out, 3, "money-too-low",
                 f"average salary: {len(low)} cell(s) below ${WAGE_LO:,} (min "
                 f"${min(low):,.2f}) - monthly dollars reported as annual, or a "
                 "ratio whose denominator is not a headcount, lands here")
    if high:
        _finding(out, 3, "money-too-high",
                 f"average salary: {len(high)} cell(s) above ${WAGE_HI:,} (max "
                 f"${max(high):,.0f}) - salary TOTALS reported as averages land here")


CHECKS["Age_Serv_Wage"] = lambda g, o, z: check_wage_grid(g, o)


# ------------------------------------------------------------------ walk ---
def discover(all_runs=False):
    """(plan, target, run_dir) for each archived run holding a derived grid.
    Default keeps only the NEWEST run per (plan, target) - auditing superseded
    runs just re-reports bugs already fixed."""
    targets = json.load(open(os.path.join(HERE, "targets.json"),
                             encoding="utf-8"))
    names = [t for t in targets if t != "_comment"]
    found = {}
    for parent, dirs, files in os.walk(RUNS):
        if "derived.json" not in files:
            continue
        base = os.path.basename(parent)
        tgt = next((t for t in names if f"_{t}_" in base), None)
        if not tgt:
            continue
        plan = base.split(f"_{t if False else tgt}_")[0]
        stamp = base.rsplit("_", 2)[-2:]
        key = (plan, tgt, base) if all_runs else (plan, tgt)
        prev = found.get(key)
        if prev is None or base > os.path.basename(prev):
            found[key] = parent
    return targets, sorted((k[0], k[1], v) for k, v in found.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-runs", action="store_true",
                    help="audit every archived run, not just the newest per cell")
    ap.add_argument("--csv", help="also write findings here")
    ap.add_argument("--min-sev", type=int, default=1, choices=(1, 2, 3))
    args = ap.parse_args()

    targets, cells = discover(args.all_runs)
    rows, n_clean, n_cells, n_unavail = [], 0, 0, 0

    for plan, tgt, run in cells:
        try:
            with open(os.path.join(run, "derived.json"), encoding="utf-8") as fh:
                grid = json.load(fh)
        except Exception as e:
            rows.append((3, plan, tgt, "unreadable", f"derived.json: {e}", run))
            continue
        n_cells += 1
        # A cell Stage A declared UNAVAILABLE has an all-null grid by design -
        # that is the honest answer when the document does not publish the
        # target, not a failure. Count them, do not flag them.
        try:
            with open(os.path.join(run, "extraction.json"), encoding="utf-8") as fh:
                extraction = json.load(fh)
            unavailable = bool(extraction.get("unavailable"))
        except Exception:
            extraction, unavailable = {}, False
        if unavailable:
            n_unavail += 1
            continue
        out = []
        check_generic(grid, out, broadcast=extraction.get("broadcast"))
        fn = CHECKS.get(tgt)
        zero_imp = bool((targets.get(tgt) or {}).get("zero_impossible_cells"))
        if fn and not any(c == "empty-grid" for _, c, _ in out):
            fn(grid, out, zero_imp)
        if not out:
            n_clean += 1
        for sev, code, msg in out:
            if sev >= args.min_sev:
                rows.append((sev, plan, tgt, code, msg, run))

    rows.sort(key=lambda r: (-r[0], r[1], r[2]))
    n_checked = n_cells - n_unavail
    print(f"audited {n_cells} cells ({'all runs' if args.all_runs else 'newest run each'}): "
          f"{n_unavail} declared unavailable (skipped), {n_checked} checked -> "
          f"{n_clean} clean, {n_checked - n_clean} with findings\n")
    cur = None
    for sev, plan, tgt, code, msg, run in rows:
        if sev != cur:
            cur = sev
            print(f"\n===== {SEV[sev]} =====")
        print(f"  {plan:10s} {tgt:15s} [{code}]")
        print(f"      {msg}")
        print(f"      {os.path.relpath(run, os.path.dirname(HERE))}")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["severity", "plan", "target", "code", "finding", "run_dir"])
            for sev, plan, tgt, code, msg, run in rows:
                w.writerow([SEV[sev], plan, tgt, code, msg,
                            os.path.relpath(run, os.path.dirname(HERE))])
        print(f"\nwrote {len(rows)} findings to {args.csv}")


if __name__ == "__main__":
    main()
