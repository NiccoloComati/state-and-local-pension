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

The breadth-first sweep over every plan x target is run_batch.py, which calls
run_one() below and writes an aggregate report.

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
    # ---- production-style plans (little or no ground truth; extraction is
    # reviewed via the audit artifacts, not a score) ----
    "aus": {   # Austin COAERS - workbook never filled; fully cold (GRS)
        "pdf": os.path.join(CITIES, "aus_modeldata", "TX_AUSTINCITY-COAERS_AV_2019_12.pdf"),
        "workbook": None,
    },
    "mil": {   # Milwaukee ERS - novel actuarial firm; only Age_Serv_Num has truth
        "pdf": os.path.join(CITIES, "mil_modeldata", "WI_MILWAUKEECITY-ERS_AV_2019_151.pdf"),
        "workbook": os.path.join(CITIES, "mil_modeldata", "mil_data19_gen.xlsx"),
    },
    "bos": {   # Boston SBRS - stub workbook (Segal)
        "pdf": os.path.join(CITIES, "bos_modeldata", "MA_BOSTONCITY-SBRS_AV_2019_148.pdf"),
        "workbook": os.path.join(CITIES, "bos_modeldata", "bos_data19_gen.xlsx"),
    },
}


def load_targets():
    with open(os.path.join(HERE, "targets.json"), encoding="utf-8") as fh:
        return json.load(fh)


def target_names(targets):
    return [k for k in targets if not k.startswith("_")]


def _totals_status(result):
    """Worst printed-totals status across the transcribed source tables:
    'suspect' if any table fails reconciliation, 'clean' if some table has
    printed totals and all reconcile, 'none' if no table prints totals."""
    tables = result.get("source_tables", [])
    any_printed = any(t.get("printed_row_totals") or t.get("printed_col_totals")
                      for t in tables)
    any_suspect = any(ops.totals_check(t) for t in tables)
    return "suspect" if any_suspect else ("clean" if any_printed else "none")


