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


def _plain_assumptions(result, target):
    """Plain-English notes for any modeling assumption a run embedded, written
    into derived.json (`assumptions_plain`) and printed. The point is that a
    reader of the extracted data sees, in ordinary language, what was assumed
    and why - not only the ops shorthand (Niccolo, 2026-07-28)."""
    notes = []
    b = result.get("broadcast")
    if b:
        how = ("averaging the " + " and ".join(b.get("series_sources", []) or []) +
               " columns") if b.get("series_op") == "mean" else \
              ("using the " + ", ".join(b.get("series_sources", []) or []) + " column")
        if b.get("axis") == "age":
            notes.append(
                "This plan's valuation reports " + target.replace("_", " ").lower() +
                " by YEARS OF SERVICE only - it does not break the rates down by age. "
                "We therefore applied each service level's rate to every age (" + how +
                "). This is faithful to the plan's own assumption that the rate depends "
                "on length of service, not age; it does not invent any numbers. "
                "(Approved by Niccolo, 2026-07-28; assumption register #4.)")
        else:
            notes.append(
                "This plan's valuation reports " + target.replace("_", " ").lower() +
                " by AGE only - it does not break the rates down by years of service. "
                "We applied each age's rate across every service column (" + how + "). "
                "Unlike the service-only case, this fills in a dimension the document "
                "does NOT measure, so it is a modeling ASSUMPTION, not a direct reading "
                "of the source. (Approved by Niccolo + coauthor, 2026-07-28; assumption "
                "register #4.)")
    return notes

# The extraction corpus: every city fund with an in-folder AV PDF (the ppd_id
# is the trailing number in the AV filename; it drives the PPD cross-check).
# workbook=None or a blank/stub sheet -> production mode (reviewed via the
# audit artifacts + PPD cross-check, not a score).
#
# EXPANDED 2026-07-29 from 16 to 32 funds. The missing PDFs were located in the
# PPD's own report library (publicplansdata.org/wp-content/uploads/reports/ -
# not linked from the site nav; the YEAR is swappable in the URL). Survey and
# per-plan year coverage: `Data Extraction/ppd_source_survey.md` +
# `ppd_report_availability.csv`. Every added PDF was verified for plan identity,
# year, text layer, and presence of the target exhibits before registration.
#
# VINTAGE RULE: the PDF year must match the workbook's vintage wherever a
# workbook exists, or the score compares two different years of data (hence
# nsh/nyc_ers use the 2020 AV against their data20 workbooks). Where no 2019 AV
# is published, the nearest available year is used and flagged below.
#
# NOT obtainable here: Fort Worth is not a PPD plan at all, and Indianapolis is
# not a city fund (its employees are in Indiana state plans) - the empty
# fw_/ind_ folders do not correspond to fetchable city AVs.
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

    # ---- ADDED 2026-07-29: never swept before, so nothing below is verified
    # against a PDF yet. Several DO carry 2022-collector ground truth (noted),
    # so they are scored, not production-only - but treat a first-sweep score as
    # a hypothesis until adjudicated against the source PDF, as always.
    # (a) the cities the catalogue wanted but whose PDFs were missing:
    "den":     _plan("den_modeldata", "CO_DENVERCITYCOUNTY-DERP_AV_2019_22.pdf", "den_data19_primary.xlsx", 22),
    "sea":     _plan("sea_modeldata", "WA_SEATTLECITY-ERS_AV_2019_156.pdf", "sea_data19_primary.xlsx", 156),
    # nsh + nyc_ers: 2020 AV to match their data20 workbooks (vintage rule above)
    "nsh":     _plan("nsh_modeldata", "TN_NASHVILLECITY-MPP_AV_2020_158.pdf", "nsh_data20_primary.xlsx", 158),
    "nyc_ers": _plan("nyc_modeldata", "NY_NYC-ERS_AV_2020_76.pdf", "nyc_data20_primary.xlsx", 76),
    # DC publishes ONE combined report covering Teachers (20) AND Police & Fire
    # (19); the dc workbook has no filled sheets -> both run production-mode.
    "dc_pf":   _plan("dc_modeldata", "DC_DCRB-PFRS-TRS_AV_2019_19_20.pdf", None, 19),
    "dc_teach": _plan("dc_modeldata", "DC_DCRB-PFRS-TRS_AV_2019_19_20.pdf", None, 20),
    # (b) city funds that exist in the PPD but were never registered:
    "hou_gen": _plan("hou_modeldata", "TX_HMERF_AV_2019_204.pdf", "hou_data19_gen.xlsx", 204),
    # hou_ff: NO 2019 AV is published (2016 -> 2020 gap); the 2020 AV is paired
    # with a data19 workbook, so its scores carry a one-year vintage mismatch.
    "hou_ff":  _plan("hou_modeldata", "TX_HOUSTONCITY-HFRRF_AV_2020_30.pdf", "hou_data19_ff.xlsx", 30),
    "dal_pf":  _plan("dal_modeldata", "TX_DALLASCITY-DPFP_AV_2019_153.pdf", "dal_data19_ffpol.xlsx", 153),
    "aus_pol": _plan("aus_modeldata", "TX_AUSTINCITY-COAPRS_AV_2019_217.pdf", None, 217),
    "aus_ff":  _plan("aus_modeldata", "TX_AUSTINCITY-COAFFRP_AV_2017_216.pdf", None, 216),   # nearest year: no 2018-2021 AV
    "clt_ff":  _plan("clt_modeldata", "NC_CHARLOTTE-FRS_AV_2022_182.pdf", None, 182),        # nearest year: AV starts 2022
    "nyc_pol": _plan("nyc_modeldata", "NY_NYC-PPF_AV_2019_150.pdf", None, 150),
    "nyc_edu": _plan("nyc_modeldata", "NY_NYC-BERS_AV_2018_211.pdf", None, 211),             # nearest year: no 2019 AV
    # nyc_fire publishes NO standalone AV - only the ACFR, which does carry
    # actuarial-valuation content. Expect a harder extraction.
    "nyc_fire": _plan("nyc_modeldata", "NY_NYC-FPF_ACFR_2021_149.pdf", None, 149),
    # Colorado PERA covers Denver Schools inside a multi-division report
    # (divisions 13/14/15/23 in one PDF) - a whole-document locate test.
    "den_schools": _plan("den_modeldata", "CO_CO-PERA-LGD-SCDTF-SDTF_AV_2019_13_14_15_23.pdf", None, 23),
}

