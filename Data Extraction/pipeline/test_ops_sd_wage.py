"""Executor verification for COLUMN weighted_avg.

San Diego's AV (Cheiron, Table A-8) publishes averages directly, but its
service columns are finer than the target's: 'Under 1'+'1 to 4' merge into
target '4', and '35 to 39'+'40 and up' into target '40'. Merging averages
needs a count-weighted average ACROSS COLUMNS - an op the col_map vocabulary
lacked. The live run of 2026-07-10 (sd_Age_Serv_Wage_20260710_124156)
transcribed both tables correctly and NOTED the vocabulary limitation, then
declared the illegal share_even; the executor crashed on arity.

This test re-executes THAT ARCHIVED TRANSCRIPTION (zero API cost) with the
corrected declaration - col weighted_avg, weights = the A-7 counts table -
and scores it against the human workbook.
Run: python pipeline/test_ops_sd_wage.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

RUN = os.path.join(os.path.dirname(HERE), "runs", "sd_Age_Serv_Wage_20260710_124156")
WORKBOOK = os.path.join(os.path.dirname(HERE), "..", "Data", "Plans", "Cities",
                        "sd_modeldata", "sd_data19_gen.xlsx")


def main():
    with open(os.path.join(RUN, "extraction.json"), encoding="utf-8") as fh:
        archived = json.load(fh)

    tables = archived["source_tables"]
    # archived order: table 0 = average salaries (A-8), table 1 = counts (A-7)
    assert "Average Salary" in tables[0]["title"], tables[0]["title"]
    assert "counts" in tables[1]["title"].lower(), tables[1]["title"]

    # corrected declaration: the two column MERGES become weighted_avg with
    # the counts table as weights (the model's share_even was the illegal
    # least-bad fallback it itself flagged in notes)
    col_map = []
    for cm in archived["col_map"]:
        if len(cm["sources"]) > 1:
            col_map.append({"target": cm["target"], "sources": cm["sources"],
                            "op": "weighted_avg", "weights_table": 1})
        else:
            col_map.append(cm)
    row_map = archived["row_map"]          # already correct (weighted_avg '70')

    derived = ops.execute(tables, row_map, col_map)

    truth = harness.load_truth(WORKBOOK, "Age_Serv_Wage")
    report = harness.score(truth, derived)
    harness.print_report(report)

    ok = report["exact"] + report["close"] + report["star_ok"]
    total = report["exact"] + report["close"] + report["wrong"] + report["star_ok"]
    print(f"exact+close+star = {ok} of {total} compared cells")
    assert ok >= 0.9 * total, "too many mismatches - adjudicate before accepting"
    print("PASS: archived sd transcription + column weighted_avg reproduces the workbook"
          " (adjudicate any residual mismatches against the PDF)")


if __name__ == "__main__":
    main()
