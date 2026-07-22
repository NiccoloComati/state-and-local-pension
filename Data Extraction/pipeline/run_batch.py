"""Breadth-first sweep: run every plan x target, capture artifacts, emit an
aggregate report. This is the machinery for the open-weights corpus pass -
run the whole set, read the failure map, then fix instructions/tools in bulk
(instead of the cautious one-at-a-time grind that suited paid API calls).

Local inference is free and fast, so we run wide and lean on automatic
verifiers: the score where a filled workbook exists, and the printed-totals
reconciliation + a PPD cross-check everywhere else. Nothing here adjudicates -
it flags what needs a human's eyes, ranked.

Usage (from "Data Extraction", with the vLLM env vars set - see
engaging_beta/runbook.md):
    python pipeline/run_batch.py                       # all plans x all targets
    python pipeline/run_batch.py --plans phx,chi_pol   # subset of plans
    python pipeline/run_batch.py --targets Age_Serv_Num,Retirement
    python pipeline/run_batch.py --quiet               # only the summary table

Writes runs/_batch_<stamp>/summary.json and summary.csv, and prints a table.
Each cell's per-run artifacts live in the usual runs/<plan>_<target>_<ts>/.
"""
import argparse
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_test   # noqa: E402  (PLANS, run_one, load_targets, target_names, DATA_EXTRACTION)


def _fmt(o):
    """One compact status token per cell for the printed matrix."""
    st = o["status"]
    if st == "crash":
        return "CRASH"
    if st == "unavailable":
        return "unavail"
    if st == "production":
        return f"prod/{o['totals']}"          # no score; totals status is the signal
    sc = o["score"]
    tag = f"{sc:.3f}" if sc is not None else "?"
    if o["totals"] == "suspect":
        tag += "!"                            # score exists but transcription suspect
    return tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plans", help="comma-separated subset (default: all)")
    ap.add_argument("--targets", help="comma-separated subset (default: all)")
    ap.add_argument("--quiet", action="store_true", help="suppress per-run logs")
    args = ap.parse_args()

    targets = run_test.load_targets()
    all_targets = run_test.target_names(targets)
    plans = args.plans.split(",") if args.plans else sorted(run_test.PLANS)
    tgts = args.targets.split(",") if args.targets else all_targets
    for p in plans:
        if p not in run_test.PLANS:
            sys.exit(f"unknown plan {p!r}; known: {sorted(run_test.PLANS)}")
    for t in tgts:
        if t not in all_targets:
            sys.exit(f"unknown target {t!r}; known: {all_targets}")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(run_test.DATA_EXTRACTION, "runs", f"_batch_{stamp}")
    os.makedirs(batch_dir, exist_ok=True)

    outcomes = []
    total = len(plans) * len(tgts)
    n = 0
    for plan in plans:
        for target in tgts:
            n += 1
            print(f"\n===== [{n}/{total}] {plan} / {target} "
                  + "=" * 30, flush=True)
            try:
                o = run_test.run_one(plan, target, targets, verbose=not args.quiet)
            except Exception as e:                    # noqa: BLE001 - never abort the sweep
                o = {"plan": plan, "target": target, "status": "crash",
                     "crash": f"harness error: {str(e)[:200]}", "score": None,
                     "totals": None, "n_tables": None, "n_attempts": None,
                     "run_dir": None, "exact": None, "close": None, "wrong": None,
                     "missing": None, "extra": None}
            outcomes.append(o)
            # persist incrementally so a preemption/kill still leaves a summary
            with open(os.path.join(batch_dir, "summary.json"), "w", encoding="utf-8") as fh:
                json.dump(outcomes, fh, indent=2)

    with open(os.path.join(batch_dir, "summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(outcomes[0].keys()))
        w.writeheader()
        w.writerows(outcomes)

    # ---- printed matrix: plans x targets ----
    grid = {(o["plan"], o["target"]): o for o in outcomes}
    w_plan = max(len(p) for p in plans)
    w_col = max(9, max(len(t) for t in tgts))
    print("\n\n================ BATCH SUMMARY ================")
    header = " " * w_plan + "  " + "  ".join(t[:w_col].rjust(w_col) for t in tgts)
    print(header)
    for plan in plans:
        cells = []
        for target in tgts:
            o = grid.get((plan, target))
            cells.append((_fmt(o) if o else "-").rjust(w_col))
        print(plan.ljust(w_plan) + "  " + "  ".join(cells))
    print("\nlegend: 0.xxx=score  '!'=score but transcription suspect  "
          "prod/<totals>=no truth  unavail=declared unavailable  CRASH=failed")

    # ---- ranked attention list (what a human should look at first) ----
    def needs_eyes(o):
        if o["status"] == "crash":
            return (0, o)                      # hard failures first
        if o["status"] == "scored" and o["totals"] == "suspect":
            return (1, o)                      # a score we can't trust
        if o["status"] == "scored" and (o["score"] or 0) < 0.98:
            return (2, o)                      # imperfect score - adjudicate
        if o["status"] in ("production", "unavailable") and o["totals"] == "suspect":
            return (3, o)                      # no truth AND internally inconsistent
        return None

    flagged = sorted((r for r in (needs_eyes(o) for o in outcomes) if r),
                     key=lambda r: r[0])
    print(f"\n---- attention list ({len(flagged)} of {len(outcomes)} runs) ----")
    labels = {0: "CRASH", 1: "SUSPECT+SCORED", 2: "IMPERFECT", 3: "NO-TRUTH+SUSPECT"}
    for rank, o in flagged:
        extra = o["crash"] if o["status"] == "crash" else \
            (f"score={o['score']} wrong={o['wrong']} totals={o['totals']}")
        print(f"  [{labels[rank]}] {o['plan']}/{o['target']}: {extra}")
    if not flagged:
        print("  (nothing flagged - every run scored clean or reconciled)")

    # ---- headline counts ----
    from collections import Counter
    c = Counter(o["status"] for o in outcomes)
    clean = sum(1 for o in outcomes if o["status"] == "scored"
                and (o["score"] or 0) >= 0.98 and o["totals"] != "suspect")
    print(f"\nstatus: {dict(c)} | clean-scored(>=0.98, reconciled): {clean}")
    print(f"[batch artifacts] {batch_dir}")


if __name__ == "__main__":
    main()
