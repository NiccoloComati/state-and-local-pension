"""LLM extraction step (Stage A): full document text -> source-native tables
+ DECLARED transformation operations. The model does NO arithmetic - it
transcribes tables exactly as printed and declares how their bins map onto
the target grid; ops.py executes the mapping deterministically.

Why: (1) the source-native tables are preserved for reproducibility/auditing
(page-level provenance the human collectors never recorded); (2) extraction
errors and transformation errors are separately measurable; (3) all
arithmetic is exact by construction.

Every call's full request + raw response is archived next to the output.

Requires ANTHROPIC_API_KEY in the environment:
    PowerShell:  $env:ANTHROPIC_API_KEY = "sk-ant-..."
Note: temperature/top_p are NOT sent - they are removed on current models
(the API returns 400 if present).
"""
import json
import os

MODEL = "claude-opus-4-8"
# Output-token budget. The Anthropic path keeps 32000 (Opus output cap); the
# local vLLM backend defaults higher because big multi-table docs (e.g. mil's
# 9 employer count tables) need >32000 tokens of JSON and were TRUNCATING mid-
# response in the 2026-07-23 sweep (6 crashes). 64000 output + a 90K-token doc
# + the retry conversation still fits the 262144 served context window.
# Override either backend with EXTRACT_MAX_TOKENS.
_DEFAULT_MAX_TOKENS = "64000" if os.environ.get("EXTRACT_OPENAI_BASE_URL") else "32000"
MAX_TOKENS = int(os.environ.get("EXTRACT_MAX_TOKENS", _DEFAULT_MAX_TOKENS))

# ---- open-weights backend (beta; see engaging_beta/runbook.md) ----
# Set EXTRACT_OPENAI_BASE_URL (e.g. http://localhost:8000/v1) to route Stage A
# to an OpenAI-compatible server (vLLM on Engaging) instead of the Anthropic
# API; EXTRACT_MODEL names the served model. The contract, the client-side
# validator, the retry loop, and Stage B are IDENTICAL on both backends. The
# local backend puts the document FIRST in the prompt (byte-identical prefix
# across the 6 targets -> vLLM automatic prefix caching); the Anthropic
# prompt layout is unchanged.
OPENAI_BASE_URL = os.environ.get("EXTRACT_OPENAI_BASE_URL")
OPENAI_MODEL = os.environ.get("EXTRACT_MODEL", "")
OPENAI_TIMEOUT = int(os.environ.get("EXTRACT_TIMEOUT_S", "3600"))
# best-of-N (local backend only): after the greedy attempt + one greedy
# correction retry, draw up to EXTRACT_SAMPLES independent samples at
# EXTRACT_TEMPERATURE and keep the one that best reconciles with the printed
# totals (the free verifier). Greedy decoding is deterministic, so re-running
# it cannot escape a column-shift; temperature diversity + the totals-check
# can. Set EXTRACT_SAMPLES=0 to disable (pure greedy + retry, e.g. for an A/B
# against the deterministic baseline). Per-sample seeds keep it reproducible.
OPENAI_SAMPLES = int(os.environ.get("EXTRACT_SAMPLES", "6"))
OPENAI_TEMPERATURE = float(os.environ.get("EXTRACT_TEMPERATURE", "0.6"))

_TABLE = {
    "type": "object",
    "properties": {
        "page": {"type": "integer",
                 "description": "PDF page number (from the === PDF PAGE n === markers)"},
        "title": {"type": "string",
                  "description": "the table's title/exhibit label as printed"},
        "row_labels": {"type": "array", "items": {"type": "string"},
                       "description": "row labels EXACTLY as printed in the source"},
        "col_labels": {"type": "array", "items": {"type": "string"},
                       "description": "column labels EXACTLY as printed in the source"},
        "cells": {
            "type": "array",
            "items": {"type": "array",
                      "items": {"anyOf": [{"type": "number"},
                                          {"type": "string"},
                                          {"type": "null"}]}},
            "description": "values exactly as printed; null for empty cells; '*' for suppressed cells; EXCLUDE total rows/columns from cells",
        },
        "printed_row_totals": {
            "anyOf": [{"type": "array",
                       "items": {"anyOf": [{"type": "number"}, {"type": "null"}]}},
                      {"type": "null"}],
            "description": "the table's printed per-row totals (one per row_label, aligned) if the table prints a Total column; else null. Used to VERIFY your transcription.",
        },
        "printed_col_totals": {
            "anyOf": [{"type": "array",
                       "items": {"anyOf": [{"type": "number"}, {"type": "null"}]}},
                      {"type": "null"}],
            "description": "the table's printed per-column totals (one per col_label, aligned) if the table prints a Total row; else null.",
        },
        "values_unit": {
            "anyOf": [{"type": "string", "enum": ["percent", "per_1000"]}, {"type": "null"}],
            "description": "the SCALE the table prints a RATE in, when the target wants a decimal probability. 'percent' = printed as percentages (22.50 meaning 22.5%; code /100). 'per_1000' = printed as a rate PER 1,000 members (e.g. a 'rate per 1,000' retirement/mortality table, 53.31 meaning 0.05331; code /1000). null = already a decimal, or not a rate. Transcribe the numbers AS PRINTED either way.",
        },
        "row_spans": {
            "anyOf": [{"type": "array",
                       "items": {"anyOf": [{"type": "array",
                                            "items": {"anyOf": [{"type": "integer"},
                                                                {"type": "null"}]},
                                            "minItems": 2, "maxItems": 2},
                                           {"type": "null"}]}},
                      {"type": "null"}],
            "description": "numeric [lo, hi] semantics of each printed row label (aligned with row_labels; null = open end or non-numeric label). Declare on tables whose bins code must match against target coordinates - e.g. a headcount table used as group_weighted weights ('50 to 54' -> [50, 54]). Else null.",
        },
        "col_spans": {
            "anyOf": [{"type": "array",
                       "items": {"anyOf": [{"type": "array",
                                            "items": {"anyOf": [{"type": "integer"},
                                                                {"type": "null"}]},
                                            "minItems": 2, "maxItems": 2},
                                           {"type": "null"}]}},
                      {"type": "null"}],
            "description": "numeric [lo, hi] semantics of each printed column label, aligned with col_labels; same rules as row_spans.",
        },
    },
    "required": ["page", "title", "row_labels", "col_labels", "cells",
                 "printed_row_totals", "printed_col_totals"],
    "additionalProperties": False,
}

_SPANS = {
    "anyOf": [
        {"type": "array",
         "items": {"type": "array",
                   "items": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                   "minItems": 2, "maxItems": 2}},
        {"type": "null"},
    ],
    "description": "overlap_weighted only: numeric [lo, hi] span of each source bin, aligned with sources; null = open end (e.g. '<15' -> [null, 14], '>31' -> [32, null]). Declare the printed labels' semantics - any ambiguity in bin boundaries goes here and in notes.",
}

_WEIGHTS_TABLES = {
    "anyOf": [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}],
    "description": "group_weighted only: one source_tables index PER SOURCE (aligned), each a transcribed headcount table providing that group's population weights (e.g. General/Safety member counts; actives/retirees counts). Weight tables whose bins differ from the target's coordinates need row_spans/col_spans declared.",
}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_tables": {
            "type": "array",
            "items": _TABLE,
            "description": "index 0 = the main source table; add auxiliary tables (e.g. counts used as weights, or same-shaped subgroup tables to be summed) after it",
        },
        "row_map": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"},
                                "description": "source row labels of source_tables[0] combined into this target row (empty if no data exists). If transpose=true these are the PRINTED COLUMN labels."},
                    "op": {"type": "string",
                           "enum": ["copy", "sum", "share_even", "weighted_avg",
                                    "overlap_weighted", "group_weighted"]},
                    "weights_table": {"anyOf": [{"type": "integer"}, {"type": "null"}],
                                      "description": "index into source_tables providing weights (weighted_avg only, else null)"},
                    "source_spans": _SPANS,
                    "weights_tables": _WEIGHTS_TABLES,
                },
                "required": ["target", "sources", "op", "weights_table"],
                "additionalProperties": False,
            },
        },
        "col_map": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"},
                                "description": "source col labels combined into this target col. If transpose=true these are the PRINTED ROW labels."},
                    "op": {"type": "string",
                           "enum": ["copy", "sum", "share_even", "weighted_avg",
                                    "overlap_weighted", "group_weighted", "ratio"]},
                    "weights_table": {"anyOf": [{"type": "integer"}, {"type": "null"}],
                                      "description": "index into source_tables providing count weights (weighted_avg only, else null). Column weighted_avg merges source COLUMNS of an averages table."},
                    "source_spans": _SPANS,
                    "weights_tables": _WEIGHTS_TABLES,
                    "numerator_sources": {
                        "type": "array", "items": {"type": "string"},
                        "description": "ratio SPLIT form: the source columns that are SUMMED to form the numerator (e.g. every annual-payments column, one per sex/group). Use with denominator_sources when the document prints the dollars and the counts once PER GROUP; 'sources' then lists all of them together.",
                    },
                    "denominator_sources": {
                        "type": "array", "items": {"type": "string"},
                        "description": "ratio SPLIT form: the source columns SUMMED to form the denominator - the COUNT columns (e.g. Male Number + Female Number). Never dollar columns: dollars/dollars is not an average.",
                    },
                    "annualize_monthly": {
                        "type": "boolean",
                        "description": "true ONLY on a copy/ratio column whose source dollars are printed MONTHLY while the target wants ANNUAL - code multiplies the column by 12",
                    },
                },
                "required": ["target", "sources", "op"],
                "additionalProperties": False,
            },
        },
        "derive": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "op": {"type": "string", "enum": ["ratio"]},
                        "numerator_table": {"type": "integer"},
                        "denominator_table": {"type": "integer"},
                        "annualize_monthly": {
                            "type": "boolean",
                            "description": "true when the numerator prints MONTHLY dollars while the target wants ANNUAL: code multiplies the RATIO RESULT by 12. Put it HERE (not on a column) - a column-level annualize_monthly cancels inside a ratio because it scales numerator and denominator alike.",
                        },
                    },
                    "required": ["op", "numerator_table", "denominator_table"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "op": {"type": "string", "enum": ["sum"]},
                        "tables": {"type": "array", "items": {"type": "integer"},
                                   "minItems": 2},
                    },
                    "required": ["op", "tables"],
                    "additionalProperties": False,
                },
            ],
            "description": "null normally. Use {op:'ratio',...} when the document publishes TOTALS instead of target averages. Use {op:'sum', tables:[...]} when the additive target is split across same-shaped subgroup tables; code sums them cell-wise before mapping.",
        },
        "transpose": {
            "type": "boolean",
            "description": "true when the printed table's orientation is the REVERSE of the target's (e.g. printed age rows x service cols, target service rows x age cols). Transcribe as printed; code transposes before mapping. When true, row_map maps the printed COLUMNS onto target rows and col_map maps the printed ROWS onto target columns.",
        },
        "unavailable": {
            "type": "boolean",
            "description": "true ONLY when the target quantity does not exist in the document in any derivable form; then row_map/col_map are empty lists and notes explain what the document publishes instead",
        },
        "broadcast": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "axis": {"type": "string", "enum": ["age", "service"]},
                        "series_sources": {"type": "array", "items": {"type": "string"},
                                           "minItems": 1},
                        "series_op": {"type": "string", "enum": ["copy", "mean"]},
                    },
                    "required": ["axis", "series_sources", "series_op"],
                    "additionalProperties": False,
                },
            ],
            "description": "null normally. Set it when the exhibit measures the rate along ONE dimension only. Transcribe the source with the VARYING dimension as ROWS and the rate as COLUMNS. axis='age' when the source gives rates by SERVICE only (no age) -> every target age row is filled with the same service-based rate; col_map maps target service columns from the source's service rows and row_map lists the age targets with EMPTY sources. axis='service' when the source gives rates by AGE only (no service) -> every target service column is identical; row_map maps target ages from the source's age rows and col_map lists the service targets with empty sources. series_sources = the rate COLUMN label(s); series_op='copy' for a single rate column, 'mean' to average several (e.g. Male and Female with no headcounts to weight by).",
        },
        "notes": {
            "type": "string",
            "description": "every judgment call: why these tables, ambiguities, anything the maps cannot express",
        },
    },
    "required": ["source_tables", "row_map", "col_map", "derive", "transpose", "notes"],
    "additionalProperties": False,
}

