"""
Build Documentation/city_extraction_catalogue.md — a per-plan, per-sheet record of
WHAT is extracted for each city plan and WHERE it is documented (source PDFs +
verbatim collector logs + Airtable table docs). For reviewing the already-done
plans (and learning the method) and doing the remaining ones by hand.

Read-only inputs; writes one markdown file (UTF-8). Run from project root:
    python "Documentation/provenance/build_city_extraction_catalogue.py"
"""
import os, re, glob, zipfile
import pandas as pd
import openpyxl

PROV = os.path.dirname(os.path.abspath(__file__))         # Documentation/provenance/
ROOT = os.path.dirname(os.path.dirname(PROV))             # project root
CIT = os.path.join(ROOT, "Data", "Plans", "Cities")
DOCS = os.path.join(ROOT, "Documentation")                # catalogue (narrative) stays top-level
OUT = os.path.join(DOCS, "city_extraction_catalogue.md")

MODEL_SHEETS = ["Age_Serv_Num", "Age_Serv_Wage", "Sep_Rate", "Avg_Mort", "Ret_Rate", "Retirement"]
ALL_SHEETS = ["Wage_Growth", "Refund_Rate", "Avg_Mort", "Sep_Rate", "Ret_Rate",
              "Retirement", "Age_Serv_Num", "Age_Serv_Wage", "Inactv_Serv_Num"]
SHEET_TO_STATE = {"Age_Serv_Num": "ageservice", "Age_Serv_Wage": "wagerel",
                  "Sep_Rate": "withdrawal", "Avg_Mort": "mortality",
                  "Ret_Rate": "retirement", "Retirement": "retdist",
                  "Wage_Growth": "wagegrowth (GHOST: engine ignores)",
                  "Refund_Rate": "refund (model-defaults)",
                  "Inactv_Serv_Num": "inactive scaling (model-defaults)"}
ROLE = {"Age_Serv_Num": "CORE", "Age_Serv_Wage": "CORE", "Sep_Rate": "CORE",
        "Avg_Mort": "matters", "Ret_Rate": "matters", "Retirement": "matters (retdist)",
        "Wage_Growth": "unused", "Refund_Rate": "defaulted", "Inactv_Serv_Num": "defaulted"}
STATUS_GLYPH = {"plan_specific": "DONE (plan-specific)", "shared_default": "COPIED-DEFAULT (verify)",
                "empty": "EMPTY (missing)", "absent": "ABSENT (no sheet)"}

PLAN_FUND = {  # plan -> the ONE ppd_id it actually models (multi-fund cities)
 "chi_data19_edu":"11","chi_data19_gen":"145","chi_data19_pol":"146","chi_data19_ff":"206",
 "hou_data19_gen":"204","hou_data19_pol":"208","hou_data19_ff":"30",
 "lax_data19_gen":"139","lax_data19_ffpol":"140","lax_data19_uty":"141",
}
FUND_NAMES = {  # ppd_id -> readable fund
 "11":"Chicago Teachers (CTPF)","145":"Chicago Municipal (MEABF)","146":"Chicago Police (PABF)",
 "206":"Chicago Fire (FABF)","215":"Chicago Laborers","204":"Houston Municipal (HMERF)",
 "208":"Houston Police (HPOPS)","30":"Houston Firefighters (HFRRF)","139":"LA City Employees (LACERS)",
 "140":"LA Fire & Police (LAFPP)","141":"LA Water & Power (DWP)","148":"Boston (State-Boston RS)",
 "151":"Milwaukee ERS","152":"Philadelphia Municipal (PMRS)","94":"Phoenix (COPERS)",
 "144":"San Diego (SDCERS)","98":"San Francisco (SFERS)","201":"Dallas ERF","12":"Austin (COAERS)"}

CLEAN = {
    "﻿": "",                       # BOM
    "’": "'", "‘": "'",        # smart single quotes
    "“": '"', "”": '"',        # smart double quotes
    "–": "-", "—": "-",        # en/em dash
    "�": "'",                       # replacement char (was usually an apostrophe)
    "â€™": "'",           # mojibake '
    "â€œ": '"', "â€": '"',  # mojibake " "
    "â€“": "-", "â€”": "-",  # mojibake - -
    "Â": "",                        # stray mojibake A-circumflex
}
def clean(t):
    for a, b in CLEAN.items():
        t = t.replace(a, b)
    return t

def docx_text(path):
    try:
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8","ignore")
    except Exception as e:
        return f"[unreadable docx: {e}]"
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return clean(re.sub(r"\n{3,}", "\n\n", xml).strip())

