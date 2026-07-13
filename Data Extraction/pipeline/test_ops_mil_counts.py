"""Executor verification for derive=sum (cross-table additive counts).

Milwaukee's AV publishes active member counts as three same-shaped group
tables: General Employees, Policemen, and Firemen. The live run of 2026-07-13
(mil_Age_Serv_Num_20260713_161425) transcribed all three tables correctly and
its notes said exactly what deterministic code must do: sum the group tables
cell-wise. ops.py had no document-level sum operation, so the run scored only
the General table.

This test re-executes THAT ARCHIVED TRANSCRIPTION (zero API cost) under the
corrected declaration - derive=sum(t0,t1,t2) - and scores it against the one
Milwaukee sheet that has human truth.
Run: python pipeline/test_ops_mil_counts.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import ops      # noqa: E402

RUN = os.path.join(os.path.dirname(HERE), "runs", "mil_Age_Serv_Num_20260713_161425")
WORKBOOK = os.path.join(os.path.dirname(HERE), "..", "Data", "Plans", "Cities",
                        "mil_modeldata", "mil_data19_gen.xlsx")


def main():
    with open(os.path.join(RUN, "extraction.json"), encoding="utf-8") as fh:
        archived = json.load(fh)

    tables = archived["source_tables"]
    assert len(tables) == 3, len(tables)
    assert "General" in tables[0]["title"], tables[0]["title"]
    assert "Policemen" in tables[1]["title"], tables[1]["title"]
    assert "Firemen" in tables[2]["title"], tables[2]["title"]

    derive = {"op": "sum", "tables": [0, 1, 2]}
    derived = ops.execute(tables, archived["row_map"], archived["col_map"],
                          derive=derive)

    truth = harness.load_truth(WORKBOOK, "Age_Serv_Num")
    report = harness.score(truth, derived, zero_equals_empty=True)
    harness.print_report(report)

    source_total = sum(sum(v or 0 for v in row) for t in tables for row in t["cells"])
    truth_total = sum(sum(v or 0 for v in row) for row in truth["cells"])
    print(f"source group total = {source_total}; truth total = {truth_total}")

    for k, t in enumerate(tables):
        problems = ops.totals_check(t)
        assert not problems, f"table {k} totals check: {problems}"
    print("printed totals check: OK on all three group tables")

    assert report["exact"] == 80, report
    assert report["wrong"] == report["missing_in_cand"] == report["extra_in_cand"] == 0, report
    assert source_total == truth_total == 10974, (source_total, truth_total)
    print("PASS: archived Milwaukee transcription + derive=sum reproduces the workbook")


if __name__ == "__main__":
    main()