SYSTEM = """You extract actuarial tables from U.S. public pension actuarial valuation \
reports. You receive the FULL text of a document (pages marked === PDF PAGE n ===) and \
a target grid specification.

The document text is LAYOUT-PRESERVED: within a table, a value's horizontal \
position indicates its column. Use the header positions to assign each value to \
its column - especially for rows with leading empty cells, where counting values \
left-to-right would misplace them.

Your job has two strictly separated parts:
1. TRANSCRIBE: locate the source table(s) containing the target data (firms title and \
format them differently - judge by content) and transcribe them EXACTLY as printed: \
original bin labels, original values, null for empty cells, '*' for suppressed cells. \
Never compute, round, merge, or invent anything at this step. Exclude total rows/columns. \
INTERLEAVED EXHIBITS (very common): one printed table often shows TWO lines per \
age band - a member-COUNT line and a dollar line (average pay, or total salary) - \
sharing one set of age row labels and service column headers. Transcribe it as TWO \
source_tables with IDENTICAL row_labels/col_labels, one line type each (say which in \
each title), and reference the counts table by index (weights_table for weighted_avg, \
or denominator_table for a ratio). NEVER put both line types in one table's cells: \
that yields twice as many cell rows as row_labels and is rejected. \
TRANSCRIBE THE FEWEST TABLES THAT COVER EVERY MEMBER EXACTLY ONCE. Documents \
publish the same distribution at MANY levels of aggregation - by sex (Male/Female), by \
tier (Tier 1/Tier 2), and especially by EMPLOYER / AGENCY / DEPARTMENT sub-unit - each \
with its own subtotal, plus rolled-up GROUP TOTALS. Transcribe only the top-level tables \
that PARTITION the whole plan once, and NEVER transcribe both a total and its sub-parts \
(that double-counts). Concretely: if a group is split across employer/department tables \
(e.g. 'General City', 'Water Department', 'School Board', ...) AND a 'General Employees - \
Total' table is printed, transcribe ONLY the 'General - Total' - never the per-employer \
tables, never also the per-tier tables for that same group. Prefer any single 'Total' / \
'All Participants' / 'All Active Members' / 'Total City' table when one exists. The set \
you transcribe must sum to the plan's printed grand total (verify) - e.g. a system with \
General + Police + Fire is exactly THREE total tables, not the dozen agency/tier \
sub-tables. Use derive=sum over the group totals only when no single all-members table is \
printed. Fewer tables = far less chance of a misread and no double-counting.
SIDE-BY-SIDE TABLES (very common): a page often prints two or three SEPARATE \
exhibits next to each other, and the text layer merges their rows onto shared \
lines. One line can therefore carry values from two different tables, and a third \
table's rows can appear between them at irregular intervals - e.g. a line reading \
"20  50.0% 55.0 25.0% 50.0" is service 20 of the GENERAL table (2 values) followed \
by service 20 of the SAFETY table (2 values), while a nearby line reading "61 15.0" \
belongs to a third age-based table entirely. Identify each table by its OWN caption \
and column headers (Table B-7, Table B-8, ...), then transcribe ONLY the columns \
belonging to the table you need, ignoring the neighbour's values on the same line \
and skipping lines that belong to a different table. Never merge two captions into \
one table, and never let a neighbour's column become a column of yours. If only one \
of the tables is relevant to the target, transcribe just that one and say in notes \
which others share the page. \
2. DECLARE: describe how the source bins map onto the target grid as row_map/col_map \
operations (copy, sum, share_even, weighted_avg for rows; copy, sum, share_even, \
weighted_avg, ratio for columns). \
Deterministic code will execute these - you do NO arithmetic. If a weighted average is \
needed (e.g. merging salary bins), also transcribe the table that provides the weights \
(e.g. member counts) as an additional source table and reference it by index. \
If a target COLUMN is a per-row quotient of two source columns (e.g. average benefit = \
total annual dollars / member count printed side by side), use col op "ratio" with \
exactly two sources [numerator, denominator] - code divides row by row; if the source \
dollars are printed MONTHLY and the target wants ANNUAL, add "annualize_monthly": true \
to that column entry (code multiplies by 12 - never convert units yourself). \
The denominator of such a quotient is ALWAYS a member count column. If the exhibit \
prints the dollars and the counts once per GROUP (e.g. Male Number | Male Annual \
Payments | Female Number | Female Annual Payments) and prints no Total column, two \
sources cannot express the target: declare "numerator_sources" = every dollar column \
and "denominator_sources" = every count column (with "sources" listing all of them), \
and code sums each side before dividing. Never divide one group's dollars by another \
group's dollars, and never report just one group as if it were the whole population. \
If one printed ROW bucket covers several target rows (e.g. '90 & Up' across \
90-94/95-99/100+), map EACH covered target row to it with op "share_even": code splits \
the bucket's values evenly across those rows (additive columns split; a ratio column \
then reproduces the bucket average automatically). \
If the document publishes TOTALS instead of the averages the target wants (e.g. total \
salary dollars per cell plus member counts, but no average-salary exhibit), transcribe \
BOTH tables and declare derive = {"op": "ratio", "numerator_table": <totals>, \
"denominator_table": <counts>}: code aggregates both tables with your maps (additive \
ops only - sum/copy, NOT weighted_avg) and divides cell-wise. If those totals are \
MONTHLY dollars while the target wants ANNUAL (check the exhibit's own stated average, \
or divide the printed grand total by the member count - a monthly salary average is a \
few thousand, an annual one tens of thousands), add "annualize_monthly": true INSIDE \
the derive object - code multiplies the RATIO RESULT by 12. Do NOT put annualize_monthly \
on a column in ratio mode: there it scales the numerator and the denominator alike and \
cancels out. Transcribe the printed monthly numbers unchanged either way. \
If the document publishes \
an ADDITIVE target (e.g. active member counts) separately by employee group, transcribe \
all same-shaped group tables and declare derive = {"op": "sum", "tables": [<indices>]}: \
code sums those tables cell-wise before applying your maps. Otherwise derive is null. \
If the printed orientation is the reverse of the target's, set transpose=true \
(transcribe as printed; code transposes; row_map then maps the printed COLUMNS onto \
target rows). For RATE tables whose bins do not align with the target bins, use op \
"overlap_weighted" and declare each source bin's numeric span in "source_spans" \
([lo, hi], null = open end, e.g. "<15" -> [null, 14]): code blends the rates \
proportionally to how many years of the target bin fall in each source bin. Rates are \
intensive - never sum them; a target bin inside one source bin just copies its rate. \
If a rate table is printed on a SCALE while the target wants a decimal probability, \
transcribe the numbers as printed and declare the scale in values_unit: "percent" for \
percentages (22.50 -> 0.225), "per_1000" for a 'rate per 1,000 members' table (53.31 -> \
0.05331) - code does the division. (A rate whose printed values exceed ~1 but the target \
is a probability is always one of these scales - never leave values_unit null then.) \
If a rate exhibit measures the rate along ONE dimension only - termination/withdrawal \
rates by YEARS OF SERVICE with no age breakdown, or by AGE with no service breakdown - \
do NOT declare it unavailable and do NOT invent the missing dimension's bins. Transcribe \
the source with the VARYING dimension as ROWS and the rate as COLUMNS, and declare \
"broadcast": {"axis": ..., "series_sources": [...], "series_op": ...}. Use axis="age" \
when the rate is by SERVICE only (code repeats the same service-based rate across every \
age - faithful to the plan assuming termination depends on service, not age): col_map \
maps each target service column from the source's service-year rows (op copy, or \
overlap_weighted with source_spans when service bins do not align), and row_map lists \
the target age rows each with an EMPTY sources list. Use axis="service" when the rate is \
by AGE only: row_map maps each target age row from the source's age rows, and col_map \
lists the target service columns each with EMPTY sources. series_sources = the rate \
COLUMN label(s); series_op="copy" for a single rate column, "mean" to average several \
(e.g. Male and Female when no headcount table is printed to weight by; if the plan is \
one specific group, name only that group's column with copy). broadcast is null \
whenever the exhibit genuinely gives the rate by BOTH age and service. \
If the document publishes the target separately per POPULATION GROUP (e.g. General vs \
Safety termination rates; pre- vs post-retirement mortality) and the target wants one \
blended value, use op "group_weighted": sources = the group rows/columns, and \
"weights_tables" = one source_tables index PER source, in the same order, each a \
transcribed headcount table (e.g. the membership distribution). Code looks the \
weight up at the bin containing each output cell and computes the population-weighted \
blend - declare row_spans/col_spans on any weights table whose printed bins differ \
from the target's coordinates (e.g. "50 to 54" -> [50, 54]). The indices need not be \
distinct: if ONE membership-distribution exhibit covers every group (the usual case), \
transcribe it once and repeat its index, e.g. two sources blended by table 2 give \
"weights_tables": [2, 2]. weights_tables is never omitted - without it the blend has \
no populations to weight by and the extraction is rejected.

Every target row/column must appear exactly once in the maps, in target-grid order. \
If data for a target bin does not exist anywhere in the document, give it an empty \
sources list. If the ENTIRE target (or a whole dimension of its grid) is not published \
in any derivable form, set "unavailable": true, leave row_map and col_map as EMPTY \
lists, and use notes to state exactly what the document publishes instead; you may \
transcribe the closest related tables into source_tables as archived evidence. Never \
approximate a missing dimension (e.g. copying an age-only average across every service \
column) - that is a modeling assumption for humans to decide, not an extraction. \
Record every judgment call in notes."""


