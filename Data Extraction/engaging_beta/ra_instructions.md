# Checking automated pension-data extraction against the source documents

**Your worksheet:** `ra_worklist_round3.csv` (101 rows). Every row is a job for
you. Nothing in it belongs to anyone else.

---

## 1. What this project is doing, in plain terms

We model the long-run finances of US public pension plans (cities like Phoenix,
Chicago, Los Angeles). To do that the model needs detailed tables about each
plan's members — how many active employees there are at each age and length of
service, what they earn, how likely they are to quit, retire, or die, and how
many retirees there are at each age.

Those tables exist only inside **actuarial valuation reports**: long PDFs, one
per plan per year, written by actuarial firms. Reading one out by hand takes
hours per plan.

We have built software that does it automatically: a language model reads the
whole PDF, finds the right table, copies it out exactly as printed, and states
which arithmetic should be applied to reshape it into the format our model
needs. Separate, ordinary code then does that arithmetic.

**Your job is to check its work against the original PDFs.** The software can be
confidently wrong, and only a person looking at the source document can tell.

## 2. The single most important rule

**The source PDF is the reference. Always. There is nothing else to compare
against.** Your judgement of whether a number is right comes from opening the
actuarial valuation and reading the printed table.

## 3. What you are checking

Open the row's `artifacts_folder`. It contains:

- **`extraction.json`** — the raw table exactly as the software read it off the
  page, the transformation it chose, and a plain-English `notes` field where it
  explains what it thought it was doing. **Read the notes first.**
- **`derived.json`** — the final table after the arithmetic.

The row also tells you the `source_pdf` and, in `model_says_it_used`, the page
numbers and table titles the software claims it read. Start there.

Check **two separate things**, and record them separately, because they fail
independently:

**(a) Transcription** — do the numbers in `extraction.json` match the PDF, digit
for digit? A table can be perfectly transcribed and still be useless if the next
step was wrong, and it can look plausible while hiding a misread digit.

**(b) Transformation** — was the right operation chosen for what the document
actually prints? Adding up numbers that should have been averaged, dividing
dollars by dollars instead of by a headcount, mapping a bin to the wrong column
— all produce clean-looking output that is wrong.

## 4. Mistakes we have actually seen — look for these

- An entire table copied **one column late**, so every value is correct but sits
  under the wrong heading. Caused by the PDF's text layer splitting a number
  ("2 ,625" is one number, 2625).
- A printed **"Total" line** treated as if it were another age group.
- **Monthly** dollar amounts reported as annual (out by a factor of 12).
- An exhibit that prints **two lines per age band** — a headcount line and a
  dollar line — flattened into one table.
- **Two tables printed side by side** on one page, read as a single table.
- Numbers taken from the **wrong population** — e.g. the disability mortality
  table instead of the healthy one.

## 5. Priorities

Work down the `priority` column.

All three checks behind these priorities are done WITHOUT any reference
document — they compare the extraction against itself or against an independent
membership database — so when one of them complains, something is genuinely off.

- **1-HIGH (20 rows)** — an automated check already disagrees. The `why_flagged`
  column says which: the table's own printed totals do not add up from the cells
  it copied, or the headcount contradicts an independent database, or the output
  audit judges the values implausible (a mortality rate that falls with age, an
  "average salary" of a million dollars). These almost always mean a real
  mistake. Spend your time here.
- **2-MED (25 rows)** — nobody has ever checked these at all. Confirm against
  the PDF.
- **3-LOW (56 rows)** — no automated check complained. A spot-check of a few
  cells against the printed table is enough.

## 6. When a row is not simply right or wrong

Record which of these it is, and move on:

- **Image, not text** — the table is a picture, so our text-reading software
  physically cannot see it. Say so explicitly. This is NOT the same as "not in
  the document", and we need an exact count of these, because they need a
  different kind of software. (At least one plan, Philadelphia, is like this.)
- **Genuinely not in the document** — the plan simply does not publish it.
- **Needs a judgement call about method** — e.g. the document gives rates by age
  only and something must be assumed to fill in years of service, or it is
  unclear which group of retirees counts. **Do not decide these.** Record the
  question and move on; they are Niccolo's to settle.
- **A real extraction or arithmetic error** — record the PDF page and the
  correct value.

## 7. What to write

Fill in the last five columns of your row:

| column | what to put |
|---|---|
| `VERDICT` | `correct` / `wrong` / `needs-decision` / `image-only` / `not-in-document` |
| `LAYER` | `transcription` / `transformation` / `assumption` / `image` |
| `PDF_PAGE_CHECKED` | the page and exhibit you looked at — **always, even when correct** |
| `CORRECT_VALUE_IF_WRONG` | what the PDF actually prints |
| `NOTES` | anything that does not fit above |

A verdict of "correct" with no page reference cannot be re-checked by anyone
else, so it is not usable. Always give the page.

## 8. How to work

Do a chunk, then review it with Niccolo before continuing — it is a loop, not a
single pass. Rows may re-open after we fix something and re-run; that is normal
and not wasted work. If a whole plan looks broken in the same way, stop and say
so rather than filling in fifty rows.

Ask when something is ambiguous. "I don't know which of these two tables it
should have used" is a useful answer.