def read_text(path):
    try:
        return clean(open(path, encoding="utf-8-sig", errors="ignore").read().strip())
    except Exception as e:
        return f"[unreadable: {e}]"

def folder_for(plan):
    city = plan.split("_")[0]
    return os.path.join(CIT, f"{city}_modeldata")

def source_pdfs(folder, fund_id=None):
    """If fund_id is known, return only PDFs whose filename carries that ppd_id;
    if none match, return ([],[],[]) with matched=False so the caller can flag it."""
    av, cafr, other = [], [], []
    all_av, all_cafr = [], []
    for f in glob.glob(os.path.join(folder, "*.pdf")):
        b = os.path.basename(f); bl = b.lower()
        is_av = ("_av" in bl or "av_2019" in bl or "merf_av" in bl)
        is_cafr = any(k in bl for k in ("cafr","acfr","financialstatements","annualreport"))
        match = (fund_id is None) or bool(re.search(rf"[_-]{fund_id}(?:[._-]|$)", os.path.splitext(bl)[0]))
        if is_av: all_av.append(b)
        elif is_cafr: all_cafr.append(b)
        if match:
            if is_av: av.append(b)
            elif is_cafr: cafr.append(b)
            elif not (is_av or is_cafr): other.append(b)
    matched = (fund_id is None) or bool(av or cafr)
    if not matched:   # fund known but no file carries its id -> report folder contents as context
        return sorted(all_av), sorted(all_cafr), sorted(other), False
    return sorted(av), sorted(cafr), sorted(other), True

def plan_logs(plan, folder):
    """Return [(filename, text)] — per-plan log first, then city-level logs."""
    city = plan.split("_")[0]
    out = []
    # per-plan .md log
    p = os.path.join(folder, f"{plan}_log.md")
    if os.path.exists(p): out.append((f"{plan}_log.md", read_text(p)))
    # city-level logs (.md/.txt/.docx not tied to a single plan)
    for f in sorted(glob.glob(os.path.join(folder, "*"))):
        b = os.path.basename(f); bl = b.lower()
        if f.endswith(p): continue
        if bl == f"{plan}_log.md": continue
        if bl.endswith(".docx") and ("log" in bl):
            out.append((b, docx_text(f)))
        elif bl.endswith(".txt") and "log" in bl:
            out.append((b, read_text(f)))
        elif bl.endswith(".md") and "log" in bl and not bl.startswith(plan):
            # other-plan .md logs only attached if city-level (no plan prefix match)
            if not re.match(r"[a-z]+_data\d", bl):
                out.append((b, read_text(f)))
    return out

def scratch_sheets(plan, folder):
    f = os.path.join(folder, f"{plan}.xlsx")
    if not os.path.exists(f): return []
    try:
        wb = openpyxl.load_workbook(f, read_only=True)
        s = [sn for sn in wb.sheetnames if "scratch" in sn.lower() or "note" in sn.lower() or "work" in sn.lower()]
        wb.close(); return s
    except Exception:
        return []

