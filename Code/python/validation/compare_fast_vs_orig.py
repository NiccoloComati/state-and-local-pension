"""
Compare fast Python outputs (062026_fast) against original Python outputs (062026_py).
Checks that optimizations produce bit-identical simulation results.

Usage:
  python "Cluster Code/cluster_062026/Python Code/compare_fast_vs_orig.py"
  python "Cluster Code/cluster_062026/Python Code/compare_fast_vs_orig.py" --orig 062026_py --fast 062026_fast --output Results/Runs/062026_fast/_compare_fast_vs_orig.csv
"""
from __future__ import annotations
import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# validation/ → Python Code/ → cluster_062026/ → Cluster Code/ → State Pension Model/
ROOT = Path(__file__).resolve().parents[3]


def load_pkl(path: Path) -> dict:
    with path.open("rb") as f:
        return pickle.load(f)


MATRIX_KEYS = ["AAL", "NormalCost", "cash_outflows", "cash_inflows"]
SCALAR_KEYS = ["Model_AAL", "CAFR_AAL", "Percent_difference",
               "Inflation", "rf", "discountrate"]


def compare_plan(plan: str, orig_dir: Path, fast_dir: Path) -> list[dict]:
    orig_path = orig_dir / plan / f"{plan}_detAL_{orig_dir.name}.pkl"
    fast_path = fast_dir / plan / f"{plan}_detAL_{fast_dir.name}.pkl"

    if not orig_path.exists():
        return [{"plan": plan, "object": "*", "status": "missing_orig",
                 "max_abs": float("nan"), "max_rel": float("nan")}]
    if not fast_path.exists():
        return [{"plan": plan, "object": "*", "status": "missing_fast",
                 "max_abs": float("nan"), "max_rel": float("nan")}]

    orig = load_pkl(orig_path)
    fast = load_pkl(fast_path)
    rows = []

    for key in MATRIX_KEYS:
        if key not in orig or key not in fast:
            rows.append({"plan": plan, "object": key, "status": "missing_key",
                         "max_abs": float("nan"), "max_rel": float("nan")})
            continue
        a = np.asarray(orig[key], dtype=float)
        b = np.asarray(fast[key], dtype=float)
        if a.shape != b.shape:
            rows.append({"plan": plan, "object": key, "status": "shape_mismatch",
                         "max_abs": float("nan"), "max_rel": float("nan")})
            continue
        diff   = np.abs(a - b)
        rel    = diff / (np.abs(a) + 1e-12)
        max_abs = float(np.nanmax(diff))
        max_rel = float(np.nanmax(rel))
        status  = "ok" if max_abs == 0.0 else "mismatch"
        rows.append({"plan": plan, "object": key, "status": status,
                     "max_abs": max_abs, "max_rel": max_rel})

    for key in SCALAR_KEYS:
        v_orig = orig.get(key)
        v_fast = fast.get(key)
        if v_orig is None or v_fast is None:
            continue
        try:
            diff   = abs(float(v_orig) - float(v_fast))
            status = "ok" if diff == 0.0 else "mismatch"
            rows.append({"plan": plan, "object": key, "status": status,
                         "max_abs": diff, "max_rel": float("nan")})
        except (TypeError, ValueError):
            pass

    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orig",   default="062026_py")
    parser.add_argument("--fast",   default="062026_fast")
    parser.add_argument("--output", default=None)
    parser.add_argument("--plans",  default="all")
    args = parser.parse_args()

    orig_dir = ROOT / "Results" / "Runs" / args.orig
    fast_dir = ROOT / "Results" / "Runs" / args.fast

    if args.plans == "all":
        plan_list_file = ROOT / "Code" / "python" / "config" / "plans_38.txt"
        plans = [l.strip() for l in plan_list_file.read_text().splitlines()
                 if l.strip() and not l.startswith("#") and l.strip() != "MA50"]
    else:
        plans = [p.strip() for p in args.plans.split(",")]

    all_rows = []
    for plan in plans:
        all_rows.extend(compare_plan(plan, orig_dir, fast_dir))

    df = pd.DataFrame(all_rows)

    print(f"\nComparing {args.orig} (original) vs {args.fast} (fast)\n")
    print("Status counts:")
    print(df["status"].value_counts().to_string())

    mismatches = df[df["status"] == "mismatch"]
    if len(mismatches):
        print(f"\n{len(mismatches)} mismatches:")
        print(mismatches[["plan", "object", "max_abs", "max_rel"]].to_string(index=False))
    else:
        print("\nAll outputs identical between original and fast versions.")

    out_path = args.output or str(fast_dir / "_compare_fast_vs_orig.csv")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
