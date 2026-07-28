"""Two transcription failures the 2026-07-28 verify batch exposed.

1. chi_ff Age_Serv_Wage CRASHED again (8 attempts) - and NOT on the monthly
   salary issue it was re-run to prove. 5 of the 8 attempts died on
   "cells has 13 rows but 12 row_labels": Exhibit B.1 p.32 prints 12 age bands
   plus a 'Total' line, and the model put the Total line in cells without a
   label. The interleave guard only fires on EXACT multiples (one attempt did
   show 24 = 2x12), so the +1 case got a bare count mismatch and never
   recovered - which meant ops.execute never ran and the monthly fix was never
   exercised. Guard: len(cells) == len(row_labels) + 1 names the printed total.

2. chi_edu Age_Serv_Wage scored 0.00 while transcribing every value CORRECTLY
   but one column late: cells[25-29] = [None, 4761166, 145504054, 46732744, ...]
   where p55 prints Under 1 = $4,761,166 | 1-4 = $145,504,054 | 5-9 =
   $46,732,744. The workbook matches the PDF exactly - (4,761,166+145,504,054)
   / (388+2,625) = 49,872.29 - so truth was right and the candidate was shifted.
   ops.totals_check caught it (10 row-total mismatches) but the local backend
   only WARNED, while the Anthropic path had always retried on totals. Guard:
   a contract-clean candidate with totals mismatches now gets one correction
   retry carrying those mismatches.

Run: python pipeline/test_transcription_guards.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract  # noqa: E402
import harness  # noqa: E402
import ops      # noqa: E402


def main():
    spec = json.load(open(os.path.join(HERE, "targets.json"),
                          encoding="utf-8"))["Age_Serv_Wage"]

    # ---- 1. the +1 printed-total row -------------------------------------
    labels = ["Under 20", "20 - 24", "25 - 29"]
    tbl = {"page": 32, "title": "Exhibit B.1 (counts)",
           "row_labels": labels, "col_labels": ["Under 1", "1 - 4"],
           "cells": [[None, None], [20, 20], [121, 170],
                     [382, 559]],                      # <- the printed Total line
           "printed_row_totals": None, "printed_col_totals": None}
    res = {"source_tables": [tbl], "derive": None, "transpose": False,
           "row_map": [{"target": "<25", "sources": labels[:2], "op": "sum",
                        "weights_table": None}],
           "col_map": [{"target": "4", "sources": ["Under 1", "1 - 4"], "op": "sum"}],
           "notes": "n"}
    probs = extract.validate(copy.deepcopy(res), spec)
    msg = next((x for x in probs if "row_labels" in x), None)
    assert msg and "exactly ONE extra" in msg, probs
    assert "printed_col_totals" in msg, msg
    print("  +1 row: named as the printed TOTAL line, routed to printed_col_totals")

    # an exact multiple still gets the INTERLEAVED message (not the total one)
    inter = copy.deepcopy(res)
    inter["source_tables"][0]["cells"] = [[1, 2]] * 6      # 6 = 2 x 3 labels
    m2 = next(x for x in extract.validate(inter, spec) if "row_labels" in x)
    assert "INTERLEAVED" in m2 and "exactly ONE extra" not in m2, m2
    print("  exact multiples still route to the INTERLEAVED message")

    # and a matching table is silent
    ok = copy.deepcopy(res)
    ok["source_tables"][0]["cells"] = [[None, None], [20, 20], [121, 170]]
    assert not [x for x in extract.validate(ok, spec) if "row_labels" in x]
    print("  a well-formed table is silent")

    # ---- 2. totals mismatches reach the model ----------------------------
    run = harness.find_run("chi_edu_Age_Serv_Wage_20260727_194149")
    with open(os.path.join(run, "extraction.json"), encoding="utf-8") as fh:
        shifted = json.load(fh)

    # the shipped candidate really was contract-clean ...
    assert extract.validate(copy.deepcopy(shifted), spec) == [], \
        extract.validate(copy.deepcopy(shifted), spec)
    # ... yet its own printed totals contradict it
    _, fatal, totals, _ = extract._evaluate(json.dumps(shifted), spec)
    assert fatal == [], fatal
    assert len(totals) >= 10, totals
    assert all(isinstance(t, str) and t.startswith("source_tables[") for t in totals)
    print(f"  chi_edu: contract-clean but {len(totals)} printed-total mismatches")

    # the correction message carries them AND explains the split-numeral cause
    note = extract._totals_correction_message(totals)
    assert "cells sum to" in note, note
    assert "COLUMN MISALIGNMENT" in note
    assert "2625" in note and "46732744" in note      # the real p55 split numerals
    print("  correction message quotes the mismatches and the split-numeral cause")

    # confirm the diagnosis against the PDF: truth = (dollars)/(lives), and the
    # candidate's own numbers reproduce it only when read one column EARLIER
    dollars, lives = shifted["source_tables"][0], shifted["source_tables"][1]
    r = dollars["row_labels"].index("25-29")
    cols = dollars["col_labels"]
    d1, d2 = dollars["cells"][r][cols.index("1-4")], dollars["cells"][r][cols.index("5-9")]
    l1, l2 = lives["cells"][r][cols.index("1-4")], lives["cells"][r][cols.index("5-9")]
    assert (d1, d2, l1, l2) == (4761166, 145504054, 388, 2625), (d1, d2, l1, l2)
    avg = (d1 + d2) / (l1 + l2)
    assert abs(avg - 49872.29339528709) < 1e-6, avg
    print(f"  PDF check: values sit under the NEXT column's header; read correctly "
          f"they give {avg:,.2f} = the workbook value")

    print("PASS: the +1 total row is named, and a totals-mismatched candidate now "
          "gets a correction carrying the evidence")


if __name__ == "__main__":
    main()