def main():
    fill = pd.read_csv(os.path.join(PROV, "city_sheet_fill_audit.csv"))
    inv = pd.read_csv(os.path.join(PROV, "city_source_inventory.csv")).set_index("plan")
    plans = sorted(fill["plan"].unique())

    L = []
    W = L.append
    W("# City Extraction Catalogue\n")
    W("**Generated** by `build_city_extraction_catalogue.py` (do not hand-edit; regenerate). "
      "Per city plan: what is extracted on each model-relevant sheet, the source documents it came "
      "from, and the verbatim collector provenance/assumptions. Use it to (a) review and check the "
      "already-extracted plans and learn the extraction method, and (b) work the remaining gaps yourself.\n")
    W("**Status legend:** DONE (plan-specific extracted data) | COPIED-DEFAULT (a generic table was "
      "pasted in — verify whether it's a legitimate published standard table or a placeholder) | "
      "EMPTY (sheet exists but blank) | ABSENT (no sheet).\n")
    W("**Which sheets matter:** the engine reads only `ageservice, retdist, wagerel, mortality, "
      "withdrawal, retirement, refund`. `Wage_Growth` and `disability` are GHOST sheets (never read — "
      "wage growth comes from PPD). `Refund_Rate` and `Inactv_Serv_Num` are model-DEFAULTED (don't "
      "block a run). So real extraction effort = the 6 columns below. See `model_input_dictionary.md`.\n")
    W("**How extraction was documented (the 'from where'):** (1) the source AV/CAFR PDFs listed per "
      "plan; (2) the collector logs reproduced verbatim below (Amy Fan / Alex Gant, 2022) — these state, "
      "per sheet, what was found, in which document, and what assumption was made; (3) the Airtable base "
      "'Pensions documentation' (export in `Data/Sources/airtable_export/`, currently only Boston's table "
      "rows — needs an 'All'-views re-export); (4) the per-sheet keyword catalog in "
      "`guidebook_city_collection.md` (what each table is titled in an AV — your search guide when "
      "extracting new ones).\n")

    # master matrix
    W("\n## Master matrix (6 model-relevant sheets)\n")
    W("| plan | fund(s) | "+" | ".join(s.replace("_","\\_") for s in MODEL_SHEETS)+" |")
    W("|"+"---|"*(2+len(MODEL_SHEETS)))
    glyph_short={"plan_specific":"DONE","shared_default":"copy?","empty":"EMPTY","absent":"ABSENT"}
    def plan_fund_label(plan):
        if plan in PLAN_FUND:
            p = PLAN_FUND[plan]; return f"{p} = {FUND_NAMES.get(p,p)}"
        ppds = str(inv.loc[plan,"city_ppd_ids"]) if plan in inv.index else ""
        ids = [p for p in ppds.split("|") if p and p.lower() != "nan"]
        if len(ids) == 1: return f"{ids[0]} = {FUND_NAMES.get(ids[0],ids[0])}"
        if not ids: return "— (no ppd_id derivable from folder PDFs; see planlevel_overview.xlsx)"
        return "; ".join(f"{p}={FUND_NAMES.get(p,p)}" for p in ids)

    for plan in plans:
        row = fill[fill.plan==plan].set_index("sheet")
        funds = plan_fund_label(plan)
        cells = " | ".join(glyph_short.get(row.loc[s,"status"],"?") if s in row.index else "?" for s in MODEL_SHEETS)
        W(f"| {plan} | {funds} | {cells} |")

    # per-plan detail
    W("\n## Per-plan detail\n")
    for plan in plans:
        folder = folder_for(plan)
        row = fill[fill.plan==plan].set_index("sheet")
        layout = inv.loc[plan,"folder_layout"] if plan in inv.index else ""
        funds = plan_fund_label(plan)
        fund_id = PLAN_FUND.get(plan) or (lambda ids: ids[0] if len(ids)==1 else None)(
            [p for p in str(inv.loc[plan,"city_ppd_ids"]).split("|") if p] if plan in inv.index else [])
        av, cafr, other, matched = source_pdfs(folder, fund_id)
        scr = scratch_sheets(plan, folder)

        W(f"\n### {plan}")
        W(f"- **Fund / ppd_id:** {funds}")
        W(f"- **Folder layout:** {layout}")
        if not matched:
            W(f"- **Source PDFs:** ⚠ NO PDF in folder matches this fund's ppd_id "
              f"({fund_id}) — must be fetched. Other PDFs present: {', '.join(av+cafr) or 'none'}")
        else:
            W(f"- **Source AV PDF(s):** {', '.join(av) if av else '— none in folder —'}")
            W(f"- **Source CAFR/ACFR PDF(s):** {', '.join(cafr) if cafr else '— none in folder —'}")
        if other and matched: W(f"- **Other PDF(s):** {', '.join(other)}")
        if scr: W(f"- **In-workbook scratch/notes sheets:** {', '.join(scr)}")
        W("\n| sheet | model input | role | status |")
        W("|---|---|---|---|")
        for s in ALL_SHEETS:
            st = row.loc[s,"status"] if s in row.index else "absent"
            W(f"| {s} | {SHEET_TO_STATE[s]} | {ROLE[s]} | {STATUS_GLYPH.get(st,st)} |")
        logs = plan_logs(plan, folder)
        if logs:
            for fn, txt in logs:
                W(f"\n**Provenance log — `{fn}`:**\n")
                W("```")
                W(txt if txt.strip() else "(empty)")
                W("```")
        else:
            W("\n**Provenance log:** none in folder (provenance, if any, is in Airtable).")

    # Airtable table docs
    W("\n## Airtable table-level documentation (export)\n")
    at = os.path.join(ROOT, "Data", "Sources", "airtable_export", "2. tables-Default.csv")
    if os.path.exists(at):
        df = pd.read_csv(at)
        W(f"`2. tables-Default.csv` — {df.shape[0]} rows, columns: {', '.join(map(str,df.columns))}\n")
        W("(Per the data-sources map this 'Default' export captured only Boston's table rows; a "
          "re-export from the Airtable 'All' views is needed to get every plan's per-table "
          "source-doc + page + assumptions.)\n")
        W("```")
        W(clean(df.head(40).to_string(index=False)))
        W("```")
    else:
        W("_(no Airtable tables export found)_")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {OUT}  ({len(L)} lines, {len(plans)} plans)")

if __name__ == "__main__":
    main()
