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
import harness     # noqa: E402
import locate      # noqa: E402
import extract     # noqa: E402
import ops         # noqa: E402
import ppd_check   # noqa: E402

# targets whose derived grid is a COUNT distribution -> summable and
# cross-checkable against PPD actives_tot
COUNT_TARGETS = {"Age_Serv_Num"}

# The extraction corpus: every city fund with an in-folder AV PDF (the ppd_id
# is the trailing number in the AV filename; it drives the PPD cross-check).
# workbook=None or a blank/stub sheet -> production mode (reviewed via the
# audit artifacts + PPD cross-check, not a score). AVs are missing in-folder
# for the primary-layout cities (dc/den/fw/nsh/nyc/sea) and hou gen/ff -> those
# are not sweepable until the PDFs are fetched from publicplansdata.org.
def _plan(folder, pdf, workbook, ppd_id):
    return {"pdf": os.path.join(CITIES, folder, pdf),
            "workbook": os.path.join(CITIES, folder, workbook) if workbook else None,
            "ppd_id": ppd_id}


PLANS = {
    # ---- validated fidelity battery (2026-07-22) ----
    "phx":     _plan("phx_modeldata", "AZ_PHOENIXCITY-COPERS_AV_2019_94.pdf", "phx_data19_gen.xlsx", 94),
    "chi_pol": _plan("chi_modeldata", "IL_CHICAGOCITY-PABF_AV_2019_146.pdf", "chi_data19_pol.xlsx", 146),
    "sd":      _plan("sd_modeldata", "CA_SANDIEGOCITY-SDCERS_AV_2019_144.pdf", "sd_data19_gen.xlsx", 144),
    "mil":     _plan("mil_modeldata", "WI_MILWAUKEECITY-ERS_AV_2019_151.pdf", "mil_data19_gen.xlsx", 151),
    "aus":     _plan("aus_modeldata", "TX_AUSTINCITY-COAERS_AV_2019_12.pdf", None, 12),
    "bos":     _plan("bos_modeldata", "MA_BOSTONCITY-SBRS_AV_2019_148.pdf", "bos_data19_gen.xlsx", 148),
    # ---- rest of the corpus (in-folder AV + workbook) ----
    "chi_edu": _plan("chi_modeldata", "IL_CHICAGOCITY-CTPF_AV_2019_11.pdf", "chi_data19_edu.xlsx", 11),
    "chi_ff":  _plan("chi_modeldata", "IL_CHICAGOCITY-FABF_AV_2019_206.pdf", "chi_data19_ff.xlsx", 206),
    "chi_gen": _plan("chi_modeldata", "IL_CHICAGOCITY-MEABF_AV_2019_145.pdf", "chi_data19_gen.xlsx", 145),
    "dal":     _plan("dal_modeldata", "Tx_Dallas_ERF_AV_2019_201.pdf", "dal_data19_primary_AF.xlsx", 201),
    "hou_pol": _plan("hou_modeldata", "TX_HOUSTONCITY-HPOPS_AV_2019_208.pdf", "hou_data19_pol.xlsx", 208),
    "lax_gen": _plan("lax_modeldata", "CA_LACITY-LACERS_AV_2019_139.pdf", "lax_data19_gen.xlsx", 139),
    "lax_uty": _plan("lax_modeldata", "CA_LACITY-DWP_AV_2019_141.pdf", "lax_data19_uty.xlsx", 141),
    "lax_ffpol": _plan("lax_modeldata", "CA_LACITY-LAFPP_AV_2019_140.pdf", "lax_data19_ffpol.xlsx", 140),
    "phi":     _plan("phi_modeldata", "PA_PHILADELPHIACITY-MPERS_AV_2019_152.pdf", "phi_data19_gen.xlsx", 152),
    "sf":      _plan("sf_modeldata", "CA_SANFRANCITYCOUNTY-SFERS_AV_2019_98.pdf", "sf_data19_gen.xlsx", 98),
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
           "crash": None, "run_dir": None, "ppd": None}

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

    # for active-count targets, hand best-of-N the PPD plan total so it can
    # prefer a candidate that reconciles (catches wrong-table-set double-counts
    # like mil's 12-table over-sum that per-table totals-checks cannot see)
    reconcile_total = None
    if target == "Age_Serv_Num":
        reconcile_total = ppd_check.actives_tot(plan.get("ppd_id"))

    try:
        result, record = extract.extract(
            target, spec, source_text,
            record_path=os.path.join(run_dir, "record.json"),
            reconcile_total=reconcile_total)
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

    # ---- redundant safety verifier: PPD cross-check (count targets) ----
    # AV-independent second opinion: catches whole tables dropped/double-counted
    # (which a within-table totals-check cannot, since a shift conserves the
    # total) and works even with no human workbook.
    if target in COUNT_TARGETS and not result.get("unavailable"):
        ppd = ppd_check.cross_check(derived, plan.get("ppd_id"))
        if ppd:
            out["ppd"] = ppd["status"]
            mark = "OK" if ppd["status"] == "ok" else "!! OFF"
            log(f"[verify] PPD actives_tot cross-check: extracted {ppd['extracted']} "
                f"vs PPD {ppd['expected']} (ratio {ppd['ratio']}) -> {mark}")

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