def run_one(plan_key, target, targets, pages=None, verbose=True):
    """Run one plan x target end to end. Writes artifacts to a fresh run dir
    and returns a structured outcome dict (never raises - a Stage A crash is
    captured as status='crash'). This is the unit the batch harness iterates."""
    plan = PLANS[plan_key]
    spec = targets[target]
    out = {"plan": plan_key, "target": target, "status": None, "score": None,
           "exact": None, "close": None, "wrong": None, "missing": None,
           "extra": None, "totals": None, "n_tables": None, "n_attempts": None,
           "crash": None, "run_dir": None}

    def log(*a):
        if verbose:
            print(*a)

    if pages:
        source_text = locate.page_text(plan["pdf"], pages)
    else:
        source_text = locate.full_text(plan["pdf"])
        log(f"[doc] full document: {os.path.basename(plan['pdf'])} "
            f"({len(source_text):,} chars, ~{len(source_text) // 4:,} tokens)")
        if len(source_text.strip()) < 1000:
            out["status"] = "crash"
            out["crash"] = "document text layer is (near-)empty - vision fallback needed"
            log("[doc] " + out["crash"])
            return out

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(DATA_EXTRACTION, "runs", f"{plan_key}_{target}_{stamp}")
    os.makedirs(run_dir, exist_ok=True)
    out["run_dir"] = run_dir

    try:
        result, record = extract.extract(
            target, spec, source_text,
            record_path=os.path.join(run_dir, "record.json"))
    except Exception as e:                          # noqa: BLE001 - report, don't crash the sweep
        out["status"] = "crash"
        out["crash"] = str(e).replace("\n", " | ")[:300]
        try:
            with open(os.path.join(run_dir, "record.json"), encoding="utf-8") as fh:
                out["n_attempts"] = len(json.load(fh).get("attempts", []))
        except (OSError, ValueError):
            pass
        log(f"[CRASH] {plan_key}/{target}: {out['crash']}")
        return out

    out["n_attempts"] = len(record.get("attempts", []))
    with open(os.path.join(run_dir, "extraction.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    for k, t in enumerate(result["source_tables"]):
        log(f"[stage A] source_tables[{k}]: p.{t['page']} {t['title']!r} "
            f"({len(t['row_labels'])}x{len(t['col_labels'])})")
        issues = ops.totals_check(t)
        if issues:
            log("[stage A] !! TRANSCRIPTION SUSPECT (printed-totals check failed):")
            for msg in issues:
                log(f"      {msg}")
        elif t.get("printed_row_totals") or t.get("printed_col_totals"):
            log("[stage A]    printed-totals check: OK")
        else:
            log("[stage A]    (no printed totals to check against)")
    log(f"[stage A] notes: {result.get('notes', '')[:400]}")
    out["n_tables"] = len(result["source_tables"])
    out["totals"] = _totals_status(result)

    # ---- stage B: execute the declared operations (deterministic) ----
    if result.get("unavailable"):
        log("[stage B] TARGET DECLARED UNAVAILABLE in this document - derived.json")
        log("          is the empty template grid; tables above are archived evidence.")
        derived = ops.empty_grid(spec["grid"]["row_labels"], spec["grid"]["col_labels"])
    else:
        for kind, m, spans in (("rows", result["row_map"], spec.get("target_row_spans")),
                               ("cols", result["col_map"], spec.get("target_col_spans"))):
            _, audit = ops.resolve_overlap_sources(m, spans)
            for msg in audit:
                log(f"[stage B] overlap audit ({kind}): {msg}")
        derived = ops.execute(result["source_tables"], result["row_map"], result["col_map"],
                              derive=result.get("derive"),
                              transpose=result.get("transpose", False),
                              target_row_spans=spec.get("target_row_spans"),
                              target_col_spans=spec.get("target_col_spans"),
                              to_decimal=spec.get("convert_percent_to_decimal", False),
                              zero_impossible_cfg=spec.get("zero_impossible_cells"))
    with open(os.path.join(run_dir, "derived.json"), "w", encoding="utf-8") as fh:
        json.dump(derived, fh, indent=2)
    if not result.get("unavailable"):
        log("[stage B] declared operations:")
        for line in ops.summarize(result["row_map"], result["col_map"],
                                  derive=result.get("derive"),
                                  transpose=result.get("transpose", False)):
            log(f"    {line}")

    # ---- score against the human workbook (if one exists and is filled) ----
    truth = None
    if plan["workbook"]:
        try:
            truth = harness.load_truth(plan["workbook"], target)
            if not any(v is not None for row in truth["cells"] for v in row):
                truth = None
        except (KeyError, ValueError):
            truth = None
    if truth is None:
        out["status"] = "unavailable" if result.get("unavailable") else "production"
        log(f"[score] no ground truth for {plan_key}/{target} - PRODUCTION MODE "
            "(review artifacts vs the PDF; no score)")
        log(f"[artifacts] {run_dir}")
        return out

    report = harness.score(truth, derived,
                           zero_equals_empty=spec.get("zero_equals_empty", False))
    with open(os.path.join(run_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    out["status"] = "scored"
    out["score"] = report.get("accuracy")
    out["exact"] = report.get("exact")
    out["close"] = report.get("close")
    out["wrong"] = report.get("wrong")
    out["missing"] = report.get("missing_in_cand")
    out["extra"] = report.get("extra_in_cand")
    log(f"[score] {plan_key} / {target}")
    if verbose:
        harness.print_report(report)
    log(f"[artifacts] {run_dir}")
    return out


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

    targets = load_targets()
    if args.target not in targets:
        sys.exit(f"unknown target {args.target}; known: {target_names(targets)}")
    plan = PLANS[args.plan]
    spec = targets[args.target]

    if args.keyword_scan:
        for p, score_, matched in locate.locate_pages(plan["pdf"], spec["keywords"], top_k=8):
            print(f"  p.{p:>3}  score={score_}  {matched}")
        return

    if args.dry_run:
        src = (locate.page_text(plan["pdf"], args.pages) if args.pages
               else locate.full_text(plan["pdf"]))
        extract.extract(args.target, spec, src, dry_run=True)
        return

    run_one(args.plan, args.target, targets, pages=args.pages, verbose=True)


if __name__ == "__main__":
    main()