FORMAT_SPEC = """OUTPUT FORMAT - return ONLY a JSON object with EXACTLY this structure
(no code fences, no extra keys, no alternative shapes):
{
  "source_tables": [
    {"page": 38, "title": "printed table title",
     "row_labels": ["Under 20", "20-24"],
     "col_labels": ["0-4", "5-9"],
     "cells": [[4, null], [150, null]],
     "printed_row_totals": [4, 150],
     "printed_col_totals": [154, null]}
  ],
  "row_map": [
    {"target": "<25", "sources": ["Under 20", "20-24"], "op": "sum", "weights_table": null}
  ],
  "col_map": [
    {"target": "4", "sources": ["0-4"], "op": "copy"}
  ],
  "derive": null,
  "transpose": false,
  "notes": "one plain string, not a list"
}
Constraints:
- source_tables[k].cells is a LIST OF LISTS of values (number, "*", or null),
  one inner list per row_label, one value per col_label. NOT objects.
- row_map/col_map "sources" are PLAIN STRINGS (row/col labels of
  source_tables[0]). NOT objects. Auxiliary tables are referenced only via
  "weights_table" (an integer index into source_tables, or null).
- row ops: "copy" | "sum" | "share_even" | "weighted_avg" | "overlap_weighted" |
  "group_weighted"; col ops: "copy" | "sum" | "share_even" | "weighted_avg" |
  "overlap_weighted" | "group_weighted" | "ratio".
  "copy" and "share_even" take EXACTLY ONE source. Merging bins of an
  AVERAGES table (rows or columns) is ALWAYS "weighted_avg" with
  "weights_table" pointing at the transcribed counts table - never sum or
  share_even (averages are not additive).
- col op "ratio" takes EXACTLY TWO sources [numerator, denominator]: the
  target column is their per-row quotient (e.g. average benefit = total
  dollars column / count column). The DENOMINATOR is always a member COUNT -
  dividing one dollar column by another dollar column is never an average.
  SPLIT form: when the exhibit prints the dollars AND the counts once per
  GROUP (Male Number | Male Annual Payments | Female Number | Female Annual
  Payments) and prints no Total column, two sources cannot say what you mean.
  Declare instead "numerator_sources": [every dollar column],
  "denominator_sources": [every count column], with "sources" listing all of
  them; code sums each side, then divides. Never pick just one group's pair.
  Row "share_even" splits one printed row
  bucket evenly across every target row that references it - additive
  columns are divided by the split count; a ratio column then equals the
  bucket's own average on each split row.
- "annualize_monthly": true only on a copy/ratio COLUMN whose source dollars
  are printed MONTHLY while the target wants ANNUAL - code multiplies that
  column by 12. Never convert units yourself.
- "overlap_weighted" (RATE tables with non-aligned bins) requires
  "source_spans": one [lo, hi] integer span per source (null = open end).
  Code blends rates proportionally by year overlap with the target bin.
- "group_weighted" (blending POPULATION GROUPS into one value) requires
  "weights_tables": one source_tables index per source, IN THE SAME ORDER as
  "sources". Code looks up each group's population at the output cell's
  coordinates (declare row_spans/col_spans on weight tables whose bins differ
  from the target's) and blends by population. The indices need not be
  distinct: when ONE membership table covers every group, repeat it. Worked
  example - a mortality exhibit printed Male/Female, blended by a single
  active-member distribution transcribed as table 2:
    "source_tables": [
      {"page": 69, "title": "Pre-Retirement Mortality Rates",
       "row_labels": ["20", "25", "30"], "col_labels": ["Male", "Female"],
       "cells": [[0.05, 0.02], [0.06, 0.03], [0.07, 0.04]],
       "row_spans": [[20, 24], [25, 29], [30, 34]], "values_unit": "percent",
       "printed_row_totals": null, "printed_col_totals": null},
      {"page": 53, "title": "Distribution of Active Members",
       "row_labels": ["Under 25", "25 - 29"], "col_labels": ["Total"],
       "cells": [[311], [1032]], "row_spans": [[null, 24], [25, 29]],
       "printed_row_totals": null, "printed_col_totals": null}
    ],
    "col_map": [{"target": "Death_Prob", "sources": ["Male", "Female"],
                 "op": "group_weighted", "weights_tables": [1, 1]}]
  Note weights_tables has TWO entries for TWO sources even though both point
  at the same table, and that the weights table carries row_spans because its
  bins are coarser than the target's single ages.
- "transpose": true when the printed orientation is the reverse of the
  target's; transcribe as printed, code transposes the MAIN table
  (source_tables[0]) before mapping - auxiliary tables keep their printed
  orientation.
- "row_spans"/"col_spans" (per table, optional): numeric [lo, hi] semantics of
  the printed bin labels, aligned with row_labels/col_labels (null = open end
  or non-numeric label). Required on group_weighted weights tables whose bins
  are coarser than the target grid.
- a source rate table on a scale gets "values_unit": "percent" (printed as %)
  or "per_1000" (printed as a rate per 1,000 members) - numbers still
  transcribed exactly as printed; code divides by 100 or 1,000.
- "derive" is null UNLESS one of these document-level computations is needed:
  (a) the document publishes totals instead of the target's averages: transcribe
  BOTH tables (same bin labels) and set
  {"op": "ratio", "numerator_table": <index of the totals table>,
  "denominator_table": <index of the counts table>}. In ratio mode all row ops
  must be additive (sum/copy, never weighted_avg) - code aggregates both
  tables with the same maps, then divides cell-wise (average = total/count).
  If those totals are MONTHLY and the target wants ANNUAL, add
  "annualize_monthly": true INSIDE this derive object (code x12's the ratio
  RESULT). It does NOT belong on a column in ratio mode - there it scales
  numerator and denominator alike and cancels.
  (b) the document publishes an ADDITIVE target split across same-shaped
  subgroup tables (e.g. General + Police + Fire member counts): transcribe all
  subgroup tables and set {"op": "sum", "tables": [<indices>]}. In sum mode,
  table labels must match and all maps must be additive (sum/copy/share_even).
- printed_row_totals / printed_col_totals are for ADDITIVE SUM totals ONLY (a
  printed 'Total' row/column that equals the sum of the cells - counts, dollar
  totals). Code checks them against your cells to catch column-alignment
  mistakes. If the table prints AVERAGES (e.g. an average-salary exhibit), a
  printed 'Average' row/column is NOT a sum of the cells - set
  printed_row_totals / printed_col_totals to NULL for it (do not put averages
  there; the check would falsely fire). Also null when the table prints no
  totals. When they ARE additive totals, align each value carefully by its
  column position - interleaved / whitespace-collapsed layouts make a
  one-column-off slip easy, and the totals check is what catches it.
- "broadcast": null normally. Set it when a RATE exhibit measures the rate
  along ONE dimension only, so the other target axis repeats the same rate.
  {"axis": "age", "series_sources": ["Rate"], "series_op": "copy"} = the source
  gives rates by SERVICE only; col_map maps each target service column from the
  source's service-year rows (op copy / overlap_weighted), row_map lists the
  target age rows with EMPTY sources, and code fills every age identically.
  {"axis": "service", ...} = rates by AGE only; row_map maps target ages from
  the source's age rows, col_map lists the service columns with EMPTY sources.
  series_sources = the rate COLUMN label(s); series_op "copy" (one column) or
  "mean" (average several, e.g. Male+Female with no headcounts). Transcribe the
  source with the VARYING dimension as ROWS. Do NOT combine broadcast with
  derive/transpose/unavailable. This is NOT "approximating a missing
  dimension" - it is the faithful reading of a rate the plan defines on one
  variable; use it instead of unavailable for one-dimensional rate exhibits.
- "unavailable": false normally (may be omitted). Set true ONLY when the
  target does not exist in the document in any derivable form: then row_map
  and col_map MUST be EMPTY lists, derive must be null, notes must state what
  the document publishes instead, and source_tables may hold the closest
  related tables (transcribed exactly as printed, archived as evidence) or be
  empty. Never fill a target grid by approximating a dimension the document
  does not publish.
- "notes" is a single string."""


def build_prompt(target_name, target_spec, source_text, doc_first=False):
    g = target_spec["grid"]
    rules = "\n".join(f"- {r}" for r in target_spec["rules"])
    head = f"""TARGET: {target_name}
WHAT IT IS: {target_spec['description']}
UNIT: {target_spec['unit']}

TARGET GRID (row_map/col_map targets must be exactly these, in this order):
- target rows: {json.dumps(g['row_labels'])}
  ({g.get('rows_meaning', '')})
- target cols: {json.dumps(g['col_labels'])}
  ({g.get('cols_meaning', '')})

MAPPING GUIDANCE FOR THIS TARGET:
{rules}

{FORMAT_SPEC}"""
    tail = ("Transcribe the source table(s) exactly as printed, then declare "
            "the bin mappings.\nReturn ONLY the JSON object.")
    if doc_first:
        # document first = byte-identical prefix across targets (prefix cache)
        return f"FULL DOCUMENT TEXT:\n{source_text}\n\n{head}\n\n{tail}"
    return f"{head}\n\nFULL DOCUMENT TEXT:\n{source_text}\n\n{tail}"


