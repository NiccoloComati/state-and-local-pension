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

MODEL = "claude-opus-4-8"
MAX_TOKENS = 32000

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
            "anyOf": [{"type": "string", "enum": ["percent"]}, {"type": "null"}],
            "description": "'percent' if the table prints percentages (e.g. 22.50 meaning 22.5%) while the target wants decimals - code scales by 0.01. Else null. Transcribe the numbers AS PRINTED either way.",
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

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_tables": {
            "type": "array",
            "items": _TABLE,
            "description": "index 0 = the main source table; add auxiliary tables (e.g. the counts table when it supplies weights) after it",
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
                           "enum": ["copy", "sum", "weighted_avg", "overlap_weighted"]},
                    "weights_table": {"anyOf": [{"type": "integer"}, {"type": "null"}],
                                      "description": "index into source_tables providing weights (weighted_avg only, else null)"},
                    "source_spans": _SPANS,
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
                                    "overlap_weighted"]},
                    "weights_table": {"anyOf": [{"type": "integer"}, {"type": "null"}],
                                      "description": "index into source_tables providing count weights (weighted_avg only, else null). Column weighted_avg merges source COLUMNS of an averages table."},
                    "source_spans": _SPANS,
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
                    },
                    "required": ["op", "numerator_table", "denominator_table"],
                    "additionalProperties": False,
                },
            ],
            "description": "null normally. Use {op:'ratio',...} when the document publishes TOTALS instead of the averages the target wants (e.g. total salary dollars + member counts): both tables are aggregated with the same maps (additive ops only) and divided cell-wise by code.",
        },
        "transpose": {
            "type": "boolean",
            "description": "true when the printed table's orientation is the REVERSE of the target's (e.g. printed age rows x service cols, target service rows x age cols). Transcribe as printed; code transposes before mapping. When true, row_map maps the printed COLUMNS onto target rows and col_map maps the printed ROWS onto target columns.",
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
Never compute, round, merge, or invent anything at this step. Exclude total rows/columns.
2. DECLARE: describe how the source bins map onto the target grid as row_map/col_map \
operations (copy, sum, weighted_avg for rows; copy, sum, share_even, weighted_avg for \
columns). \
Deterministic code will execute these - you do NO arithmetic. If a weighted average is \
needed (e.g. merging salary bins), also transcribe the table that provides the weights \
(e.g. member counts) as an additional source table and reference it by index. \
If the document publishes TOTALS instead of the averages the target wants (e.g. total \
salary dollars per cell plus member counts, but no average-salary exhibit), transcribe \
BOTH tables and declare derive = {"op": "ratio", "numerator_table": <totals>, \
"denominator_table": <counts>}: code aggregates both tables with your maps (additive \
ops only - sum/copy, NOT weighted_avg) and divides cell-wise. Otherwise derive is null. \
If the printed orientation is the reverse of the target's, set transpose=true \
(transcribe as printed; code transposes; row_map then maps the printed COLUMNS onto \
target rows). For RATE tables whose bins do not align with the target bins, use op \
"overlap_weighted" and declare each source bin's numeric span in "source_spans" \
([lo, hi], null = open end, e.g. "<15" -> [null, 14]): code blends the rates \
proportionally to how many years of the target bin fall in each source bin. Rates are \
intensive - never sum them; a target bin inside one source bin just copies its rate. \
If a table prints percentages while the target wants decimals, transcribe as printed \
and set the table's values_unit to "percent" - code does the scaling.

Every target row/column must appear exactly once in the maps, in target-grid order. \
If data for a target bin does not exist anywhere in the document, give it an empty \
sources list. Record every judgment call in notes."""


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
- row ops: "copy" | "sum" | "weighted_avg" | "overlap_weighted"; col ops:
  "copy" | "sum" | "share_even" | "weighted_avg" | "overlap_weighted".
  "copy" and "share_even" take EXACTLY ONE source. Merging bins of an
  AVERAGES table (rows or columns) is ALWAYS "weighted_avg" with
  "weights_table" pointing at the transcribed counts table - never sum or
  share_even (averages are not additive).
- "overlap_weighted" (RATE tables with non-aligned bins) requires
  "source_spans": one [lo, hi] integer span per source (null = open end).
  Code blends rates proportionally by year overlap with the target bin.
- "transpose": true when the printed orientation is the reverse of the
  target's; transcribe as printed, code transposes before mapping.
- a source table printing percentages gets "values_unit": "percent"
  (numbers still transcribed exactly as printed).
- "derive" is null UNLESS the document publishes totals instead of the target's
  averages: then transcribe BOTH tables (same bin labels) and set
  {"op": "ratio", "numerator_table": <index of the totals table>,
  "denominator_table": <index of the counts table>}. In ratio mode all row ops
  must be additive (sum/copy, never weighted_avg) - code aggregates both
  tables with the same maps, then divides cell-wise (average = total/count).
- If the source table PRINTS totals (a Total column and/or Total row),
  transcribe them into printed_row_totals / printed_col_totals (aligned with
  row_labels / col_labels; null where not printed). They are checked in code
  against your cells to catch column-alignment mistakes - tables whose text
  layout interleaves rows or collapses whitespace make it easy to place a
  value one column off, so align each value carefully by its column position.
  Set them to null if the table prints no totals.
- "notes" is a single string."""


def build_prompt(target_name, target_spec, source_text):
    g = target_spec["grid"]
    rules = "\n".join(f"- {r}" for r in target_spec["rules"])
    return f"""TARGET: {target_name}
WHAT IT IS: {target_spec['description']}
UNIT: {target_spec['unit']}

TARGET GRID (row_map/col_map targets must be exactly these, in this order):
- target rows: {json.dumps(g['row_labels'])}
  ({g.get('rows_meaning', '')})
- target cols: {json.dumps(g['col_labels'])}
  ({g.get('cols_meaning', '')})

MAPPING GUIDANCE FOR THIS TARGET:
{rules}

{FORMAT_SPEC}

FULL DOCUMENT TEXT:
{source_text}

Transcribe the source table(s) exactly as printed, then declare the bin mappings.
Return ONLY the JSON object."""


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


def validate(result):
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

    tables = result["source_tables"]
    if not isinstance(tables, list) or not tables:
        p.append("source_tables must be a non-empty list")
        tables = []
    for k, t in enumerate(tables):
        if not isinstance(t, dict):
            p.append(f"source_tables[{k}] is not an object")
            continue
        for key, typ in (("page", int), ("title", str),
                         ("row_labels", list), ("col_labels", list)):
            if not isinstance(t.get(key), typ):
                p.append(f"source_tables[{k}].{key} missing or not {typ.__name__}")
        for key in ("printed_row_totals", "printed_col_totals"):
            tv = t.setdefault(key, None)   # tolerated if absent
            if tv is not None:
                if not isinstance(tv, list) or any(
                        v is not None and not isinstance(v, (int, float)) for v in tv):
                    p.append(f"source_tables[{k}].{key} must be a list of numbers/nulls or null")
        vu = t.setdefault("values_unit", None)   # tolerated if absent
        if vu is not None and vu != "percent":
            p.append(f"source_tables[{k}].values_unit must be 'percent' or null")
        cells = t.get("cells")
        if not isinstance(cells, list):
            p.append(f"source_tables[{k}].cells missing or not a list of lists"
                     " (do NOT use row objects like {{'label':..,'values':..}})")
        else:
            if isinstance(t.get("row_labels"), list) and len(cells) != len(t["row_labels"]):
                p.append(f"source_tables[{k}].cells has {len(cells)} rows but "
                         f"{len(t['row_labels'])} row_labels")
            for i, row in enumerate(cells):
                if not isinstance(row, list):
                    p.append(f"source_tables[{k}].cells[{i}] is not a list")
                    break
                for v in row:
                    if v is not None and not isinstance(v, (int, float, str)):
                        p.append(f"source_tables[{k}].cells[{i}] has invalid value {v!r}")
                        break

    row_ops = {"copy", "sum", "weighted_avg", "overlap_weighted"}
    col_ops = {"copy", "sum", "share_even", "weighted_avg", "overlap_weighted"}
    for name, ops_allowed in (("row_map", row_ops), ("col_map", col_ops)):
        entries = result[name]
        if not isinstance(entries, list) or not entries:
            p.append(f"{name} must be a non-empty list")
            continue
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                p.append(f"{name}[{i}] is not an object")
                continue
            if not isinstance(e.get("target"), str):
                p.append(f"{name}[{i}].target missing or not a string")
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
            wt = e.get("weights_table")
            if wt is not None and not isinstance(wt, int):
                p.append(f"{name}[{i}].weights_table must be an integer index or null")
            if op == "weighted_avg" and not isinstance(wt, int):
                p.append(f"{name}[{i}] ({e.get('target')!r}): weighted_avg requires an "
                         "integer weights_table (transcribe the counts table and "
                         "reference its index)")
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

    derive = result.setdefault("derive", None)   # tolerated if absent
    if derive is not None:
        if not isinstance(derive, dict):
            p.append("derive must be null or an object")
        else:
            if derive.get("op") != "ratio":
                p.append(f"derive.op {derive.get('op')!r} must be 'ratio'")
            for key in ("numerator_table", "denominator_table"):
                v = derive.get(key)
                if not isinstance(v, int) or not (0 <= v < len(tables)):
                    p.append(f"derive.{key} must be a valid index into source_tables")
            for name in ("row_map", "col_map"):
                for i, e in enumerate(result.get(name, [])):
                    if isinstance(e, dict) and e.get("op") == "weighted_avg":
                        p.append(f"{name}[{i}]: weighted_avg is not allowed in ratio "
                                 "mode - use additive ops (sum/copy); code divides the "
                                 "aggregated tables")

    if not isinstance(result["notes"], str):
        p.append("notes must be a single string (not a list)")
    return p


def extract(target_name, target_spec, source_text, record_path=None, dry_run=False):
    """Run one extraction (with one format-correction retry if the response
    does not conform to the contract). Returns (result_dict, record_dict)."""
    prompt = build_prompt(target_name, target_spec, source_text)

    if dry_run:
        print("--- DRY RUN: prompt that would be sent ---")
        print(prompt[:3000])
        print(f"--- ({len(prompt)} chars total; model={MODEL}) ---")
        return None, None

    import anthropic  # deferred so dry runs work without the package/key
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": prompt}]
    record = {"attempts": [], "model": MODEL}
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
            problems = validate(result)
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
