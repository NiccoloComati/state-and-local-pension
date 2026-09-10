"""Build the counterfactual tier workbooks from the baseline one.

The tier workbook holds every plan's benefit rules, up to six tiers each. These
counterfactuals change those rules and nothing else, so each one is a normal model
INPUT, produced by this script and passed to the engine with `--tier-file`.

    python settings/build_counterfactual_tier_files.py           # write them
    python settings/build_counterfactual_tier_files.py --check   # verify, write nothing

Produces, in Data/Common/states/ alongside the source:

  planchanges_noreform2007_2022_clean.xlsx
      Every tier starting after 2007-01-01 takes the benefit rules of the newest
      tier that existed before then. Answers "had the post-2007 reforms not
      happened". Feeds Lenney figures 11 and 12.

  planchanges_cola0_2022_clean.xlsx
      Every tier's COLA set to zero.

  planchanges_colainflation_2022_clean.xlsx
      Every tier's COLA set to that plan's own inflation assumption, read from the
      baseline run so it matches what the engine actually used rather than
      re-deriving the PPD fallback chain.

  The two COLA files feed Lenney figure 4.

TWO THINGS THAT WILL BREAK IT IF CHANGED.

The sheet must be named `in`. engine/run_plan.py does
`pd.read_excel(tier_file, sheet_name='in')`, and pandas' default sheet name makes
every plan fail at load.

`startdate` is never touched. It decides which members sit in which tier, so the
counterfactual has to keep the same people in the same tiers and change only the
promise they accrue under. Rewriting start dates would move members between tiers
and measure something else entirely.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SHEET = "in"
CUT = pd.Timestamp("2007-01-01")

# The columns that say how generous a tier is. Deliberately excludes startdate.
BENEFIT_PARAMS = ["benefitfactor", "cola", "our_cola", "type", "compounded",
                  "nr", "er", "vesting", "maxsal", "yrsal", "ercont", "eecont"]
COLA_COLS = [f"cola{k}" for k in range(1, 7)]

SOURCE = "planchanges_main_2022_clean.xlsx"
INFLATION_RUN = "20260908_1"      # where per-plan inflation is read from


def paths() -> tuple[Path, Path]:
    here = Path(__file__).resolve().parent            # Code/python/settings
    root = here.parent.parent.parent                  # project root
    return root, root / "Data" / "Common" / "states"


def no_reform(t: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    out = t.copy()
    n = 0
    for i, row in t.iterrows():
        dates = [pd.to_datetime(row[f"startdate{k}"], errors="coerce") for k in range(1, 7)]
        pre = [k for k in range(1, 7) if pd.notna(dates[k - 1]) and dates[k - 1] <= CUT]
        post = [k for k in range(1, 7) if pd.notna(dates[k - 1]) and dates[k - 1] > CUT]
        if not pre or not post:
            continue
        donor = max(pre)
        for k in post:
            for p in BENEFIT_PARAMS:
                out.at[i, f"{p}{k}"] = row[f"{p}{donor}"]
        n += 1
    return out, n


def cola_zero(t: pd.DataFrame) -> pd.DataFrame:
    out = t.copy()
    for c in COLA_COLS:
        out[c] = 0.0
    return out


def cola_inflation(t: pd.DataFrame, root: Path) -> tuple[pd.DataFrame, dict]:
    runs = root / "Results" / "Runs" / INFLATION_RUN
    if not runs.exists():
        raise FileNotFoundError(
            f"{runs} not found; it supplies each plan's inflation assumption. "
            "Point INFLATION_RUN at a run that exists.")
    infl = {}
    for d in runs.iterdir():
        if not d.is_dir() or not re.fullmatch(r"[A-Z]{2}\d+", d.name):
            continue
        s = pd.read_parquet(next(iter(d.glob("*_parquet"))) / "scalars.parquet")
        infl[d.name] = float(dict(zip(s["name"], s["value"]))["Inflation"])

    out = t.copy()
    missing = []
    for i, row in t.iterrows():
        plan = str(row["planid"]).split("_")[0]
        if plan not in infl:
            missing.append(plan)
            continue
        for c in COLA_COLS:
            out.at[i, c] = infl[plan]
    if missing:
        raise ValueError(f"no inflation value for {missing}; cannot build this workbook")
    return out, infl


def write(df: pd.DataFrame, path: Path, source: pd.DataFrame) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name=SHEET, index=False)
    back = pd.read_excel(path, sheet_name=SHEET, header=0)   # exactly as the engine reads it
    assert list(back.columns) == list(source.columns), f"{path.name}: columns changed"
    assert len(back) == len(source), f"{path.name}: row count changed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what would change and verify the existing files; write nothing")
    a = ap.parse_args()

    root, common = paths()
    src = common / SOURCE
    if not src.exists():
        raise FileNotFoundError(f"{src} not found")
    t = pd.read_excel(src, sheet_name=SHEET)

    nr, n_plans = no_reform(t)
    z = cola_zero(t)
    w, infl = cola_inflation(t, root)

    nr_cols = [f"nr{k}" for k in range(1, 7)]
    changed = int((t[nr_cols].to_numpy(float) != nr[nr_cols].to_numpy(float)).sum())
    same_dates = bool((t[[f"startdate{k}" for k in range(1, 7)]].astype(str)
                       == nr[[f"startdate{k}" for k in range(1, 7)]].astype(str)).all().all())

    print(f"source: {src.name}  ({len(t)} plans)")
    print(f"  no-reform: {n_plans} plans have post-2007 tiers rewritten, "
          f"{changed} threshold-age cells changed, startdates untouched: {same_dates}")
    print(f"  cola0:     every tier COLA -> 0")
    print(f"  colainf:   every tier COLA -> plan inflation, "
          f"{min(infl.values()):.4f}-{max(infl.values()):.4f} across {len(infl)} plans")

    targets = [(nr, "planchanges_noreform2007_2022_clean.xlsx"),
               (z, "planchanges_cola0_2022_clean.xlsx"),
               (w, "planchanges_colainflation_2022_clean.xlsx")]

    if a.check:
        for df, name in targets:
            p = common / name
            if not p.exists():
                print(f"  MISSING {name}")
                continue
            on_disk = pd.read_excel(p, sheet_name=SHEET, header=0)
            gen = df.reset_index(drop=True)
            # Compared value by value rather than with DataFrame.equals, which also
            # compares dtypes: a column that round-trips through Excel as float64
            # against an int64 in memory is reported as different when nothing is.
            bad = [c for c in gen.columns
                   if c not in on_disk.columns
                   or (not np.allclose(on_disk[c].to_numpy(float), gen[c].to_numpy(float),
                                       rtol=0, atol=1e-12, equal_nan=True)
                       if pd.api.types.is_numeric_dtype(gen[c])
                       and pd.api.types.is_numeric_dtype(on_disk[c])
                       else not on_disk[c].astype(str).equals(gen[c].astype(str)))]
            print(f"  {'OK      ' if not bad else 'DIFFERS '}{name}"
                  + (f"  columns: {bad}" if bad else ""))
        return 0

    for df, name in targets:
        write(df, common / name, t)
        print(f"  wrote {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
