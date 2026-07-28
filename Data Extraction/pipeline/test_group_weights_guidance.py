"""group_weighted without weights_tables: make the retry actionable.

chi_gen and sd Avg_Mort each burned ALL 8 attempts against the bare rule
("group_weighted requires weights_tables") and crashed. Meanwhile 10 of the 14
plans that produced an Avg_Mort blend got it right, and 6 of those pass ONE
distribution table repeated per source (lax_gen/lax_uty/lax_ffpol [2,2],
chi_edu [2,2,2,2], hou_pol [1,1,1,1], phx [1,1,2,2]). So the likely confusion
is believing a DISTINCT weights table per group is required - when the document
publishes a single membership distribution, there is no such table to find.

Under test: the rejection now (a) states the indices may repeat and shows the
shape, and (b) lists the tables actually transcribed, so the retry can pick one
by title instead of guessing. Also asserts a repeated index is accepted and
executes.

Anchored on the real lax_gen declaration (Avg_Mort, weights_tables [2, 2] over
'Distribution of Active Members as of June 30, 2019').
Run: python pipeline/test_group_weights_guidance.py
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
                          encoding="utf-8"))["Avg_Mort"]
    run = harness.find_run("lax_gen_Avg_Mort_20260727_155221")
    with open(os.path.join(run, "extraction.json"), encoding="utf-8") as fh:
        good = json.load(fh)
    good["col_map"][0].pop("values_unit", None)      # redundant; table declares it

    # the real declaration, with ONE table serving BOTH sources, is accepted
    assert good["col_map"][0]["weights_tables"] == [2, 2], good["col_map"][0]
    assert extract.validate(copy.deepcopy(good), spec) == [], \
        extract.validate(copy.deepcopy(good), spec)
    print("  a repeated weights_tables index ([2, 2]) validates cleanly")

    # and it executes down the REAL path (the exhibit prints percentages, and
    # Avg_Mort declares convert_percent_to_decimal - without it the "blend"
    # comes out 100x too big, e.g. 0.035 at age 20)
    g = ops.execute(good["source_tables"], good["row_map"], good["col_map"],
                    derive=good.get("derive"),
                    target_row_spans=spec.get("target_row_spans"),
                    to_decimal=spec.get("convert_percent_to_decimal", False))
    by_age = {lab: row[0] for lab, row in zip(g["row_labels"], g["cells"])
              if isinstance(row[0], (int, float))}
    assert by_age, "blend produced no numbers"
    # a mortality curve: young ages are tiny, and it rises monotonically-ish
    assert by_age["20"] < 0.001, by_age["20"]
    assert by_age["20"] < by_age["45"] < by_age["65"], by_age
    print(f"  executes: q20={by_age['20']:.6f} q45={by_age['45']:.6f} "
          f"q65={by_age['65']:.6f} ({len(by_age)} ages blended)")

    # drop weights_tables -> the chi_gen/sd failure shape
    bad = copy.deepcopy(good)
    bad["col_map"][0].pop("weights_tables")
    probs = extract.validate(bad, spec)
    msg = next((x for x in probs if "weights_tables" in x), None)
    assert msg, probs
    assert "do NOT have to be different" in msg, msg
    assert '"weights_tables": [2, 2]' in msg, msg          # the concrete shape
    assert "a list of 2 source_tables indices" in msg, msg  # matches source count
    assert "Distribution of Active Members" in msg, msg     # names the real table
    print("  rejection names the shape AND the transcribed table to use")

    # wrong LENGTH is rejected too (one index for two sources)
    short = copy.deepcopy(good)
    short["col_map"][0]["weights_tables"] = [2]
    assert any("weights_tables" in x for x in extract.validate(short, spec))
    print("  a weights_tables shorter than sources is rejected")

    print("PASS: group_weighted guidance is actionable - repeat-an-index is "
          "stated, and the candidate tables are listed by title")


if __name__ == "__main__":
    main()
