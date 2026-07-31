# Verifying automated pension-data extraction — working guide

**Your worksheet:** `model_output_verif_worklist.xlsx` — 100 rows, every one a job for you. Nothing in it belongs to anyone else.

---

## What the project is doing

We model the long-run finances of US public pension plans — cities like Phoenix, Chicago, Los Angeles, New York. The model needs detailed tables about each plan's membership: how many active employees at each age and length of service, what they earn, how likely they are to leave, retire or die, and how many retirees there are at each age.

Those tables exist only inside **actuarial valuation reports** — long PDFs, one per plan per year, each actuarial firm using its own layout. Reading one out by hand takes hours.

We built software that does it automatically: a language model reads the whole PDF, finds the relevant table, copies it out exactly as printed, and declares which arithmetic should reshape it into the format our model needs. Ordinary code then performs that arithmetic. Your job is to check the result against the original PDF.

## The one rule

**The source PDF is the reference. Always.** Whether a number is right is settled by opening the actuarial valuation and reading the printed table. There is nothing else to compare against.

## Why verification is needed at all

The software fails in ways automated checks cannot catch, because the output usually looks entirely reasonable. The worst case we found: two plans print their tables as **images**. The text layer carries the exhibit title but no numbers at all. The software found the title and produced a full table of plausible, smoothly-declining rates — which passed every automated check we have. Those numbers were invented. We caught it only by opening the PDF.

So "the values look sensible" is never sufficient. Only a person with the document can confirm a number was actually read.

## What each row gives you

| column | meaning |
|---|---|
| `Priority` | work order — see below |
| `Plan`, `Fund` | which pension fund |
| `Table`, `Table contents` | which of the six data tables, in plain words |
| `Issue` | why this row needs attention |
| `PDF` | the document to open |
| `Model cited` | the page and exhibit title the software *claims* it read |
| `Page` | **the page where the numbers actually are** — use this one |
| `Folder` | the software's working files (see below) |

On `Page`: actuarial reports are numbered by their *printed* page, which is offset from the PDF's own page count. The software reports the printed number, so on 18 rows the page it names is not the page you need. We located the real page automatically and put it here. Where it says "only some values located automatically", be extra careful — that can itself indicate a bad extraction.

The `Folder` column points at the software's working files. `extraction.json` holds the raw table as it read it, the transformation it chose, and a plain-English `notes` field explaining what it thought it was doing — **read the notes first**. `derived.json` holds the final table after the arithmetic.

## What to check — two separate things

**Transcription.** Do the numbers in `extraction.json` match the PDF, digit for digit? These PDFs mangle easily: a text layer can split "77" into "7 7", or "2,625" into "2 ,625", and the software sometimes copies the split version.

**Transformation.** Was the right operation chosen for what the document prints? Adding figures that should have been averaged, dividing dollars by dollars instead of by a headcount, mapping a bin to the wrong column — each produces clean-looking output that is wrong.

Record these separately. They fail independently: a table can be transcribed perfectly and ruined by the next step, or look right while hiding a misread digit.

## Failure modes we have actually seen

- A whole table copied **one column late** — every value correct, every one under the wrong heading.
- A printed **"Total" line** treated as another age band.
- **Monthly** dollar amounts reported as annual — out by a factor of twelve.
- An exhibit printing **two lines per age band** (a count line and a dollar line) flattened into one table.
- **Two tables printed side by side** read as a single table.
- The **wrong population** — a disability mortality table instead of the healthy-lives one.
- **Invented numbers** where the page is an image (above).

## Priorities

Every check behind these priorities runs *without* any reference document — it compares the extraction against itself, or against an independent membership database — so when one complains, something is genuinely off.

**1-HIGH (19 rows).** An automated check already disagrees: the table's own printed totals do not add up from the cells copied, or the headcount contradicts an independent database, or the values are implausible. These are usually real errors. Start here.

**2-MED (25 rows).** Nobody has ever checked these. Confirm against the PDF.

**3-LOW (56 rows).** Nothing explicit complained. Note that the fabricated-table case above would have sat in this tier, so do actually open the PDF.

## When a row is not simply right or wrong

- **Image, not text** — the table is a picture, so our software cannot read it. Say so explicitly; this is *not* the same as "not in the document", and we need an exact count because those need different software.
- **Genuinely not in the document** — the plan does not publish it.
- **Needs a methodology decision** — e.g. the document gives rates by age only and something must be assumed to fill in years of service, or it is unclear which group of retirees counts. **Do not decide these.** Record the question and move on; they are Niccolo's.
- **A real error** — say what it is and possibly give the page.

## What to write

Three columns at the end.

**`Result`** — pick from the dropdown:

| option | means |
|---|---|
| `Correct` | matches the PDF |
| `Wrong numbers` | a value was misread |
| `Wrong table` | it used the wrong exhibit |
| `Wrong method` | values transcribed right, the calculation applied to them is wrong |
| `Image` | the table is a picture, so it cannot be read at all |
| `Not in PDF` | the plan genuinely does not publish this |
| `Question` | needs a methodology decision — record it, don't decide it |

**`Why`** — one line saying what you saw and where. Name the page and exhibit, even when the answer is `Correct` ("matches Exhibit F.3, p.38"), because a verdict nobody can re-check is not usable. When it's wrong, say roughly how — "every value one column to the right", "these are monthly, not annual", "read 7 and 7 where the page prints 77" etc.

**`Correct source`** — only when it used the wrong exhibit or claims the data is missing: where the right table actually is (page and exhibit name). Leave blank otherwise.