def _parse(text):
    """json.loads with tolerance for code fences / leading prose."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    if not s.lstrip().startswith("{"):
        i = s.find("{")
        if i >= 0:
            s = s[i:]
    return json.loads(s)


def validate(result, target_spec=None):
    """Client-side contract validation (the API may not enforce our schema,
    e.g. behind proxies that drop output_config). Returns list of problems."""
    p = []
    if not isinstance(result, dict):
        return ["top level is not a JSON object"]
    for key in ("source_tables", "row_map", "col_map", "notes"):
        if key not in result:
            p.append(f"missing top-level key {key!r}")
    if p:
        return p

    unavailable = result.setdefault("unavailable", False)   # tolerated if absent
    if not isinstance(unavailable, bool):
        p.append("unavailable must be a boolean")
        unavailable = False

    tables = result["source_tables"]
    if not isinstance(tables, list):
        p.append("source_tables must be a list")
        tables = []
    elif not tables and not unavailable:
        p.append('source_tables is empty - if the target data does not exist in '
                 'this document in any derivable form, set "unavailable": true '
                 'with EMPTY row_map/col_map and notes explaining what the '
                 'document publishes instead; otherwise transcribe the source '
                 'table(s)')
    for k, t in enumerate(tables):
        if not isinstance(t, dict):
            p.append(f"source_tables[{k}] is not an object")
            continue
        for key, typ in (("page", int), ("title", str),
                         ("row_labels", list), ("col_labels", list)):
            if not isinstance(t.get(key), typ):
                p.append(f"source_tables[{k}].{key} missing or not {typ.__name__}")
        # duplicate labels make label-based row/col maps AMBIGUOUS: the executor
        # resolves a repeated label to the LAST occurrence, silently. (mil
        # Retirement 2026-07-27: a two-panel table with 'Total' for BOTH the
        # count total and the monthly-$ total -> Number mapped to the $ column
        # and AverageBenefit=ratio($,$)=1 x12=12.) Force distinct labels.
        for key in ("row_labels", "col_labels"):
            labs = t.get(key)
            if isinstance(labs, list):
                seen, dups = set(), []
                for lab in labs:
                    s = str(lab).strip()
                    if s in seen and s not in dups:
                        dups.append(s)
                    seen.add(s)
                if dups:
                    p.append(f"source_tables[{k}].{key} has DUPLICATE labels {dups} - "
                             "label-based maps become ambiguous (code silently takes "
                             "the last). Give each a DISTINCT label; if the table has "
                             "two panels under repeated headers (e.g. a COUNT panel and "
                             "a dollar panel both showing Male/Female/Total), "
                             "disambiguate them, e.g. 'Total Count' vs 'Total Monthly "
                             "Benefit', and map each target column to the right one.")
        for key in ("printed_row_totals", "printed_col_totals"):
            tv = t.setdefault(key, None)   # tolerated if absent
            if tv is not None:
                if not isinstance(tv, list) or any(
                        v is not None and not isinstance(v, (int, float)) for v in tv):
                    p.append(f"source_tables[{k}].{key} must be a list of numbers/nulls or null")
        vu = t.setdefault("values_unit", None)   # tolerated if absent
        if vu is not None and vu not in ("percent", "per_1000"):
            p.append(f"source_tables[{k}].values_unit must be 'percent', 'per_1000', "
                     "or null (a printed rate scaled as % or per-1,000; else null)")
        for key, labels_key in (("row_spans", "row_labels"), ("col_spans", "col_labels")):
            sp = t.setdefault(key, None)   # tolerated if absent
            if sp is None:
                continue
            labels = t.get(labels_key)
            if (not isinstance(sp, list)
                    or (isinstance(labels, list) and len(sp) != len(labels))
                    or any(s is not None and (
                        not isinstance(s, list) or len(s) != 2
                        or any(v is not None and not isinstance(v, int) for v in s))
                        for s in sp)):
                p.append(f"source_tables[{k}].{key} must be null or one [lo, hi] "
                         f"integer span (or null) per {labels_key} entry, aligned")
        cells = t.get("cells")
        if not isinstance(cells, list):
            p.append(f"source_tables[{k}].cells missing or not a list of lists"
                     " (do NOT use row objects like {{'label':..,'values':..}})")
        else:
            if isinstance(t.get("row_labels"), list) and len(cells) != len(t["row_labels"]):
                nlab = len(t["row_labels"])
                # INTERLEAVED exhibit: Segal-family tables print TWO physical
                # lines per age band - a COUNT line and a dollar line (average
                # payroll or total salary) - e.g. bos Exhibit A p.49, lax_gen
                # Exhibit B p.53. Flattening both line types into one `cells`
                # gives exactly 2x (or kx) the row_labels and crashed 3 cells of
                # the 2026-07-27 sweep (bos ASN, bos ASW, lax_gen ASW). Say what
                # to DO about it instead of just reporting the count mismatch.
                if nlab and len(cells) % nlab == 0 and len(cells) // nlab >= 2:
                    k_lines = len(cells) // nlab
                    p.append(
                        f"source_tables[{k}].cells has {len(cells)} rows = EXACTLY "
                        f"{k_lines}x its {nlab} row_labels: this is an INTERLEAVED "
                        "exhibit that prints several lines per age band (a member-COUNT "
                        "line and a dollar line - average pay or total salary). Do NOT "
                        f"flatten them into one table. Transcribe {k_lines} SEPARATE "
                        "source_tables, each with the SAME row_labels/col_labels and "
                        "one line type per table (e.g. source_tables[0] = the dollar "
                        "values, source_tables[1] = the counts), then reference the "
                        "counts table by index for weighted_avg (or as the ratio's "
                        "denominator_table). State in the title which line each holds.")
                elif len(cells) == nlab + 1:
                    # ONE extra row is almost always the printed grand-TOTAL line
                    # transcribed into cells without a matching label. chi_ff
                    # Exhibit B.1 p.32 (12 age bands + a 'Total' line) failed this
                    # way on 5 of 8 attempts and never recovered, which blocked the
                    # monthly-salary fix from ever executing. A total is not a bin:
                    # it belongs in printed_col_totals, where the reconciler uses it.
                    p.append(
                        f"source_tables[{k}].cells has {len(cells)} rows but {nlab} "
                        "row_labels - exactly ONE extra. The extra row is almost "
                        "always the printed grand-TOTAL line ('Total', 'All Members') "
                        "at the bottom of the exhibit. A total is NOT an age/service "
                        "bin: REMOVE that row from cells and put its values in "
                        "printed_col_totals instead (one value per col_label - code "
                        "checks them against the sum of your cells, which is how a "
                        "column-alignment slip gets caught). Same for a printed "
                        "'Total' COLUMN: it belongs in printed_row_totals, not in "
                        "col_labels/cells. If the extra row is genuinely a data bin, "
                        "add its label to row_labels so the two lists line up.")
                else:
                    p.append(f"source_tables[{k}].cells has {len(cells)} rows but "
                             f"{nlab} row_labels")
            for i, row in enumerate(cells):
                if not isinstance(row, list):
                    p.append(f"source_tables[{k}].cells[{i}] is not a list")
                    break
                for v in row:
                    if v is not None and not isinstance(v, (int, float, str)):
                        p.append(f"source_tables[{k}].cells[{i}] has invalid value {v!r}")
                        break

    row_ops = {"copy", "sum", "share_even", "weighted_avg", "overlap_weighted",
               "group_weighted"}
    col_ops = {"copy", "sum", "share_even", "weighted_avg", "overlap_weighted",
               "group_weighted", "ratio"}
    # Keys the executor actually READS on a map entry. Anything else is
    # silently ignored by ops.py, which is how sd and sf Retirement shipped:
    # both invented "numerator_table"/"denominator_table" ON THE COLUMN entry
    # (those are derive-level keys), code ignored them, and the ratio
    # degenerated to Total/Total = 1.0 for every row. An unknown key means the
    # model is trying to express something the contract does not support -
    # better a retry with guidance than a plausible-looking wrong number.
    ENTRY_KEYS = {"target", "sources", "op", "weights_table", "weights_tables",
                  "source_spans", "annualize_monthly",
                  "numerator_sources", "denominator_sources"}
    ELSEWHERE = {
        "numerator_table": "a derive-level key: derive={'op':'ratio',"
                           "'numerator_table':N,'denominator_table':M} divides "
                           "two whole TABLES. To divide two COLUMNS use col op "
                           "'ratio' with sources [numerator col, denominator "
                           "col], or numerator_sources/denominator_sources",
        "denominator_table": "a derive-level key (see numerator_table)",
        "values_unit": "declared on the SOURCE TABLE, not on a map entry - "
                       "code scales the table before mapping",
        "notes": "the single top-level 'notes' string",
    }
    gw_weight_tables, gw_used = set(), False
    for name, ops_allowed in (("row_map", row_ops), ("col_map", col_ops)):
        entries = result[name]
        if unavailable:
            if entries != []:
                p.append(f"unavailable=true requires {name} to be an EMPTY list - "
                         "either the target is derivable (then map it fully) or it "
                         "is not (then declare no mappings)")
            continue
        if not isinstance(entries, list) or not entries:
            p.append(f"{name} must be a non-empty list")
            continue
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                p.append(f"{name}[{i}] is not an object")
                continue
            if not isinstance(e.get("target"), str):
                p.append(f"{name}[{i}].target missing or not a string")
            for key in sorted(set(e) - ENTRY_KEYS):
                p.append(f"{name}[{i}] ({e.get('target')!r}): unknown key {key!r} - "
                         "the executor IGNORES it, so whatever it was meant to say "
                         "does not happen. " +
                         (f"{key!r} is {ELSEWHERE[key]}." if key in ELSEWHERE
                          else f"Remove it. Allowed: {sorted(ENTRY_KEYS)}"))
            srcs = e.get("sources")
            if not isinstance(srcs, list) or any(not isinstance(s, str) for s in srcs):
                p.append(f"{name}[{i}].sources must be a list of PLAIN STRINGS "
                         "(source row/col labels), not objects")
                srcs = None
            op = e.get("op")
            if op not in ops_allowed:
                p.append(f"{name}[{i}].op {op!r} not in {sorted(ops_allowed)}")
            if srcs is not None and op in ("copy", "share_even") and len(srcs) > 1:
                p.append(f"{name}[{i}] ({e.get('target')!r}): {op!r} takes exactly one "
                         "source. To MERGE bins use 'sum' (additive quantities) or "
                         "'weighted_avg' with weights_table = the counts table "
                         "(averages - never sum/share_even them)")
            n_s, d_s = e.get("numerator_sources"), e.get("denominator_sources")
            split = n_s is not None or d_s is not None
            if op != "ratio" and split:
                p.append(f"{name}[{i}] ({e.get('target')!r}): numerator_sources / "
                         "denominator_sources only belong on a 'ratio' column")
            elif op == "ratio" and split:
                for key, v in (("numerator_sources", n_s),
                               ("denominator_sources", d_s)):
                    if (not isinstance(v, list) or not v
                            or any(not isinstance(s, str) for s in v)):
                        p.append(f"{name}[{i}] ({e.get('target')!r}): ratio SPLIT form "
                                 f"needs {key} = a NON-EMPTY list of source column "
                                 "labels (both sides required)")
                if (isinstance(n_s, list) and isinstance(d_s, list)
                        and isinstance(srcs, list)
                        and set(map(str, srcs)) != set(map(str, n_s)) | set(map(str, d_s))):
                    p.append(f"{name}[{i}] ({e.get('target')!r}): in the ratio SPLIT "
                             "form 'sources' must list EXACTLY the union of "
                             "numerator_sources and denominator_sources")
            elif op == "ratio" and srcs is not None and len(srcs) != 2:
                # The 2-source form cannot express a per-group split (Male $ |
                # Male N | Female $ | Female N) - phi Retirement crashed here
                # rather than declare a wrong pairing. Point at the split form.
                p.append(f"{name}[{i}] ({e.get('target')!r}): ratio takes exactly TWO "
                         "sources [numerator, denominator] (e.g. the total-dollars "
                         "column then the count column). If the document prints the "
                         "dollars AND the counts once per GROUP (per sex, per tier) "
                         "with no printed Total column, use the SPLIT form instead: "
                         "\"numerator_sources\": [every dollar column], "
                         "\"denominator_sources\": [every COUNT column], and "
                         "\"sources\" = all of them. Code sums each side, then "
                         "divides")
            am = e.get("annualize_monthly")
            if am is not None:
                if not isinstance(am, bool):
                    p.append(f"{name}[{i}].annualize_monthly must be a boolean")
                elif am and (name != "col_map" or op not in ("copy", "ratio")):
                    p.append(f"{name}[{i}] ({e.get('target')!r}): annualize_monthly "
                             "only belongs on col_map copy/ratio entries (a dollar "
                             "column printed monthly)")
            wt = e.get("weights_table")
            if wt is not None and not isinstance(wt, int):
                p.append(f"{name}[{i}].weights_table must be an integer index or null")
            if op == "weighted_avg" and not isinstance(wt, int):
                p.append(f"{name}[{i}] ({e.get('target')!r}): weighted_avg requires an "
                         "integer weights_table (transcribe the counts table and "
                         "reference its index)")
            # weights_table 0 = the MAIN values table itself. Weighting a table
            # by itself is never meaningful: for an averages grid the values
            # (e.g. average salary) live in source_tables[0] and the SEPARATE
            # counts table must be a later index. This exact slip made phx
            # Age_Serv_Wage compute weighted-avg-of-counts (0.0) in the
            # 2026-07-23 sweep - see data_extraction_context.md.
            if op == "weighted_avg" and wt == 0:
                p.append(f"{name}[{i}] ({e.get('target')!r}): weighted_avg weights_table "
                         "is 0 (the MAIN values table) - you are weighting the values by "
                         "themselves. Put the AVERAGES/values table at source_tables[0] "
                         "and the member-COUNTS table at a later index, then set "
                         "weights_table to that counts index.")
            spans = e.get("source_spans")
            if op == "overlap_weighted":
                bad = (not isinstance(spans, list)
                       or (srcs is not None and len(spans) != len(srcs))
                       or any(not isinstance(s, list) or len(s) != 2
                              or any(v is not None and not isinstance(v, int) for v in s)
                              for s in (spans or [])))
                if bad:
                    p.append(f"{name}[{i}] ({e.get('target')!r}): overlap_weighted "
                             "requires source_spans - one [lo, hi] integer span per "
                             "source, null for open ends (e.g. '<15' -> [null, 14])")
            elif spans is not None:
                p.append(f"{name}[{i}] ({e.get('target')!r}): source_spans only "
                         "belongs on overlap_weighted entries")
            wts = e.get("weights_tables")
            if op == "group_weighted":
                n_tables = len(result.get("source_tables") or [])
                bad = (not isinstance(wts, list)
                       or (srcs is not None and len(wts) != len(srcs))
                       or any(not isinstance(k, int) or not (0 <= k < n_tables)
                              for k in (wts or [])))
                if bad:
                    # chi_gen and sd Avg_Mort burned all 8 attempts against the
                    # bare rule. 10 of the 14 plans that DID get it right pass
                    # ONE distribution table repeated per source
                    # (weights_tables: [2, 2]) - so the likeliest confusion is
                    # thinking a DISTINCT table per group is required. Say that,
                    # and list what has actually been transcribed to choose from.
                    avail = "; ".join(
                        f"{k}={str((t or {}).get('title'))[:48]!r}"
                        for k, t in enumerate(result.get("source_tables") or [])
                        if isinstance(t, dict)) or "(none transcribed yet)"
                    n_src = len(srcs) if srcs is not None else "N"
                    p.append(
                        f"{name}[{i}] ({e.get('target')!r}): group_weighted requires "
                        f"weights_tables - a list of {n_src} source_tables indices, "
                        "ONE PER SOURCE and in the same order, each pointing at a "
                        "transcribed headcount table. They do NOT have to be "
                        "different: when a single membership-distribution table "
                        "covers every group (the usual case - e.g. one 'Distribution "
                        "of Active Members' exhibit), repeat its index, e.g. "
                        f"\"weights_tables\": [{', '.join(['2'] * (n_src if isinstance(n_src, int) else 2))}]. "
                        "If no headcount table is transcribed yet, transcribe the "
                        "membership-distribution exhibit and reference it; declare "
                        "row_spans on it when its bins are coarser than the target "
                        f"(e.g. '50 to 54' -> [50, 54]). Transcribed tables: {avail}")
                else:
                    gw_weight_tables.update(wts)
                    gw_used = True
            elif wts is not None:
                p.append(f"{name}[{i}] ({e.get('target')!r}): weights_tables only "
                         "belongs on group_weighted entries")

    # EVERY mapped source label must actually exist on the table it is read
    # from. ops._get looks the label up with `str(l).strip()` and returns None
    # on a miss, so an invented label produces a null cell in silence - the
    # single most destructive gap found so far. It emptied 12 of 16 Sep_Rate
    # grids (the model mapped target SERVICE columns '1','2','3' onto a source
    # that only prints 'Males'/'Females' - the exhibit has no service
    # dimension), most of the empty Ret_Rate grids, chi_edu Avg_Mort, mil
    # Age_Serv_Wage and sd Retirement. None of them raised anything.
    # transpose swaps which printed axis the maps address (see ops module doc).
    # broadcast has its OWN label geometry (varying-axis sources are the source's
    # ROW labels, series_sources are its COLUMN labels), checked separately below.
    if not unavailable and not result.get("broadcast") and tables and isinstance(tables[0], dict):
        main = tables[0]
        flipped = bool(result.get("transpose"))
        printed_rows = [str(x).strip() for x in (main.get("row_labels") or [])]
        printed_cols = [str(x).strip() for x in (main.get("col_labels") or [])]
        axes = (("row_map", printed_cols if flipped else printed_rows,
                 "printed COLUMN labels" if flipped else "printed ROW labels"),
                ("col_map", printed_rows if flipped else printed_cols,
                 "printed ROW labels" if flipped else "printed COLUMN labels"))
        for name, avail, what in axes:
            if not avail:
                continue
            known, missing = set(avail), {}
            for i, e in enumerate(result.get(name) or []):
                if not isinstance(e, dict):
                    continue
                srcs = list(e.get("sources") or [])
                for key in ("numerator_sources", "denominator_sources"):
                    if isinstance(e.get(key), list):
                        srcs += e[key]
                for s in srcs:
                    if str(s).strip() not in known:
                        missing.setdefault(str(s), []).append(e.get("target"))
            if missing:
                shown = list(missing)[:6]
                p.append(
                    f"{name} references {len(missing)} source label(s) that do "
                    f"NOT exist in source_tables[0]: {shown}"
                    f"{' ...' if len(missing) > 6 else ''}. Code matches these "
                    "EXACTLY against the table's own labels and silently yields "
                    "an empty cell when there is no match, so the whole grid "
                    f"comes out null. The {what} of source_tables[0] are: "
                    f"{avail[:14]}{' ...' if len(avail) > 14 else ''}. Either use "
                    "those labels VERBATIM (same dashes and spacing as you "
                    "transcribed them), or - if the exhibit genuinely does not "
                    "publish that dimension at all - give those targets an EMPTY "
                    "sources list and explain in notes. Do NOT invent a label "
                    "for a bin the document does not print.")

    # span consistency: the same source bin must mean the same span everywhere
    # (the executor pools spans across entries to compute overlap sets)
    for name in ("row_map", "col_map"):
        entries = result.get(name)
        if not isinstance(entries, list):
            continue
        pool = {}
        for e in entries:
            if not isinstance(e, dict) or e.get("op") != "overlap_weighted":
                continue
            srcs, spans = e.get("sources"), e.get("source_spans")
            if not isinstance(srcs, list) or not isinstance(spans, list):
                continue
            for s, sp in zip(srcs, spans):
                key = str(s).strip()
                if key in pool and pool[key] != sp:
                    p.append(f"{name}: source bin {s!r} declared with two different "
                             f"spans ({pool[key]} vs {sp}) - a printed bin has ONE "
                             "meaning; declare the same span everywhere")
                pool[key] = sp

    transpose = result.setdefault("transpose", False)   # tolerated if absent
    if not isinstance(transpose, bool):
        p.append("transpose must be a boolean")

    # broadcast: a one-dimensional rate exhibit filled identically along the axis
    # the document does not measure (Sep_Rate service-only / age-only sources -
    # the shape behind most of the s8 audit's empty grids). Its label geometry
    # differs from a normal map, so it is validated here (and the standard
    # label-existence check above is skipped for it).
    broadcast = result.setdefault("broadcast", None)   # tolerated if absent
    if broadcast is not None:
        if not isinstance(broadcast, dict):
            p.append("broadcast must be null or an object")
        elif unavailable:
            p.append("broadcast and unavailable are mutually exclusive")
        elif transpose:
            p.append("broadcast cannot be combined with transpose - transcribe the "
                     "varying dimension as ROWS and set broadcast instead")
        elif result.get("derive") is not None:
            p.append("broadcast cannot be combined with derive")
        else:
            axis = broadcast.get("axis")
            series = broadcast.get("series_sources")
            sop = broadcast.get("series_op")
            if axis not in ("age", "service"):
                p.append("broadcast.axis must be 'age' (source varies by service "
                         "only) or 'service' (source varies by age only)")
            if not isinstance(series, list) or not series or not all(
                    isinstance(s, str) for s in series):
                p.append("broadcast.series_sources must be a non-empty list of the "
                         "rate COLUMN label(s) to read")
            if sop not in ("copy", "mean"):
                p.append("broadcast.series_op must be 'copy' (one rate column) or "
                         "'mean' (average several, e.g. Male+Female)")
            elif sop == "copy" and isinstance(series, list) and len(series) != 1:
                p.append("broadcast.series_op='copy' takes exactly one series source; "
                         "use 'mean' to combine several")
            # label geometry: varying-axis map sources are the source's ROW labels;
            # series_sources are its COLUMN labels; the constant-axis map's sources
            # must be empty (code fills that axis identically).
            if axis in ("age", "service") and tables and isinstance(tables[0], dict):
                main = tables[0]
                rows = {str(x).strip() for x in (main.get("row_labels") or [])}
                cols = {str(x).strip() for x in (main.get("col_labels") or [])}
                vary_name = "col_map" if axis == "age" else "row_map"
                const_name = "row_map" if axis == "age" else "col_map"
                miss = {}
                for e in (result.get(vary_name) or []):
                    if isinstance(e, dict):
                        for s in (e.get("sources") or []):
                            if str(s).strip() not in rows:
                                miss.setdefault(str(s), []).append(e.get("target"))
                if miss:
                    p.append(f"broadcast: {vary_name} (the varying axis) references "
                             f"{len(miss)} label(s) that are not ROW labels of "
                             f"source_tables[0]: {list(miss)[:6]}. In broadcast the "
                             "varying-axis sources are the source's ROW labels "
                             f"(the printed bins). Available rows: {sorted(rows)[:14]}")
                bad_series = [s for s in (series or []) if s not in cols]
                if bad_series:
                    p.append(f"broadcast.series_sources {bad_series} are not COLUMN "
                             f"labels of source_tables[0]. Available columns: {sorted(cols)}")
                nonempty_const = [e.get("target") for e in (result.get(const_name) or [])
                                  if isinstance(e, dict) and (e.get("sources") or [])]
                if nonempty_const:
                    p.append(f"broadcast: {const_name} entries must have EMPTY sources "
                             f"(that axis is filled identically); these do not: "
                             f"{nonempty_const[:6]}")

    # group_weighted declarations must be executable: weight tables need their
    # bin spans, and the main table needs spans on the axis whose labels form
    # the weight lookup's second coordinate (live sd Sep_Rate run 2026-07-14:
    # the model declared a correct blend but omitted every span, crashing the
    # executor - this check moves that failure into the retry loop)
    if gw_used:
        for k in sorted(gw_weight_tables):
            t = tables[k] if k < len(tables) else None
            if not isinstance(t, dict):
                continue
            for key, labels_key in (("row_spans", "row_labels"),
                                    ("col_spans", "col_labels")):
                labels = t.get(labels_key) or []
                if len(labels) > 1 and not t.get(key):
                    p.append(f"source_tables[{k}] is used as group_weighted weights "
                             f"and has {len(labels)} {labels_key} but no {key}: "
                             "declare the numeric [lo, hi] span of every printed "
                             "bin label (null = open end)")
        multi_col_weights = any(
            isinstance(tables[k], dict) and len(tables[k].get("col_labels") or []) > 1
            for k in gw_weight_tables if k < len(tables))
        if multi_col_weights and tables and isinstance(tables[0], dict):
            key, labels_key = (("row_spans", "row_labels") if transpose
                               else ("col_spans", "col_labels"))
            main = tables[0]
            if len(main.get(labels_key) or []) > 1 and not main.get(key):
                p.append(f"source_tables[0] needs {key} declared: group_weighted "
                         "weights are looked up by the main table's bin "
                         "coordinates (with transpose=true the printed ROW "
                         "labels are that lookup axis)")

    derive = result.setdefault("derive", None)   # tolerated if absent
    if unavailable and derive is not None:
        p.append("unavailable=true requires derive to be null")
    elif derive is not None:
        if not isinstance(derive, dict):
            p.append("derive must be null or an object")
        else:
            dop = derive.get("op")
            if dop not in ("ratio", "sum"):
                p.append(f"derive.op {dop!r} must be 'ratio' or 'sum'")
            if dop == "ratio":
                for key in ("numerator_table", "denominator_table"):
                    v = derive.get(key)
                    if not isinstance(v, int) or not (0 <= v < len(tables)):
                        p.append(f"derive.{key} must be a valid index into source_tables")
            elif dop == "sum":
                table_idxs = derive.get("tables")
                if (not isinstance(table_idxs, list) or len(table_idxs) < 2
                        or any(not isinstance(v, int) or not (0 <= v < len(tables))
                               for v in table_idxs)):
                    p.append("derive.tables must be a list of at least two valid "
                             "source_tables indices")
                elif len(set(table_idxs)) != len(table_idxs):
                    p.append("derive.tables must not repeat table indices")
                elif tables:
                    base = tables[table_idxs[0]]
                    for v in table_idxs[1:]:
                        t = tables[v]
                        if (len(t.get("row_labels") or []) != len(base.get("row_labels") or [])
                                or len(t.get("col_labels") or []) != len(base.get("col_labels") or [])):
                            p.append("derive=sum tables must have the same SHAPE (same "
                                     "number of rows and columns) - they are summed by "
                                     "position; transcribe the same distribution grid in "
                                     "each group table")
            banned = ({"weighted_avg", "ratio"} if dop == "ratio"
                      else {"weighted_avg"})   # col ratio after derive=sum is fine
            for name in ("row_map", "col_map"):
                for i, e in enumerate(result.get(name, [])):
                    if isinstance(e, dict) and e.get("op") in banned:
                        p.append(f"{name}[{i}]: {e.get('op')} is not allowed in "
                                 f"{dop} mode - use additive maps")

    if not isinstance(result["notes"], str):
        p.append("notes must be a single string (not a list)")
    elif unavailable and not result["notes"].strip():
        p.append("unavailable=true requires notes stating what the document "
                 "publishes instead of the target")

    # unit plausibility for probability targets: a probability cannot exceed 1,
    # so a main table with values > 1.5 and no percent flag is almost certainly
    # a percentage table missing its values_unit declaration (live sd Sep_Rate
    # run 2026-07-14 embedded rates 100x too large this way)
    if (target_spec and target_spec.get("convert_percent_to_decimal")
            and tables and isinstance(tables[0], dict)
            and tables[0].get("values_unit") is None):
        cells = tables[0].get("cells") or []
        mx = max((v for row in cells if isinstance(row, list)
                  for v in row if isinstance(v, (int, float))
                  and not isinstance(v, bool)), default=None)
        if mx is not None and mx > 1.5:
            scale = "'per_1000' (per 1,000 members)" if mx > 100 else "'percent'"
            p.append(f"source_tables[0] holds values up to {mx} for a target whose "
                     f"unit is a probability (max 1): the table prints a scaled rate - "
                     f"set its values_unit to {scale} so code rescales it (transcribe "
                     "the numbers as printed either way)")

    # plausibility for an AVERAGE-dollar target (Age_Serv_Wage): a per-person
    # average salary can't be seven figures. If source_tables[0] (the values
    # table that fills the grid) holds million-dollar cells and derive is NOT
    # ratio, the model transcribed a salary-TOTALS table and is emitting the raw
    # sums as if they were averages (the whole-corpus 2026-07-27 chi_edu/ff/gen/
    # pol wage 0.00s: notes said 'average = totals/lives' but derive was None).
    # Make it a loud contract violation so best-of-N/retry declares derive=ratio.
    ceiling = target_spec.get("max_plausible_value") if target_spec else None
    is_ratio = isinstance(derive, dict) and derive.get("op") == "ratio"
    if ceiling and tables and isinstance(tables[0], dict) and not is_ratio:
        cells = tables[0].get("cells") or []
        mx = max((v for row in cells if isinstance(row, list)
                  for v in row if isinstance(v, (int, float))
                  and not isinstance(v, bool)), default=None)
        if mx is not None and mx > ceiling:
            p.append(f"source_tables[0] holds values up to {mx:,.0f} - a per-person "
                     f"average can't exceed {ceiling:,.0f}, so this is a salary-TOTALS "
                     "table, not an averages exhibit. Transcribe the member-COUNTS "
                     "table too and declare derive={'op':'ratio','numerator_table':"
                     "<totals index>,'denominator_table':<counts index>} with additive "
                     "maps (sum/copy) - code computes average = total/count. Do NOT "
                     "emit the totals as if they were averages.")

    # ratio completeness: a derive=ratio divides a numerator (totals) table by a
    # denominator (counts) table, aggregating BOTH with the row/col maps. If one
    # table's MAPPED cells are all null, every average is total/None or None/count
    # = None and the output grid comes out empty. Live 2026-07-27 chi_pol
    # Age_Serv_Wage: the salary (numerator) table was transcribed with ONLY its
    # 'Total' column filled - all 90 interior age x service cells null - so the
    # grid scored 0.0 despite a correct derive=ratio. Fire ONLY when EVERY mapped
    # cell of a table is null (filled==0): a legitimately sparse plan still fills
    # some interior cells, so this can't false-positive - it catches a table
    # transcribed as margins-only. Turns the silent empty grid into a retry.
    if (is_ratio and not transpose and tables
            and isinstance(result.get("row_map"), list)
            and isinstance(result.get("col_map"), list)):
        row_srcs = [s for e in result["row_map"] if isinstance(e, dict)
                    for s in (e.get("sources") or []) if isinstance(s, str)]
        col_srcs = [s for e in result["col_map"] if isinstance(e, dict)
                    for s in (e.get("sources") or []) if isinstance(s, str)]
        for role, idx in (("numerator", derive.get("numerator_table")),
                          ("denominator", derive.get("denominator_table"))):
            if not isinstance(idx, int) or not (0 <= idx < len(tables)):
                continue
            t = tables[idx]
            if not isinstance(t, dict):
                continue
            ri = {lab: k for k, lab in enumerate(t.get("row_labels") or [])}
            ci = {lab: k for k, lab in enumerate(t.get("col_labels") or [])}
            cells = t.get("cells") or []
            seen = filled = 0
            for r in row_srcs:
                if r not in ri:
                    continue
                row = cells[ri[r]] if ri[r] < len(cells) else []
                for c in col_srcs:
                    if c not in ci:
                        continue
                    seen += 1
                    v = row[ci[c]] if isinstance(row, list) and ci[c] < len(row) else None
                    if v is not None:
                        filled += 1
            if seen and filled == 0:
                p.append(f"derive=ratio {role} source_tables[{idx}] has {seen} cells "
                         "referenced by the row/col maps and EVERY ONE is null - the "
                         "table was transcribed with only its margins/'Total', not the "
                         "interior. A ratio needs the paired numbers in every cell: "
                         "transcribe the full age x service grid of BOTH the totals and "
                         "counts tables (null only where the printed cell is truly blank).")

    # MONTHLY-in-a-ratio floor: some AVs print salary/benefit dollars MONTHLY
    # (chi_ff Exhibit B.1). The ratio then yields a per-month average, which is
    # exactly 12x too small, and NO column flag can fix it (a column-level
    # annualize_monthly scales numerator and denominator alike and cancels).
    # Detect it from the data: implied average = sum(numerator)/sum(denominator).
    # Below the floor it cannot be an annual salary. Verified on the live corpus:
    # chi_ff 8,227 (monthly -> fires) vs chi_edu 74,383 / chi_gen 56,053 /
    # chi_pol 46,019 (annual -> silent) - a wide, safe gap. Self-correcting when
    # a transcribed 'Total' column inflates BOTH sums (the ratio is unchanged).
    floor = target_spec.get("min_plausible_ratio_value") if target_spec else None
    if (floor and is_ratio and not derive.get("annualize_monthly") and tables):
        def _sum(idx):
            if not isinstance(idx, int) or not (0 <= idx < len(tables)):
                return None
            t = tables[idx]
            if not isinstance(t, dict):
                return None
            return sum(v for row in (t.get("cells") or []) if isinstance(row, list)
                       for v in row if isinstance(v, (int, float))
                       and not isinstance(v, bool))
        n_sum = _sum(derive.get("numerator_table"))
        d_sum = _sum(derive.get("denominator_table"))
        if n_sum and d_sum:
            implied = n_sum / d_sum
            # Fire only when the MONTHLY hypothesis is self-consistent: below the
            # floor AND x12 lands back in the plausible annual range. An implied
            # average far below floor/12 is not a monthly salary at all - it means
            # the wrong tables were paired (e.g. ratio declared over an AVERAGES
            # table), and telling that model to "annualize" would make it worse.
            # Live separation: chi_ff 8,227 (x12 = 98,724 -> fires) vs averages-
            # table pairings at 80-874 (x12 = 960-10,488 -> silent).
            if floor / 12 <= implied < floor:
                p.append(
                    f"derive=ratio implies an average of {implied:,.0f} per member "
                    f"(sum of the totals table / sum of the counts table), which is "
                    f"below {floor:,.0f} - the source prints MONTHLY dollars, not "
                    "annual. Add \"annualize_monthly\": true INSIDE the derive object "
                    "(not on a column - there it cancels, because it scales the "
                    "numerator and the denominator alike): "
                    "derive={'op':'ratio','numerator_table':N,'denominator_table':M,"
                    "'annualize_monthly':true}. Code then multiplies the ratio RESULT "
                    "by 12. Transcribe the printed monthly numbers unchanged.")

    # COLUMN-ratio plausibility. The 2-source col ratio happily divides one
    # DOLLAR column by another dollar column, and nothing downstream notices:
    # chi_ff and chi_gen Retirement both declared ratio(Male $, Female $) on an
    # exhibit that prints Male N | Male $ | Female N | Female $ with no Total
    # column, and shipped "average benefits" of $4.44 / $12.91 / $15.88 as
    # scored production output. (phi hit the same wall and crashed on the arity
    # rule instead - same gap, opposite symptom.) The denominator of an average
    # must be a COUNT, so the implied average is the test.
    if floor and not transpose and tables and isinstance(tables[0], dict):
        main = tables[0]
        labels = [str(c).strip() for c in (main.get("col_labels") or [])]
        rows = [r for r in (main.get("cells") or []) if isinstance(r, list)]

        def _colsum(names):
            tot, seen = 0.0, False
            for nm in names or []:
                if str(nm).strip() not in labels:
                    return None
                j = labels.index(str(nm).strip())
                for r in rows:
                    v = r[j] if j < len(r) else None
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        tot += v
                        seen = True
            return tot if seen else None

        cmap = result.get("col_map")
        for i, e in enumerate(cmap if isinstance(cmap, list) else []):
            if not isinstance(e, dict) or e.get("op") != "ratio":
                continue
            n_s = e.get("numerator_sources")
            d_s = e.get("denominator_sources")
            if not (n_s and d_s):
                s = e.get("sources")
                if not (isinstance(s, list) and len(s) == 2):
                    continue          # arity already reported above
                n_s, d_s = [s[0]], [s[1]]
            n_sum, d_sum = _colsum(n_s), _colsum(d_s)
            if not n_sum or not d_sum:
                continue
            implied = n_sum / d_sum
            if implied >= floor:
                continue
            if floor / 12 <= implied and not e.get("annualize_monthly"):
                p.append(
                    f"col_map[{i}] ({e.get('target')!r}): the declared ratio implies "
                    f"an average of {implied:,.0f}, below {floor:,.0f} - the source "
                    "prints MONTHLY dollars. Add \"annualize_monthly\": true to this "
                    "column entry (code x12's it) and say so in notes.")
            elif implied < floor / 12:
                p.append(
                    f"col_map[{i}] ({e.get('target')!r}): the declared ratio "
                    f"{n_s} / {d_s} implies an average of {implied:,.2f} - far below "
                    f"{floor:,.0f}, so the DENOMINATOR is not a member count. Dividing "
                    "one dollar column by another dollar column is not an average. "
                    "The denominator must be the COUNT column(s). If the exhibit "
                    "prints dollars and counts once per GROUP (per sex, per tier) and "
                    "has no printed Total column, use the SPLIT form: "
                    "\"numerator_sources\": [every dollar column], "
                    "\"denominator_sources\": [every count column], \"sources\": all "
                    "of them - code sums each side, then divides.")
    return p


def _call_openai(messages, temperature=0, seed=0):
    """One chat-completions call to an OpenAI-compatible server (vLLM).
    Dependency-free (urllib). temperature=0 is greedy (deterministic); a
    positive temperature with a fixed seed gives a reproducible sample.
    Thinking disabled via chat_template_kwargs (honored by vLLM for
    Qwen-family templates, harmlessly ignored elsewhere). Returns
    (text, raw_response_dict)."""
    import urllib.request
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "system", "content": SYSTEM}] + messages,
        "max_tokens": MAX_TOKENS,
        "temperature": temperature,
        "seed": seed,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "none")},
    )
    with urllib.request.urlopen(req, timeout=OPENAI_TIMEOUT) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    choice = raw["choices"][0]
    if choice.get("finish_reason") == "length":
        # Diagnostic: classify the runaway WITHOUT re-plumbing a save path.
        #   n_tables  = how many source_tables it started (over-transcription of
        #               real tables, like mil's 12 employer tables, vs. one table)
        #   n_rows    = rough count of transcribed cell-rows ('], [' separators)
        #   reps      = how many times a late 140-char window recurs in the whole
        #               output; a high count == a REPETITION LOOP (model stuck
        #               emitting the same rows), a low count == a genuinely large
        #               (single-year) table that just needs more output budget.
        # The full runaway text is also dumped to EXTRACT_DUMP_DIR (if set) so it
        # can be inspected end to end.
        c = choice.get("message", {}).get("content") or ""
        n_tables = c.count('"page"')
        n_rows = c.count("], [") + c.count("],[")
        probe = c[-300:-160]
        reps = c.count(probe) if len(probe.strip()) > 40 else 0
        verdict = "LIKELY LOOP" if reps >= 4 else "likely large/legit table"
        dump = os.environ.get("EXTRACT_DUMP_DIR")
        dumped = ""
        if dump:
            path = os.path.join(dump, f"truncated_{seed}_{len(c)}.txt")
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(c)
                dumped = f" [full text -> {path}]"
            except OSError:
                pass
        msg = (f"output-limit truncation ({MAX_TOKENS} tok): content={len(c)} chars, "
               f"{n_tables} source_tables, ~{n_rows} cell-rows, late-window recurs "
               f"{reps}x -> {verdict}.{dumped} HEAD: {c[:150].replace(chr(10),' ')!r}")
        # A truncation is a FAILED CANDIDATE, not a run abort: one looping
        # sample must not kill best-of-N (chi_pol ASN loops on some draws and
        # is perfect on others). Signalled via the 3rd return value.
        return None, raw, msg
    return choice["message"]["content"], raw, None


def _evaluate(text, target_spec):
    """Score one candidate response. Returns
    (result|None, fatal_problems, totals_violations, all_problems).
    fatal = contract violations (validate); totals_violations = count of
    printed-totals reconciliation failures (non-fatal, used only to rank
    candidates in best-of-N). A clean candidate has fatal==[] and
    totals_violations==0."""
    import ops
    try:
        result = _parse(text)
    except (ValueError, json.JSONDecodeError) as e:
        return None, [f"response is not parseable JSON: {e}"], 0, \
               [f"response is not parseable JSON: {e}"]
    fatal = validate(result, target_spec)
    totals = []
    if not fatal:
        for k, t in enumerate(result["source_tables"]):
            for msg in ops.totals_check(t):
                totals.append(f"source_tables[{k}] {msg}")
    return result, fatal, totals, list(fatal)


def _reconcile_penalty(result, target_spec, reconcile_total):
    """Best-of-N selection signal that the per-table totals-check CANNOT give:
    run the executor on this candidate and compare the DERIVED grid's total to
    a known plan total (e.g. PPD actives_tot). A candidate that transcribes
    every table cleanly but sums the WRONG SET of tables (mil summed all 12
    employer/tier tables -> 2.5x the plan) is internally consistent yet wrong;
    only reconciliation against the external total catches it. Returns the
    relative error (0.0 when no reference, or within 2% - so it never reorders
    already-correct candidates), capped so an unexecutable candidate is
    deprioritised without being treated as fatal."""
    if not reconcile_total:
        return 0.0
    import ops
    try:
        derived = ops.execute(
            result["source_tables"], result["row_map"], result["col_map"],
            derive=result.get("derive"), transpose=result.get("transpose", False),
            target_row_spans=target_spec.get("target_row_spans"),
            target_col_spans=target_spec.get("target_col_spans"),
            to_decimal=target_spec.get("convert_percent_to_decimal", False),
            zero_impossible_cfg=target_spec.get("zero_impossible_cells"))
    except Exception:
        return 9.999
    total = sum(v for row in derived["cells"] for v in row
                if isinstance(v, (int, float)) and not isinstance(v, bool))
    rel = abs(total - reconcile_total) / reconcile_total
    return 0.0 if rel <= 0.02 else round(min(rel, 9.999), 4)


def _correction_message(problems):
    return ("Your response does not conform to the required output format. "
            "Problems:\n" + "\n".join(f"- {pb}" for pb in problems) +
            "\n\nReturn the SAME data, corrected to EXACTLY the required "
            "structure.\n\n" + FORMAT_SPEC +
            "\n\nReturn ONLY the corrected JSON object.")


def _totals_correction_message(problems):
    """The structure is legal but the numbers do not add up against the exhibit's
    OWN printed totals. That is PDF-independent evidence of a transcription slip,
    and the dominant cause is column misalignment on a whitespace-collapsed text
    layer (chi_edu p55 prints '2 ,625' and '$ 4 6,732,744', splitting numerals
    across apparent columns)."""
    return ("Your JSON is structurally valid, but the numbers you transcribed do "
            "NOT agree with the totals PRINTED IN THE EXHIBIT ITSELF:\n"
            + "\n".join(f"- {pb}" for pb in problems[:20]) +
            "\n\nThe printed totals are part of the source, so the transcription "
            "is wrong somewhere. The usual cause is COLUMN MISALIGNMENT: this "
            "document's text layer collapses whitespace and can split a single "
            "number across what look like two columns (e.g. '2 ,625' is ONE "
            "value 2625, and '$ 4 6,732,744' is ONE value 46732744, not a 4 "
            "followed by 6,732,744). A value placed one column late shifts every "
            "later column and leaves a phantom empty first column.\n\n"
            "Re-read the exhibit line by line. For each row, count the values and "
            "line them up against the column headers, treating a dash as an empty "
            "cell; join digits that a stray space has split; and do not put a "
            "printed 'Total' row or column inside cells (those belong in "
            "printed_col_totals / printed_row_totals). Then re-check that each "
            "row's cells sum to its printed total.\n\n"
            "Return ONLY the corrected JSON object, same structure.")


def _extract_openai(target_name, target_spec, prompt, record, record_path,
                    reconcile_total=None):
    """Local-backend Stage A: greedy baseline -> one greedy correction retry
    -> best-of-N temperature sampling verified against the printed totals AND
    (when a plan total is known) the derived-grid reconciliation. Ranking key:
    (contract violations, reconciliation error, totals violations) - fewest
    first. Raises only if no candidate is contract-valid."""
    base = [{"role": "user", "content": prompt}]
    best = {"key": (10 ** 9, 10.0, 10 ** 9), "result": None, "text": None,
            "fatal": None, "totals": []}
    clean = (0, 0.0, 0)

    def consider(text, raw, tag, trunc=None):
        # trunc (output-limit truncation) is a FAILED candidate, not a run
        # abort: record it and keep sampling. Ranks below any parseable one.
        if trunc:
            fatal, result, totals, recon = [trunc], None, [], 10.0
        else:
            result, fatal, totals, allp = _evaluate(text, target_spec)
            recon = _reconcile_penalty(result, target_spec, reconcile_total) if not fatal else 10.0
        att = {"tag": tag, "response": raw, "usage": raw.get("usage") if raw else None,
               "n_fatal": len(fatal), "n_totals": len(totals), "reconcile_err": recon,
               "truncated": bool(trunc)}
        if fatal:
            att["format_problems"] = fatal
        if totals:
            att["totals_problems"] = totals
        record["attempts"].append(att)
        key = (len(fatal), recon, len(totals))
        if key < best["key"]:
            best.update(key=key, result=result, text=text, fatal=fatal, totals=totals)
        return key

    # 1. greedy baseline (reproducible)
    text, raw, trunc = _call_openai(base, temperature=0, seed=0)
    if consider(text, raw, "greedy", trunc) == clean:
        return _finalize_openai(best, record, record_path)

    # 2. one greedy correction retry with the specific problems fed back
    #    (only if we HAVE a candidate to correct - not if greedy truncated)
    if best["fatal"] and best["text"]:
        msgs = base + [{"role": "assistant", "content": best["text"]},
                       {"role": "user", "content": _correction_message(best["fatal"])}]
        text, raw, trunc = _call_openai(msgs, temperature=0, seed=0)
        if consider(text, raw, "retry", trunc) == clean:
            return _finalize_openai(best, record, record_path)

    # 2b. contract-clean but the printed totals do not reconcile: retry with the
    #     MISMATCHES fed back. The Anthropic path has always done this (it folds
    #     totals into `problems`); the local path only warned, so a systematic
    #     transcription slip sailed through - chi_edu Age_Serv_Wage shifted every
    #     row one column right (values all correct, one column late), produced 10
    #     row-total mismatches, and still shipped a 0.00 grid. A printed total
    #     that disagrees with the cells is PDF-independent evidence of exactly
    #     that class of error, so it is worth one greedy correction.
    if not best["fatal"] and best["totals"] and best["text"]:
        msgs = base + [{"role": "assistant", "content": best["text"]},
                       {"role": "user", "content": _totals_correction_message(best["totals"])}]
        text, raw, trunc = _call_openai(msgs, temperature=0, seed=0)
        if consider(text, raw, "retry-totals", trunc) == clean:
            return _finalize_openai(best, record, record_path)

    # 3. best-of-N: independent temperature draws to escape a deterministic
    #    mistake (column shift, phantom index, wrong table set, OR a decoding
    #    LOOP that truncates one sample), each verified by the printed totals
    #    and the plan-total reconciliation
    if OPENAI_SAMPLES > 0 and best["key"] != clean:
        print(f"[stage A] not clean after greedy+retry (best: {best['key'][0]} contract, "
              f"{best['key'][1]} reconcile, {best['key'][2]} totals); sampling up to "
              f"{OPENAI_SAMPLES} at temperature {OPENAI_TEMPERATURE}...")
        for i in range(OPENAI_SAMPLES):
            text, raw, trunc = _call_openai(base, temperature=OPENAI_TEMPERATURE, seed=1000 + i)
            if consider(text, raw, f"sample{i}", trunc) == clean:
                print(f"[stage A] clean sample found (sample{i})")
                break

    return _finalize_openai(best, record, record_path)


def _finalize_openai(best, record, record_path):
    if record_path:
        with open(record_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, default=str)
    if best["result"] is None or best["fatal"]:
        raise RuntimeError("response still violates the contract after "
                           f"{len(record['attempts'])} attempts:\n"
                           + "\n".join(best["fatal"] or ["unparseable JSON"]))
    if best["key"][1] > 0:
        print(f"[stage A] WARNING: best candidate's derived total is off by "
              f"{best['key'][1]:.1%} vs the known plan total (wrong table set / "
              "double-count?); proceeding (best of all attempts)")
    if best["key"][2] > 0:
        print(f"[stage A] WARNING: best candidate still has {best['key'][2]} "
              "printed-totals inconsistencies; transcription is suspect but "
              "proceeding (best of all attempts)")
    return best["result"], record


def extract(target_name, target_spec, source_text, record_path=None, dry_run=False,
            reconcile_total=None):
    """Run one extraction (with one format-correction retry if the response
    does not conform to the contract). Returns (result_dict, record_dict).

    reconcile_total: a known plan-wide total for the derived grid (e.g. PPD
    actives_tot for a count target). When given, best-of-N prefers the
    candidate whose derived total matches it - catches wrong-table-set
    double-counts the per-table totals-check cannot see. Local backend only."""
    use_openai = bool(OPENAI_BASE_URL)
    model_name = OPENAI_MODEL if use_openai else MODEL
    prompt = build_prompt(target_name, target_spec, source_text,
                          doc_first=use_openai)

    if dry_run:
        backend = f"openai-compatible @ {OPENAI_BASE_URL}" if use_openai else "anthropic"
        print("--- DRY RUN: prompt that would be sent ---")
        print(prompt[:3000])
        print(f"--- ({len(prompt)} chars total; model={model_name}; backend={backend}) ---")
        return None, None

    record = {"attempts": [], "model": model_name,
              "backend": "openai-compatible" if use_openai else "anthropic"}
    if use_openai:
        record["base_url"] = OPENAI_BASE_URL
        record["samples"] = OPENAI_SAMPLES
        record["temperature"] = OPENAI_TEMPERATURE
        return _extract_openai(target_name, target_spec, prompt, record, record_path,
                               reconcile_total=reconcile_total)

    import anthropic  # deferred so dry runs work without the package/key
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": prompt}]
    result = None

    for attempt in (1, 2):
        params = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": SYSTEM,
            "messages": messages,
            # kept for endpoints that honor it; proxies may drop it, which is
            # why we validate client-side below
            "output_config": {"format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
        }
        with client.messages.stream(**params) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "refusal":
            raise RuntimeError(f"model refused: {response.stop_details}")

        text = next(b.text for b in response.content if b.type == "text")
        record["attempts"].append({
            "response": response.to_dict(),
            "usage": {"input_tokens": response.usage.input_tokens,
                      "output_tokens": response.usage.output_tokens},
        })

        try:
            result = _parse(text)
            problems = validate(result, target_spec)
            if not problems:
                # transcription self-check against the tables' printed totals
                import ops
                for k, t in enumerate(result["source_tables"]):
                    for msg in ops.totals_check(t):
                        problems.append(
                            f"source_tables[{k}] transcription inconsistent with its "
                            f"printed totals ({msg}) - re-read the table carefully; "
                            "values are probably placed one column off. Align each "
                            "value to its column by position, using the printed "
                            "totals to verify.")
        except (ValueError, json.JSONDecodeError) as e:
            problems = [f"response is not parseable JSON: {e}"]

        if not problems:
            break
        record["attempts"][-1]["format_problems"] = problems
        if attempt == 1:
            print(f"[stage A] response violated the contract ({len(problems)} problems),"
                  " retrying with corrections...")
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content":
                    "Your response does not conform to the required output format. "
                    "Problems:\n" + "\n".join(f"- {pb}" for pb in problems) +
                    "\n\nReturn the SAME data, corrected to EXACTLY the required "
                    "structure.\n\n" + FORMAT_SPEC +
                    "\n\nReturn ONLY the corrected JSON object."},
            ]
        else:
            fatal = [pb for pb in problems if "printed totals" not in pb]
            if fatal:
                if record_path:
                    with open(record_path, "w", encoding="utf-8") as fh:
                        json.dump(record, fh, indent=2, default=str)
                raise RuntimeError("response still violates the contract after retry:\n"
                                   + "\n".join(fatal))
            # only totals inconsistencies remain: proceed, loudly - the score
            # and saved artifacts are still informative
            print("[stage A] WARNING: totals check still failing after retry; "
                  "transcription is suspect but proceeding")

    if record_path:
        with open(record_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, default=str)
    return result, record
