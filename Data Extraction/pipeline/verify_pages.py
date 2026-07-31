"""Check that a transcribed table's numbers ACTUALLY APPEAR in the PDF.

The gap this closes: every other check in this pipeline is either contract
validation (is the declaration well-formed?) or output plausibility (are the
values sane?). Neither can tell whether the numbers were READ or INVENTED.

Round 3 found the failure that needs: Philadelphia's assumptions appendix and
Charlotte's membership tables are printed as IMAGES. The text layer carries the
exhibit TITLE but no digits. The model located the title, and produced a full
table of plausible, internally-consistent, monotonic rates - which passed the
contract, passed the output audit, and was routed to a human as "spot-check
only". Fabricated numbers are the one error class that looks perfect.

Two signals per source table:
  match  - what share of the transcribed values can be found in the text of the
           page the model cited (or a nearby page - see below).
  image  - whether that page has essentially no digits in its text layer while
           carrying embedded images, i.e. nothing WAS readable there.

A low match alone is NOT proof of invention: AVs are routinely numbered by
PRINTED page, which is offset from the PDF index (5 of round 3's apparent
mismatches were pure offsets, 100% matched a few pages later). So the scan
searches a window around the cited page and reports where the values really
are. Only "not found anywhere near, AND the cited page is an image" is damning.

Usage:
  python pipeline/verify_pages.py --batch runs/_batch_round3 --csv out.csv
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_test  # noqa: E402

_DEC = re.compile(r"\d+\.\d+")
_DIG = re.compile(r"\d")


def value_forms(v):
    """Ways a number might be PRINTED: as itself, as a percentage, or per 1,000
    (rate tables are published on all three scales), with and without commas."""
    out = set()
    for x in (v, v * 100, v * 1000):
        if abs(x - round(x)) < 1e-9 and abs(x) < 1e12:
            out.add(str(int(round(x))))
            out.add(f"{int(round(x)):,}")
        s = "%g" % x
        out.add(s)
        if "." in s:
            out.add(s.rstrip("0").rstrip("."))
    return {s for s in out if len(s) >= 2}


def scan(pdf_path, table, window=12, sample=40):
    """-> (best_page, match_fraction, cited_page_is_image) or None."""
    import pdfplumber
    page = table.get("page")
    if not isinstance(page, int):
        return None
    vals = [v for row in (table.get("cells") or []) for v in row
            if isinstance(v, (int, float)) and v != 0][:sample]
    if len(vals) < 8:
        return None
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        if not 1 <= page <= n:
            return None
        cited = pdf.pages[page - 1]
        ctext = cited.extract_text() or ""
        is_image = (len(_DEC.findall(ctext)) <= 2 and len(_DIG.findall(ctext)) < 60
                    and len(cited.images) > 0)
        best = (0.0, page)
        for p in range(max(1, page - window), min(n, page + window) + 1):
            txt = pdf.pages[p - 1].extract_text() or ""
            if not txt:
                continue
            hit = sum(1 for v in vals if any(s in txt for s in value_forms(v)))
            frac = hit / len(vals)
            if frac > best[0]:
                best = (frac, p)
    return best[1], best[0], is_image


def verdict(match, is_image, cited, found):
    # Order matters: finding the values ANYWHERE nearby means they were read,
    # so that outranks the image flag. Only when nothing matches anywhere AND
    # the cited page carries no readable digits is invention the explanation.
    if match >= 0.6:
        return "ok" if cited == found else "page-offset (values are real)"
    if match >= 0.4:
        return "partial match - check (values largely found nearby)"
    if is_image:
        return "IMAGE PAGE - values cannot have been read; treat as FABRICATED"
    if match < 0.25:
        return "values not found near the cited page - verify against the PDF"
    return "partial match - check"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default="runs/_batch_round3")
    ap.add_argument("--csv")
    args = ap.parse_args()
    rows = []
    for d in sorted(glob.glob(os.path.join(args.batch, "*"))):
        f = os.path.join(d, "extraction.json")
        if not os.path.isdir(d) or not os.path.exists(f):
            continue
        e = json.load(open(f, encoding="utf-8"))
        if e.get("unavailable"):
            continue
        cell = os.path.basename(d)
        plan = next((k for k in sorted(run_test.PLANS, key=len, reverse=True)
                     if cell.startswith(k + "_")), None)
        if not plan:
            continue
        tables = e.get("source_tables") or []
        if not tables:
            continue
        try:
            r = scan(run_test.PLANS[plan]["pdf"], tables[0])
        except Exception as ex:
            print(f"  !! {cell}: {ex}")
            continue
        if not r:
            continue
        found, match, is_image = r
        cited = tables[0]["page"]
        rows.append({"cell": cell, "plan": plan,
                     "cited_page": cited, "values_found_on_page": found,
                     "match_pct": round(100 * match), "cited_page_is_image": is_image,
                     "verdict": verdict(match, is_image, cited, found)})
        print(f"  {rows[-1]['verdict'][:46]:48} {cell[:44]:46} "
              f"cited p{cited} -> p{found} ({rows[-1]['match_pct']}%)")
    if args.csv and rows:
        import csv as _csv
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {args.csv} ({len(rows)} tables)")
    bad = [r for r in rows if "FABRICATED" in r["verdict"]]
    off = [r for r in rows if r["verdict"].startswith("page-offset")]
    print(f"\n{len(rows)} tables | {len(off)} page-offset | {len(bad)} image-page/fabricated")


if __name__ == "__main__":
    main()
