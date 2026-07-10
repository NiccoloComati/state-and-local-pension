"""Orchestrator: extract (Stage A) -> execute declared ops (Stage B) -> score.

Stage A: the model receives the FULL text layer of the AV, locates the source
table(s) itself, transcribes them EXACTLY as printed, and declares bin-mapping
operations. Stage B: ops.py executes those operations deterministically (the
model does no arithmetic). The derived grid is scored against the human
workbook; the source-native tables are kept for reproducibility/auditing.

Usage (from the "Data Extraction" folder or anywhere):
    python pipeline/run_test.py --plan phx --target Age_Serv_Num
    python pipeline/run_test.py --plan phx --target Age_Serv_Wage
    python pipeline/run_test.py --plan chi_pol --target Age_Serv_Num
    python pipeline/run_test.py --plan phx --target Age_Serv_Num --dry-run

Debug/diagnostic options:
    --pages 38 39     restrict the document text to specific pages (cost/debug
                      lever only - NOT the normal flow)
    --keyword-scan    show the naive keyword page ranking (diagnostic only)

Artifacts land in Data Extraction/runs/<plan>_<target>_<timestamp>/:
    extraction.json  (source-native tables + declared row/col maps + notes)
    derived.json     (the grid AFTER executing the ops - what gets scored)
    record.json      (full API request + raw response - the audit trail)
    report.json      (the score vs ground truth)
"""
import argparse
import datetime
import json
import os
import sys

# Windows console is cp1252; PDF text carries Unicode - never crash on print
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))       # .../Data Extraction/pipeline
DATA_EXTRACTION = os.path.dirname(HERE)                  # .../Data Extraction
ROOT = os.path.dirname(DATA_EXTRACTION)                  # project root
CITIES = os.path.join(ROOT, "Data", "Plans", "Cities")

sys.path.insert(0, HERE)
import harness   # noqa: E402
import locate    # noqa: E402
import extract   # noqa: E402
import ops       # noqa: E402

# Test plans: ground truth exists for all of these (verified for phx;
# chi_pol and sd have logged human extractions).
PLANS = {
    "phx": {
        "pdf": os.path.join(CITIES, "phx_modeldata", "AZ_PHOENIXCITY-COPERS_AV_2019_94.pdf"),
        "workbook": os.path.join(CITIES, "phx_modeldata", "phx_data19_gen.xlsx"),
    },
    "chi_pol": {
        "pdf": os.path.join(CITIES, "chi_modeldata", "IL_CHICAGOCITY-PABF_AV_2019_146.pdf"),
        "workbook": os.path.join(CITIES, "chi_modeldata", "chi_data19_pol.xlsx"),
    },
    "sd": {
        "pdf": os.path.join(CITIES, "sd_modeldata", "CA_SANDIEGOCITY-SDCERS_AV_2019_144.pdf"),
        "workbook": os.path.join(CITIES, "sd_modeldata", "sd_data19_gen.xlsx"),
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, choices=sorted(PLANS))
    ap.add_argument("--target", required=True)
    ap.add_argument("--pages", type=int, nargs="+",
                    help="DEBUG: restrict document text to these 1-indexed pages")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the prompt, do not call the API")
    ap.add_argument("--keyword-scan", action="store_true",
                    help="DIAGNOSTIC: show the naive keyword page ranking and exit")
    args = ap.parse_args()

    plan = PLANS[args.plan]
    with open(os.path.join(HERE, "targets.json"), encoding="utf-8") as fh:
        targets = json.load(fh)
    if args.target not in targets:
        sys.exit(f"unknown target {args.target}; known: "
                 f"{[k for k in targets if not k.startswith('_')]}")
    spec = targets[args.target]

    if args.keyword_scan:
        for p, score_, matched in locate.locate_pages(plan["pdf"], spec["keywords"], top_k=8):
            print(f"  p.{p:>3}  score={score_}  {matched}")
        return

    # ---- document text (whole document unless debugging with --pages) ----
    if args.pages:
        print(f"[doc] DEBUG mode: restricting to pages {args.pages}")
        source_text = locate.page_text(plan["pdf"], args.pages)
    else:
        source_text = locate.full_text(plan["pdf"])
        print(f"[doc] full document: {os.path.basename(plan['pdf'])} "
              f"({len(source_text):,} chars, ~{len(source_text) // 4:,} tokens)")
        if len(source_text.strip()) < 1000:
            sys.exit("document text layer is (near-)empty - vision fallback needed")

    # ---- extract ----
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(DATA_EXTRACTION, "runs", f"{args.plan}_{args.target}_{stamp}")
    if not args.dry_run:
        os.makedirs(run_dir, exist_ok=True)

    result, _ = extract.extract(
        args.target, spec, source_text,
        record_path=None if args.dry_run else os.path.join(run_dir, "record.json"),
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return

    with open(os.path.join(run_dir, "extraction.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    for k, t in enumerate(result["source_tables"]):
        print(f"[stage A] source_tables[{k}]: p.{t['page']} {t['title']!r} "
              f"({len(t['row_labels'])}x{len(t['col_labels'])})")
        issues = ops.totals_check(t)
        if issues:
            print(f"[stage A] !! TRANSCRIPTION SUSPECT (printed-totals check failed):")
            for msg in issues:
                print(f"      {msg}")
        elif t.get("printed_row_totals") or t.get("printed_col_totals"):
            print(f"[stage A]    printed-totals check: OK")
        else:
            print(f"[stage A]    (no printed totals to check against)")
    print(f"[stage A] notes: {result.get('notes', '')[:400]}")

    # ---- stage B: execute the declared operations (deterministic) ----
    derived = ops.execute(result["source_tables"], result["row_map"], result["col_map"])
    with open(os.path.join(run_dir, "derived.json"), "w", encoding="utf-8") as fh:
        json.dump(derived, fh, indent=2)
    print("[stage B] declared operations:")
    for line in ops.summarize(result["row_map"], result["col_map"]):
        print(f"    {line}")

    # ---- score the derived grid against the human workbook ----
    truth = harness.load_truth(plan["workbook"], args.target)
    report = harness.score(truth, derived,
                           zero_equals_empty=spec.get("zero_equals_empty", False))
    with open(os.path.join(run_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"[score] {args.plan} / {args.target}")
    harness.print_report(report)
    print(f"[artifacts] {run_dir}")


if __name__ == "__main__":
    main()
