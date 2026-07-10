"""Executor verification for the RATIO derive op (average = total$/count).

Chicago Police's AV publishes NO average-salary exhibit - Exhibit C Part III
(p.46) gives total lives and total annual salary dollars by age x service.
The live run of 2026-07-10 (chi_pol_Age_Serv_Wage_20260710_121937) transcribed
both tables correctly and its notes said exactly what deterministic code must
do (average = total salary / count), but ops.py had no ratio operation, so the
declared weighted_avg maps executed over the counts table and scored 0.0.

This test re-executes THAT ARCHIVED TRANSCRIPTION (zero API cost) under the
corrected declaration - derive=ratio(salary$, counts) with additive maps - and
scores it against the human workbook. Run: python pipeline/test_ops_chipol_wage.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

RUNS = os.path.join(os.path.dirname(HERE), "runs")
RUN = os.path.join(RUNS, "chi_pol_Age_Serv_Wage_20260710_121937")
WORKBOOK = os.path.join(os.path.dirname(HERE), "..", "Data", "Plans", "Cities",
                        "chi_modeldata", "chi_data19_pol.xlsx")


def main():
    with open(os.path.join(RUN, "extraction.json"), encoding="utf-8") as fh:
        archived = json.load(fh)

    tables = archived["source_tables"]
    # archived order: table 0 = counts (lives), table 1 = total salary dollars
    assert "Lives" in tables[0]["title"], tables[0]["title"]
    assert "Salaries" in tables[1]["title"], tables[1]["title"]

    # the corrected declaration: same targets/sources the model declared, but
    # additive row ops + ratio derive instead of weighted_avg over counts
    row_map = [{"target": rm["target"], "sources": rm["sources"],
                "op": "sum", "weights_table": None}
               for rm in archived["row_map"]]
    col_map = archived["col_map"]          # already additive (sum)
    derive = {"op": "ratio", "numerator_table": 1, "denominator_table": 0}

    derived = ops.execute(tables, row_map, col_map, derive=derive)

    truth = harness.load_truth(WORKBOOK, "Age_Serv_Wage")
    report = harness.score(truth, derived)
    harness.print_report(report)

    # the archived transcription must also pass the (tolerance-fixed) totals
    # check: the +-1-dollar diffs are the AV's own printed-total rounding
    for k, t in enumerate(tables):
        problems = ops.totals_check(t)
        assert not problems, f"table {k} totals check: {problems}"
    print("totals check (with rounding tolerance): OK on both tables")

    assert report["exact"] + report["close"] + report["star_ok"] >= 36, report
    print("PASS: archived chi_pol transcription + ratio derive reproduces the workbook")


if __name__ == "__main__":
    main()
