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
    },
    "required": ["page", "title", "row_labels", "col_labels", "cells",
                 "printed_row_totals", "printed_col_totals"],
    "additionalProperties": False,
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
                                "description": "source row labels of source_tables[0] combined into this target row (empty if no data exists)"},
                    "op": {"type": "string", "enum": ["copy", "sum", "weighted_avg"]},
                    "weights_table": {"anyOf": [{"type": "integer"}, {"type": "null"}],
                                      "description": "index into source_tables providing weights (weighted_avg only, else null)"},
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
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "op": {"type": "string", "enum": ["copy", "sum", "share_even"]},
                },
                "required": ["target", "sources", "op"],
                "additionalProperties": False,
            },
        },
        "notes": {
            "type": "string",
            "description": "every judgment call: why these tables, ambiguities, anything the maps cannot express",
        },
    },
    "required": ["source_tables", "row_map", "col_map", "notes"],
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
operations (copy, sum, weighted_avg for rows; copy, sum, share_even for columns). \
Deterministic code will execute these - you do NO arithmetic. If a weighted average is \
needed (e.g. merging salary bins), also transcribe the table that provides the weights \
(e.g. member counts) as an additional source table and reference it by index.

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
  "notes": "one plain string, not a list"
}
Constraints:
- source_tables[k].cells is a LIST OF LISTS of values (number, "*", or null),
  one inner list per row_label, one value per col_label. NOT objects.
- row_map/col_map "sources" are PLAIN STRINGS (row/col labels of
  source_tables[0]). NOT objects. Auxiliary tables are referenced only via
  "weights_table" (an integer index into source_tables, or null).
- row ops: "copy" | "sum" | "weighted_avg"; col ops: "copy" | "sum" | "share_even".
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

    row_ops = {"copy", "sum", "weighted_avg"}
    col_ops = {"copy", "sum", "share_even"}
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
            if e.get("op") not in ops_allowed:
                p.append(f"{name}[{i}].op {e.get('op')!r} not in {sorted(ops_allowed)}")
            if name == "row_map":
                wt = e.get("weights_table", "MISSING")
                if wt is not None and not isinstance(wt, int):
                    p.append(f"row_map[{i}].weights_table must be an integer index or null")

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
