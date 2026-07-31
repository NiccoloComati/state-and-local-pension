# Resume prompt — states track

Paste the block below into Claude Code on another machine, from the project root,
to pick the states track up where 2026-07-30 left it. Kept in the repo so it travels
with the code; update it at the end of a session if the state moves on.

---

```
We are continuing the STATES track of the state & local pension sustainability model
at MIT GCFP, driving toward a working paper. Scope here is ONLY the 40 state plans —
the municipal AV-PDF extraction pipeline under `Data Extraction/` is a separate chat,
do not work on it.

Read these first, in this order, before doing anything:
  1. Documentation/states_track_context.md — start at "WHERE THIS STANDS", the top
     section. That is the state of play, what changed last session, the immediate
     next step, and the open items. Then "Decisions taken" and the "Assumption and
     limitation register". The dated sections below are the evidence trail; read
     them on demand.
  2. Documentation/session_handoff.md — the STATES section, plus "The thesis",
     "How Niccolo works", "Validation norms", "Environment quirks".
  3. Documentation/project_context.md — durable observed facts. §3.1 has the input
     vintage decomposition.
  4. Code/python/README.md — what every file is.
  5. Results/Runs/README.md — what each existing run contains.

The thesis, which must never be lost: we reframe pension sustainability
DISTRIBUTIONALLY, across outcomes and across cohorts. Lenney, Lutz & Sheiner
(Brookings) is the FOIL, not the companion — their mean/deterministic framing is
what we are arguing against. Never let an analysis collapse to a mean or median
without the distribution alongside it.

How I want you to work:

- Analysis-first. For anything substantial, show me the plan or a manifest and WAIT
  for my approval. Once I approve, execute it autonomously without checking back
  mid-stream.
- Do not overstate. Say what the evidence supports and how confident you are, and
  present options rather than conclusions when it is genuinely open. Last session
  several claims were asserted hard and then reversed; that is the failure mode to
  avoid. A keyword search finding nothing is NOT evidence of absence.
- Validate proportionally — one decisive check beats five redundant ones. But the
  standing bar for any engine change, including pure file moves, is BIT-IDENTITY:
  rerun a plan against a previous run, max difference must be 0.0. This is not a
  formality; a relocation silently shifted MA51's liability 0.7% last session
  through a relative path that returned NaN without raising.
- Every embedded assumption gets recorded AND explained in plain, non-jargon
  language — in the docs and in the run output. Say what a thing IS before saying
  what is wrong with it. I read the documentation without the code open.
- Name things literally. No coined nicknames, no descriptive suffixes on run tags.
- Data folders are sacred: move them intact, never dismantle, never delete during a
  reorganization — move to `_ARCHIVE/`.
- Update `working_context.md` as you go; durable facts go to `project_context.md`;
  keep them non-overlapping. Commit at real milestones, with NO Claude co-author
  trailer.
- The inherited Brookings state workbooks are good data. Do not frame them as a
  provenance limitation or attach a standing disclaimer to results.
- Plans that look odd are open diagnoses aimed at INCLUSION, not settled exclusions.
- Verify code and data facts freely. Stop before interpreting results or proposing
  what the paper argues — we decide that together.
- Do not spawn subagents unless I ask.

Environment: Windows, PowerShell primary (`C:\`), Bash tool available (`/c/`),
Windows Python wants `C:/` — match the path style to the shell. The project folder
is OneDrive-synced: OneDrive locks folders mid-operation, and `Remove-Item` on
project paths is sandbox-blocked, so MOVE instead of deleting. The PowerShell
console is cp1252 and chokes on Unicode in Python prints. Git tracks code and docs
only; data is gitignored and lives in OneDrive.

Where we are: inputs are settled, analysis has NOT started. The current results run
is 20260730_3. The immediate next step is a fresh 40-plan run — 20260730_3 predates
FL26's contribution-rate exception, which is the only behavioural change since, so a
new run differs from it for FL26 alone — and then the analysis in
Analysis/results.ipynb.

Start by reading the documentation above and telling me, in your own words, what
state the track is in and what you understand the next step to be. Do not start
running anything until I say so.
```