# Funds registered 2026-07-29 and NOT yet swept - no cell of these has been
# checked against its PDF. Kept explicit so a first sweep can be reported
# separately from the established corpus.
NEWLY_ADDED = {"den", "sea", "nsh", "nyc_ers", "dc_pf", "dc_teach", "hou_gen",
               "hou_ff", "dal_pf", "aus_pol", "aus_ff", "clt_ff", "nyc_pol",
               "nyc_edu", "nyc_fire", "den_schools"}

# Documents whose layout-preserved text cannot fit the 262,144-token window
# alongside a response (let alone the retry conversation), so a default sweep
# skips them; naming one in --plans still runs it. nyc_fire is a 206-page ACFR
# (no standalone AV is published for that fund) at ~262K tokens on the
# worst-case measured ratio - it needs page-scoped extraction, not a full-doc
# pass. Estimates: `Data Extraction/ppd_source_survey.md`.
OVERSIZED = {"nyc_fire"}


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


def run_one(plan_key, target, targets, pages=None, verbose=True, base_dir=None):
    """Run one plan x target end to end. Writes artifacts to a fresh run dir
    and returns a structured outcome dict (never raises - a Stage A crash is
    captured as status='crash'). This is the unit the batch harness iterates.

    base_dir groups the cell's run dir: a batch passes its own dir so all its
    cells nest under it (runs/<batch>/<plan>_<target>_<ts>/); a bare single run
    (base_dir=None) lands in runs/_adhoc/ so the top of runs/ stays clean."""
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
    runs_root = base_dir or os.path.join(DATA_EXTRACTION, "runs", "_adhoc")
    run_dir = os.path.join(runs_root, f"{plan_key}_{target}_{stamp}")
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
                              zero_impossible_cfg=spec.get("zero_impossible_cells"),
                              broadcast=result.get("broadcast"))
    # plain-language record of any modeling assumption this run embedded, so a
    # reader of derived.json sees IN PLAIN ENGLISH what was assumed and why
    # (not only in the ops jargon). Currently the broadcast fills; extend as
    # other assumption-bearing ops are added.
    plain = _plain_assumptions(result, target)
    if plain:
        derived["assumptions_plain"] = plain
    with open(os.path.join(run_dir, "derived.json"), "w", encoding="utf-8") as fh:
        json.dump(derived, fh, indent=2)
    if not result.get("unavailable"):
        log("[stage B] declared operations:")
        for line in ops.summarize(result["row_map"], result["col_map"],
                                  derive=result.get("derive"),
                                  transpose=result.get("transpose", False),
                                  broadcast=result.get("broadcast")):
            log(f"    {line}")
    for note in plain:
        log(f"[assumption] {note}")

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
