# Engaging open-weights beta — full session handoff

**Written 2026-07-22.** This file captures EVERYTHING needed to continue the
open-weights migration beta on MIT Engaging from another machine: the goal,
the decision bar, the exact cluster state, every command that worked, every
error hit and its fix, and the precise next action. Read it together with
`runbook.md` (the concise procedure) in this same folder. If you only read one
thing, read the "EXACT STATE" and "NEXT ACTION" sections.

---

## 0d. LATEST — 2026-07-27 session 5: FULL SWEEP DONE + cell-level diagnosis (READ FIRST)

The preemption problem is SOLVED (resumable `run_batch --batch-dir` + `sbatch
--requeue`; `engaging_beta/sweep_requeue.sbatch`) and the **full 96-cell sweep
completed** post all this-week's fixes. **The diagnosis is in
`engaging_beta/sweep_20260727/diagnosis.md` (READ IT) — grid, owner routing, and
the 4-way triage (solve-now / dig-deeper / assumption / hardest).** Machine-
readable: `sweep_20260727/summary.json` + `ra_worklist.csv` (per-cell owner).
The RA's job spec is `engaging_beta/ra_tasks.md`.

**Headline:** 13/96 clean; owner split **58 RA · 26 assumption · 12 me**.
Transcription machinery is strong (every Age_Serv_Num 0.87-1.0; wages 0.9-1.0
where averages are printed). The remaining losses are NOT model transcription
failure - they are (a) a few MY code/instruction fixes and (b) register
decisions. Key adjudications (from reading artifacts, not scores):
- **Wage `0.00(ratio)` on chi_edu/ff/gen/pol = MINE, highest leverage:** the
  model transcribed salary-TOTALS + counts correctly but dropped `derive=ratio`
  -> raw million-dollar totals. NOT an interleaved-layout failure (earlier guess
  wrong). One instruction/validator fix likely flips all four to ~1.0.
- **mil Retirement `0.00(map)` = MINE** (column mis-map).
- **sd Retirement `0.00(asmpt)` = assumption** (can't isolate service retirees;
  register 6c).
- **chi_pol counts 0.87 = one-row transcription shift** (RA).
- **Ret/Sep/Avg_Mort 0.00s = register-gated** (tier/convention/blend).
- **7 crashes = mine to diagnose;** image-only tables = UNKNOWN volume, need a
  vision model (the RA's Stream-B sizes it).

**NEXT SESSION order:** (1) fix the wage `derive=ratio` miss (biggest lever,
offline) + mil Retirement mapping; (2) diagnose the 7 crashes (truncation
classifier + dump dir are wired); (3) re-run the affected cells to confirm
(the preemption-proof sbatch makes this cheap); (4) the register sit-down owns
the assumption bucket. To re-run: submit `engaging_beta/sweep_requeue.sbatch`
(resumes `_batch_resumable`; delete that dir on the cluster first for a clean
full re-sweep, or scope PLANS/TARGETS in the script).

Everything below (§0c, §0b, §0, §1-9) is still valid background.

---

## 0c. LATEST — 2026-07-25 session 4: sweep-2 partial (32 runs) + a vLLM BOOT BLOCKER (READ FIRST)

Ran a re-sweep after the 6 bulk-fixes on a 2-GPU node (node5200). Got **32 of
96 runs** before the 3h wall killed the alloc; the partial `summary.json` is
saved on scratch at `runs/_batch_20260725_143259/` (survives). Then spent hours
fighting infrastructure and hit a hard boot blocker (below). **No code is
broken; this is a cluster/hardware problem.**

### What the 32 runs already tell us (fix-verification, adjudicated)
- **GATE (Age_Serv_Num) is SOLID and a headline win landed:** chi_edu 1.0,
  chi_ff 1.0, chi_gen 0.983, **chi_pol 1.0** — chi_pol is the Segal interleaved
  layout that was stuck at 0.868 on 2026-07-22. best-of-N + the hardened
  totals-check (fix #4) now SELECT the un-shifted sample (n_att=6). **The Segal
  count shift is fixed.** PPD reconcile `ok` on all counts.
- **STILL BROKEN — Age_Serv_Wage on Segal chi plans (all 0.0):** chi_edu 0.02,
  chi_ff/chi_gen/chi_pol 0.0. The interleaved total$+count layout breaks the
  ratio mapping (all-null derivation). This is the Segal-tooling bucket
  (EXTRACT_APPEND_TABLES A/B, still not run). #2 fixed GRS wage (phx 0.93) but
  not this layout.
- **STILL CRASHING — truncation at 64000 on some plans** (bos ASW/Sep,
  chi_edu/chi_gen Avg_Mort/Retirement): over-transcription runaway; fix #3
  (instruction) did NOT stop it. Needs a hard table-count/output cap.
- **Rate/blend (Ret/Sep/Avg_Mort): mostly 0.0 or crash** — bucket E, expected,
  register-decision territory, low priority.
- NOT yet re-tested (were in the unfinished 64): **mil Age_Serv_Num (#5
  reconcile — the critical one)**, dal Ret_Rate (#C per_1000), phx/sd
  regression. Next session must get these.

### THE BOOT BLOCKER (2026-07-25 evening) — for next session
2-GPU (TP=2) boot crashes at startup with **`torch.AcceleratorError: CUDA
error: an illegal memory access`** in
`vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py:1138
_warmup_prefill_kernels`, during `profile_run`. The visible
`CUDASymmetricMemory`/`CUDAPeerAllocInfo` wall is just the teardown.
- **node5200 booted TP=2 fine** (ran the 32 runs) with the STANDARD config.
- **node5201 AND node4002 both crash identically** at that GDN kernel — so it
  is NOT one bad GPU. Tried, all still crashed: `--enforce-eager` (skips
  torch.compile but not the Triton GDN kernel), `--disable-custom-all-reduce`.
- The **preemptable+lean allocation flags are NOT the cause** — node5200 used
  the identical `-p mit_preemptable -N1 --gres=gpu:h200:2 -c 8 --mem=96G`
  request and worked. (Niccolo suspected the alloc method; ruled out by
  node5200.)
- **Cache-poison hypothesis TESTED, did NOT fix it (but the test was dirty).**
  Tried on node4002: `rm -rf ~/.cache/vllm ~/.cache/torch ~/.triton
  ~/.cache/flashinfer` then a standard TP=2 boot -> STILL crashed identically.
  BUT the wipe was INCOMPLETE: `rm` failed on a couple of `.nfs*` lock files
  ("Device or resource busy") because vllm workers were still dying when it
  ran, so some cache survived. So the theory isn't cleanly disproven - a
  FULLY clean wipe was never actually achieved.
- **RECOMMENDED next-session order (stop the TP=2 roulette after ONE clean
  try):**
  1. Fresh node. Kill everything and VERIFY empty first:
     `pkill -9 -u ncomati -f vllm; sleep 8; pgrep -af vllm || echo clean`,
     THEN wipe: `rm -rf ~/.cache/vllm ~/.cache/torch ~/.triton
     ~/.cache/flashinfer` (should have NO busy-file errors this time),
     THEN the standard TP=2 boot. This is the clean cache test we never got.
  2. If that STILL crashes at `_warmup_prefill_kernels` -> the cache is
     exonerated; it's the vLLM 0.25.1 GDN kernel vs these H200 nodes. DO NOT
     keep booting TP=2. Two real options then: (a) **go TP=1** (below) and get
     the critical runs; (b) rebuild the container from a different pinned vLLM
     tag (heavier; the §7 apptainer build recipe) and retry TP=2 - a later-vLLM
     GDN kernel may not have the bug. Worth raising with Engaging/ORCD support
     too (reproducible CUDA illegal-access in a stock vLLM kernel on their
     H200s).
- **Reliable fallback that DOES boot: TP=1 single GPU.**
  `--tensor-parallel-size 1 --max-model-len 131072 --gpu-memory-utilization
  0.97 --enforce-eager` + `export EXTRACT_MAX_TOKENS=16000`. It physically
  can't hit the cross-GPU peer/kernel path and booted fine on 2026-07-24.
  Slower (no prefix-cache room -> re-prefills each doc; best-of-N amplifies
  it), so use it for a SMALL targeted run (mil/dal/phx/sd/lax_uty ASN +
  Age_Serv_Wage + Ret_Rate) to close #5/#C/regression + the Segal wage
  picture - NOT the full 96. **If tonight repeats, just do this and make
  progress instead of fighting TP=2.**
### Next-session order (short) — do NOT repeat the 2026-07-25 boot-roulette
1. Fresh preemptable alloc (gotcha #6). ONE clean TP=2 attempt: kill+verify
   procs, do a CLEAN cache wipe (no busy-file errors), standard TP=2 boot.
2. If it boots: finish the sweep (or at least mil/dal/phx/sd/lax_uty ASN +
   Age_Serv_Wage + Ret_Rate) to close #5/#C/regression + the Segal wage picture.
3. If it STILL crashes at `_warmup_prefill_kernels`: DON'T keep booting TP=2.
   Switch to **TP=1** for the small targeted set and make progress; leave a
   possible container-rebuild / support ticket for later. (Full 96-sweep waits
   for a working TP=2.)
4. Then the next bulk-fix round: Segal wage mapping (EXTRACT_APPEND_TABLES A/B)
   + a hard truncation cap.

Everything below (§0b, §0, §1-9) is still valid background.

---

## 0b. LATEST — 2026-07-23 session 3: first full sweep + bulk-fix pass (READ FIRST)

The full **16-plan x 6-target sweep RAN** (batch `_batch_20260723_114421`;
detail in the 2026-07-23 dev-log entries of `data_extraction_context.md`).
**GATE HELD, GO reconfirmed:** Age_Serv_Num >=0.95 for 10 plans; several
sub-1.0 scores are the model faithfully matching the PDF where the human
WORKBOOK is wrong. Aggregate: 54 scored / 12 crash / 15 prod / 15 unavail /
11 clean-reconciled. We then did a bulk-fix pass BY ROOT CAUSE (all committed +
pushed; suite 13/13):
- **#2 wage table-ordering** (counts-at-index-0 -> weighted-avg-of-counts):
  guard + spec rule. **CONFIRMED LIVE: phx wage 0.0 -> 0.932.**
- **#4 averages false-suspect**: totals-check no longer fires on average tables
  (a sum can't be < its max element).
- **#5 plan-total reconciliation in best-of-N** (the big one): for count
  targets, best-of-N now runs the executor on each candidate and prefers the
  one whose derived total matches PPD actives_tot - catches mil's 12-table
  over-sum (27,858 vs 10,974) that per-table totals-checks can't see. Turns
  the PPD flag into a SELECTOR.
- **C: per_1000 values_unit** (rate-per-1,000 tables, e.g. dal Ret_Rate) +
  **totals-vs-averages ratio detection** (chi_ff used weighted_avg on a
  dollar-totals table).
- **D: derive=sum aligns by POSITION** (shape check, not identical labels) ->
  fixes bos; other arity crashes triaged (units->C, interleaved->Segal, a
  couple one-off hard tables left on the attention list).
NONE of these fixes are verified live except #2. **They need a re-sweep.**

### GOTCHAS — bake these into every session (learned the hard way 2026-07-23/24)
1. **`module load miniforge/24.3.0-0` before ANY `python`** (and `module load
   apptainer/1.4.2` before any `apptainer`). The login default python is 3.6 /
   absent -> "python: command not found". EVERY fresh shell needs it, and a
   **new tmux window does NOT inherit modules OR your `export`s** - re-run the
   module load + the EXTRACT_* exports in each new window. This bit us ~4x.
2. **Allocate co-located GPUs:** `salloc ... -N 1 --gres=gpu:h200:2` — NOT
   `-G h200:2`. `-G` lets the scheduler scatter the 2 GPUs across 2 NODES
   (1 each), and TP=2 then sees only 1 GPU per node -> "World size (2) is
   larger than available GPUs (1)". `-N 1 --gres` forces both onto one node.
3. **Single-GPU fallback (no re-queue needed if you only got 1 GPU):** the MoE
   + hybrid-attention model fits on ONE H200. Boot with `--tensor-parallel-size
   1 --max-model-len 131072 --gpu-memory-utilization 0.97 --enforce-eager`, and
   set `EXTRACT_MAX_TOKENS=16000` (131072 ctx can't hold a 90K doc + 64K output
   + a retry; 16K output >> the ~7K a healthy response needs). Confirmed working
   2026-07-24. Slower (no TP) but runs the whole sweep.
4. **Launch the vLLM boot block ONCE.** A second launch hits `OSError [Errno 98]
   Address already in use` (vLLM binds the port before loading). If the `tail`
   looks stuck, Ctrl+C the TAIL only and read the log - do not relaunch.
5. **Verify the GPU count before booting:** `nvidia-smi -L` must show the number
   of H200s you need (2 for TP=2). `SLURM_GPUS_ON_NODE` / `scontrol show job`
   confirm placement.
6. **ALLOCATION STRATEGY - use preemptable + lean (the fast lane).** A
   co-located H200 pair on `mit_normal_gpu` with a 6h wall is the single
   hardest thing to schedule: waited **5h and never granted** on 2026-07-25.
   The fix that granted in **~minutes**:
   `salloc -p mit_preemptable -N 1 --gres=gpu:h200:2 -c 8 --mem=96G -t 3:00:00`.
   Why: (a) `mit_preemptable` backfills idle capacity (the decisive lever);
   (b) lean `-c 8 --mem=96G` (the sweep needs little host cpu/RAM - the model
   lives in GPU memory) schedules easier; (c) a modest wall helps backfill but
   is NOT the main lever - preemptable allows up to 48h, so if a session needs
   more runtime, `-t 6:00:00`+ on the same lean preemptable request still grants
   fast. 3h comfortably covers one full sweep (~8min boot + 1-2h). Wall expiry
   is as safe as preemption (summary.json is per-run; resume the rest). **Preemption is SAFE for us:** `run_batch`
   writes `summary.json` after every run, so a kill just means re-boot +
   finish the remaining plans, nothing completed is lost. Fallback if H200s
   are scarce: `--gres=gpu:h100:2` (2x H100 80GB = 160GB, still fits the 127GB
   model at TP=2; drop `--max-model-len` to 131072 if the tighter KV OOMs).
   HEDGE without losing a queued job: leave it pending, open a 2nd SSH,
   submit the preemptable one there, take whichever grants first.

### NEXT-ALLOCATION CHECKLIST (do these next session, in order)

**1. Boot the server** (cluster). Use the PREEMPTABLE + LEAN request per gotcha
#6 - it granted in minutes on 2026-07-25 after 5h of nothing on mit_normal_gpu:
```bash
ssh ncomati@orcd-login.mit.edu
salloc -p mit_preemptable -N 1 --gres=gpu:h200:2 -c 8 --mem=96G -t 3:00:00
# (fallback if H200s scarce: --gres=gpu:h100:2 ; last resort: mit_normal_gpu -t 6:00:00)
nvidia-smi -L                         # MUST show 2 H200 (gotcha #2/#5)
tmux new -s vllm
module load apptainer/1.4.2
cd /orcd/scratch/orcd/011/ncomati
apptainer exec --nv -B /orcd/scratch/orcd/011/ncomati --env CC=gcc --env CXX=g++ \
  containers/vllm_dir \
  vllm serve /orcd/scratch/orcd/011/ncomati/models/qwen35-122b-fp8 \
    --served-model-name qwen35-122b-fp8 --tensor-parallel-size 2 \
    --max-model-len 262144 --gpu-memory-utilization 0.90 --port 8000 \
  > /orcd/scratch/orcd/011/ncomati/vllm.log 2>&1 &
tail -f /orcd/scratch/orcd/011/ncomati/vllm.log   # wait 'Application startup complete', Ctrl+C, then Ctrl+b d
```
If you only got 1 GPU and don't want to re-queue, use the single-GPU boot from
gotcha #3 instead (TP=1, 131072, and add EXTRACT_MAX_TOKENS=16000 in step 2).

**2. Pull the fixes + set the env** (cluster). `module load miniforge` per
gotcha #1 - REQUIRED before python, and again in every new tmux window:
```bash
module load miniforge/24.3.0-0
cd /orcd/scratch/orcd/011/ncomati/state-and-local-pension && git pull
cd "Data Extraction"
python -c "import pdfplumber, pypdf, openpyxl; print('deps ok')" || pip install --user -q pdfplumber pypdf openpyxl
export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1 EXTRACT_MODEL=qwen35-122b-fp8 OPENAI_API_KEY=dummy
# on a SINGLE-GPU (131072) boot also: export EXTRACT_MAX_TOKENS=16000
```

**3. Segal A/B** (2-GPU/262144 boots ONLY - the APPEND_TABLES lever inflates the
prompt and overflows a single-GPU 131072 window; skip it on TP=1). Table-append
lever OFF then ON on the two interleaved-layout plans:
```bash
python pipeline/run_batch.py --plans chi_pol,lax_uty --targets Age_Serv_Num,Age_Serv_Wage
EXTRACT_APPEND_TABLES=1 python pipeline/run_batch.py --plans chi_pol,lax_uty --targets Age_Serv_Num,Age_Serv_Wage
```
Compare: if APPEND_TABLES=1 clears the column shift (chi_pol Age_Serv_Num up
from 0.868, lax_uty wage off its shift) without hurting, enable it for step 4;
else leave it off and the Segal plans stay flagged (acceptable).

**4. Full re-sweep** (cluster; ~1h on 2 GPUs, ~2-3h on 1). Run it inside a tmux
window (re-load miniforge + re-export env there per gotcha #1). Add
`EXTRACT_APPEND_TABLES=1` in front only if step 3 favored it:
```bash
python pipeline/run_batch.py --quiet | tee /orcd/scratch/orcd/011/ncomati/sweep2.log
```
Expected improvements vs sweep 1: mil/Age_Serv_Num reconciles (#5) or is
correctly flagged; wage 0.0s recover (#2/#3 ratio); the 6 truncation crashes
gone (mil now completes, over-transcription flagged not crashed); dal Ret_Rate
+ chi Avg_Mort scale via per_1000 (#C); bos counts no longer crash (#D).

**5. Pull the summary back for adjudication** (cluster then LAPTOP):
```bash
# cluster:
B=$(ls -dt runs/_batch_* | head -1); tar -czf /orcd/scratch/orcd/011/ncomati/sweep2_out.tgz "$B" -C /orcd/scratch/orcd/011/ncomati sweep2.log
# laptop PowerShell:
scp ncomati@orcd-login.mit.edu:/orcd/scratch/orcd/011/ncomati/sweep2_out.tgz "$env:TEMP\"
```
Then Claude reads it (extract to a temp dir, read summary.json + the log) and
we adjudicate sweep-2 vs sweep-1 by root cause + plan the next bulk-fix round.

**6. Release the alloc** when done: `tmux attach -t vllm` -> Ctrl+C the server,
`exit`; or `pkill -u ncomati -f "vllm serve"; exit`.

---

## 0. LATEST STATE — 2026-07-22 session 2 (READ THIS FIRST; supersedes §6)

**The server booted and the digit-fidelity gate (kill-test #4) PASSED.** We ran
the battery live on 2x H200 and adjudicated it. Verdict: **GO with Opus as a
targeted fallback on interleaved (Segal) layouts.**

### Boot fixes discovered (needed to re-boot from scratch)
- The apptainer image's vLLM (0.25.1) DOES support Qwen3.5 — the predicted
  "too old, rebuild" branch did NOT happen. The real boot blocker was Triton
  JIT (Qwen3.5's GDN attention compiles kernels at load) picking up a **host
  spack `CC`** that isn't inside the container. **Fix: add
  `--env CC=gcc --env CXX=g++`** to the `apptainer exec`.
- Booted at **`--max-model-len 262144`** (NOT 131072): the retry conversation
  (90K-token doc + first response + correction + output) overflows 131072 and
  vLLM 400s. 262144 fits VRAM fine (hybrid-attention KV is cheap). The exact
  working boot command is in §6 Step B with those two changes.
- Queue (kill-test #2): the H200 alloc was **near-instant** — non-issue.

### Fidelity battery (kill-test #4) — 5/6 digit-exact, 1 miss
| plan/target (firm) | result | note |
|---|---|---|
| mil Age_Serv_Num (novel) | PASS | found 9 employer tables, all digits reconcile to 10,974 (= workbook = PPD actives_tot). Crashed on a phantom `derive.tables` index (ops slip, not digits). |
| phx Age_Serv_Num (GRS) | PASS | 59/59 = 1.0 |
| phx Age_Serv_Wage (GRS) | PASS | 57/59; the 2 "misses" are the KNOWN workbook typo (86306 vs PDF 86309) — model right |
| phx Retirement (GRS) | PASS | 22/22 = 1.0; chose Service-Retirees population + ratio + share_even unprompted |
| sd Age_Serv_Num (Cheiron) | PASS | totals-check clean; 5 "misses" = KNOWN human error (collector dropped 70+) — model right |
| chi_pol Age_Serv_Num (Segal) | **MISS** | one-column-LEFT shift on the interleaved Male/Female split tables; its own col-totals don't reconcile; retry didn't fix. Also skipped the cleaner combined **Part III (p.46)**. |

Headline: **three passes reproduced known human ground-truth errors** — Qwen
transcribes the PDFs more faithfully than the workbooks in those spots. The one
miss is the hardest layout in the corpus AND partly self-inflicted (wrong
source table).

### The strategy shift (Niccolo's call — endorsed)
Local inference is $0 and seconds/run, so the Opus-era caution (surgical,
one-at-a-time, each run costs money) is obsolete. Go **breadth-first**: run the
whole corpus rough, collect the failure map, then fix instructions/tools in
BULK. Free/fast retries make ops-sloppiness a non-issue. The key technical
point: greedy decoding is DETERMINISTIC, so re-running can't escape a mistake —
**best-of-N with a verifier** (sample at temperature, keep the candidate whose
cells reconcile with the printed totals) is what turns "many free attempts"
into a real fix for the Segal shift.

### New machinery built this session (committed; `git pull` on the cluster)
- **Best-of-N in `pipeline/extract.py`** (local backend only): greedy baseline
  -> one greedy correction retry -> up to `EXTRACT_SAMPLES` (default 6)
  independent draws at `EXTRACT_TEMPERATURE` (default 0.6), keeping the best by
  (fewest contract violations, then fewest totals violations). Per-sample seeds
  keep it reproducible. `EXTRACT_SAMPLES=0` disables it (pure greedy A/B).
- **`pipeline/run_batch.py`**: runs every plan x target, writes
  `runs/_batch_<stamp>/summary.{json,csv}`, prints a plans x targets matrix +
  a ranked "attention list" (crashes, suspect-but-scored, imperfect, no-truth+
  suspect). `run_test.run_one()` was factored out as the shared unit.
- **`ops.totals_check` hardened**: a transcribed `Total` column/row is excluded
  from the reconciliation, killing the false "2x" TRANSCRIPTION-SUSPECT alarm
  (phx/chi) so the best-of-N verifier isn't polluted. Genuine shifts still fire.
- Co-author trailer disabled in commits per Niccolo (`.claude/settings.local.json`).

**Best-of-N validated live (2026-07-22):** `run_batch.py --plans mil,chi_pol
--targets Age_Serv_Num` ->
- mil: CRASH -> **1.0** (sample4 clean; phantom-index slip fixed by sampling).
- chi_pol: 0.71 -> **0.868, flagged SUSPECT** — sampling made it pick the
  correct combined Part III table, but the Segal 60-63-row column shift
  persists across all 6 samples; the totals-check CAUGHT it (didn't silently
  pass). This is the trust property: hard layouts get auto-flagged, not
  corrupted. Segal needs TOOLING or more sampling, NOT Opus fallback (Niccolo:
  Opus fallback is operationally too messy - ruled out).

### THE FULL SWEEP IS BUILT AND READY — blocked only on the cloud queue

As of commit **c2b5a9d** (pushed), everything for the breadth-first mass test
is committed. Niccolo tried to run it on 2026-07-22/23 but **the Engaging GPU
queue was slow** and he had to switch machines before an alloc came through.
Nothing is half-done; the next session just needs a GPU alloc to run the sweep.
What's built (see the 2026-07-22 dev-log entries in `data_extraction_context.md`
for detail):
- **16-plan corpus registry** in `pipeline/run_test.py` (`PLANS`), each with its
  `ppd_id`: phx, chi_pol, sd, mil, aus, bos (validated 6) + chi_edu(11),
  chi_ff(206), chi_gen(145), dal(201), hou_pol(208), lax_gen(139), lax_uty(141),
  lax_ffpol(140), phi(152), sf(98). (AVs still missing in-folder for
  dc/den/fw/nsh/nyc/sea + hou gen/ff -> not sweepable yet.)
- **best-of-N** in `extract.py` (greedy -> greedy retry -> up to
  EXTRACT_SAMPLES=6 temperature-0.6 draws, keep best by contract-then-totals
  violations; per-sample seeds reproducible).
- **`ops.totals_check`** hardened (drops a transcribed Total column -> no false
  2x SUSPECT alarm; genuine shifts still caught).
- **`ppd_check.py`** redundant verifier (derived count total vs PPD
  actives_tot; catches whole tables dropped/doubled that a shift-conserving
  totals-check can't; works with no workbook; graceful if the PPD file is
  absent). Wired into Age_Serv_Num runs.
- **prefer-combined-table hint** (SYSTEM prompt) - fixes chi_pol source
  selection deterministically.
- **opt-in table appendix** `EXTRACT_APPEND_TABLES=1` (default OFF) - the real
  Segal lever (pdfplumber-detected tables as clean pipe grids); A/B it on
  chi_pol without touching the default path.
- `run_batch.py` writes `runs/_batch_<stamp>/summary.{json,csv}` (incremental)
  + prints a plans x targets matrix and a ranked attention list; flags '!' =
  totals-suspect, '~' = PPD count off.
- Suite 12/12 green; commits no longer add a Claude co-author trailer.

### NEXT ACTION — the exact sequence to RUN THE MASS TEST (re-propose this verbatim)

Distinguish **LAPTOP** vs **cluster** shells. The prior session's server died on
the SSH drop, so re-boot under **tmux** so a disconnect can't kill it.

**A. Re-boot the server (cluster), inside tmux:**
```bash
ssh ncomati@orcd-login.mit.edu
salloc -p mit_normal_gpu -G h200:2 -c 16 --mem=200G -t 6:00:00
tmux new -s vllm
module load apptainer/1.4.2
cd /orcd/scratch/orcd/011/ncomati
apptainer exec --nv -B /orcd/scratch/orcd/011/ncomati --env CC=gcc --env CXX=g++ \
  containers/vllm_dir \
  vllm serve /orcd/scratch/orcd/011/ncomati/models/qwen35-122b-fp8 \
    --served-model-name qwen35-122b-fp8 --tensor-parallel-size 2 \
    --max-model-len 262144 --gpu-memory-utilization 0.90 --port 8000 \
  > /orcd/scratch/orcd/011/ncomati/vllm.log 2>&1 &
tail -f /orcd/scratch/orcd/011/ncomati/vllm.log
```
Wait for `Application startup complete`, Ctrl+C the tail, then **detach**:
`Ctrl+b` then `d`. (Reattach: `tmux attach -t vllm`. If the queue is slow,
that's the current blocker - note the wait.)

**B. Pull the code (cluster):**
```bash
cd /orcd/scratch/orcd/011/ncomati/state-and-local-pension && git pull
```

**C. Upload the corpus + PPD file (LAPTOP - PowerShell; git carries only code,
the data is gitignored):**
```powershell
cd "C:\Users\nicco\Massachusetts Institute of Technology\MIT Golub Center for Finance and Policy - Documents (1)\Research and Education\Projects\State and Local Pension"
tar --exclude='*_CAFR_*' --exclude='*_ACFR_*' --exclude='*Financial*' -czf "$env:TEMP\corpus.tgz" "Data\Plans\Cities" "Data\Common\states\ppd-data-latest.xlsx"
scp "$env:TEMP\corpus.tgz" ncomati@orcd-login.mit.edu:/orcd/scratch/orcd/011/ncomati/
```
Then unpack (**cluster**), into the repo root:
```bash
cd /orcd/scratch/orcd/011/ncomati/state-and-local-pension && tar xzf /orcd/scratch/orcd/011/ncomati/corpus.tgz && ls Data/Common/states/ppd-data-latest.xlsx
```

**D. Run the full sweep (cluster):**
```bash
cd "Data Extraction"
export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1 EXTRACT_MODEL=qwen35-122b-fp8 OPENAI_API_KEY=dummy
python pipeline/run_batch.py --quiet | tee /orcd/scratch/orcd/011/ncomati/sweep1.log
```
96 runs (16 plans x 6 targets); best-of-N escalates only on hard ones, ~1h.
Smoke-test the plumbing first if wanted:
`python pipeline/run_batch.py --plans sf,phi --targets Age_Serv_Num`.
Expect several new-plan sheets to be blank -> `prod/*` (production mode, no
score); the PPD cross-check still sanity-checks those.

**Then paste the BATCH SUMMARY matrix + attention list back** -> read the
aggregate failure map together -> bulk instruction/tooling fix pass (incl. the
`EXTRACT_APPEND_TABLES=1` A/B on the Segal-shift docs). That bulk-fix loop is
step 4 of the 4-point plan and the whole point of going breadth-first.

---

## 1. WHY we are doing this (the goal and the decision bar)

We are testing whether a **pinned open-weights model** can replace
`claude-opus-4-8` for **Stage A** of the AV-extraction pipeline, served on MIT
Engaging GPUs via vLLM.

Two real motivations (cost is NOT one — the whole remaining corpus is only
~$150-300 of API):
1. **Independence** from Anthropic/Parley (no proxy friction, no dependency on
   a vendor that can retire/alter a model under us).
2. **Reproducibility for the paper** — frozen open weights are a permanent,
   citable artifact; "extraction re-runnable in 10 years on model X vSHA" is a
   stronger methodological claim than a pinned proprietary API.

**Decision bar (agreed):**
- **GATE = digit-exact transcription at full context.** If the model drops or
  alters digits in the source-table transcription, it fails — that is
  unfixable by us. Judgment differences in the declared ops are the retry
  loop's / assumption-register's business and are expected to be somewhat
  worse than Opus; count them SEPARATELY from transcription errors.
- **Bit-reproducible decoding is a BONUS, not a gate.** Our reproducibility
  claim rests on archived transcriptions + the deterministic executor (Stage
  B), which hold on any backend. So the vLLM determinism/batch-invariance
  question is a nice-to-have, not a blocker.
- **GO** = digit fidelity holds on a pinned FP8 config → adopt for the corpus
  sweep, keep Opus as the cross-check baseline.
- **NO-GO** = digit errors at any precision, or operational cost clearly
  exceeds Parley friction → stay on Parley/direct API; optionally revisit
  later as a post-publication robustness appendix (certifying against the
  archived truth matrix never expires).

This is a **quick beta**: if it looks worse than staying on Parley, we bail
without having sunk much time.

---

## 2. The pipeline this plugs into (essential background)

The extraction pipeline lives in `Data Extraction/pipeline/`. Two strictly
separated stages:
- **Stage A (the model):** receives the FULL layout-preserved document text
  (~34K-90K tokens for our six test docs), locates the source table(s) by
  content, transcribes them EXACTLY as printed, and DECLARES bin-mapping
  operations. The model does ZERO arithmetic.
- **Stage B (`ops.py`, deterministic Python):** executes the declared
  operations to produce the target grid, which is scored against the human
  workbook. Never touches a model.

All six target sheet classes are specced and executor-proven offline:
Age_Serv_Num, Age_Serv_Wage, Ret_Rate, Sep_Rate, Avg_Mort, Retirement. The
full test suite is 12/12 green. Current pipeline version tag: v0.8 (plus the
open-weights adapter, "beta groundwork" commit).

**Six test plans** (PDF + human-workbook truth where noted):
- phx (Phoenix, GRS), chi_pol (Chicago PABF, Cheiron→actually GRS/Segal mix),
  sd (San Diego, Cheiron), mil (Milwaukee, novel firm), aus (Austin, GRS,
  no workbook), bos (Boston, Segal).
- Scored plans for the fidelity battery: **mil, phx, chi_pol, sd** (have
  truth). aus/bos are production-mode (no/blank truth).

### The backend adapter (already built and committed)
`Data Extraction/pipeline/extract.py` is backend-agnostic. Setting two env
vars routes Stage A to any OpenAI-compatible server (vLLM) instead of the
Anthropic API — contract, client-side validator, retry loop, and Stage B are
IDENTICAL on both backends:

```bash
export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL=qwen35-122b-fp8      # must match --served-model-name
python pipeline/run_test.py --plan mil --target Age_Serv_Num   # scores itself
```

The local path automatically: (a) orders the prompt DOCUMENT-FIRST so the
~document-length prefix is byte-identical across the six targets → vLLM
automatic prefix caching (this is also our answer to "we resend the same doc
6×" — prefix caching makes calls 2-6 nearly prefill-free); (b) decodes greedily
(temperature 0); (c) disables Qwen thinking mode via
`chat_template_kwargs={"enable_thinking": false}`; (d) aborts loudly if the
response is truncated at the token limit. **Grammar/structured decoding is
deliberately OFF** — our retry loop depends on loud failures, and schema
enforcement can convert a loud malformed-JSON failure into a silent
wrong-content success.

Relevant env vars the adapter reads: `EXTRACT_OPENAI_BASE_URL`,
`EXTRACT_MODEL`, `EXTRACT_TIMEOUT_S` (default 3600), `OPENAI_API_KEY`
(any dummy value works for a local server).

---

## 3. Kill-test ladder (cheapest first) and results so far

1. **Tokenizer inflation — DONE, PASS (decisively).** Tokenized all six docs
   with the real `Qwen/Qwen3.5-122B-A10B` and `Qwen/Qwen3-Next-80B-A3B-Instruct`
   tokenizers. Worst doc (mil) = **90,179 Qwen tokens** (not the 200-260K the
   web-research reports predicted — layout whitespace compresses to multi-space
   tokens). Whole corpus fits any candidate's window; no two-pass locate stage
   needed. Per-doc counts: phx 34,428 / chi_pol 80,082 / sd 68,466 /
   aus 44,607 / mil 90,179 / bos 51,861.
2. **Queue reality** — NOT yet measured. `queue_probe.sbatch` exists for this.
   Kill if median H200 wait > ~4h. (In practice the two GPU-less CPU allocs we
   grabbed were near-instant; H200 waits unknown.)
3. **Boot + one real call** — IN PROGRESS. Server boot command is ready (see
   NEXT ACTION). Not yet run.
4. **Digit fidelity — THE gate.** `run_test.py` against the local endpoint on
   the four truth plans. Not yet run.
5. **Determinism probe** — optional bonus, not run.

---

## 4. Cluster facts (verified on Engaging, 2026-07-20/21)

- **Login:** the old `login001`/`vlogin001` nodes were DEPRECATED 2026-05-19.
  SSH to **`orcd-login.mit.edu`** with MIT Kerberos password + Duo. From a
  laptop: `ssh ncomati@orcd-login.mit.edu`. (OnDemand "Engaging Shell Access"
  may route to the deprecated node — prefer direct SSH.)
- **User/group:** `ncomati`, group `sched_mit_hill`.
- **`$SCRATCH` is NOT set as an env var.** The scratch path is hardcoded
  everywhere: **`/orcd/scratch/orcd/011/ncomati`** (265 TB free filesystem;
  per-user quota reported as ~1 TB and ~1.0M files — watch the file/inode
  count with sandbox containers).
- **Partitions** (from `sinfo`, `orcd-docs.mit.edu`):
  - `mit_normal_gpu`: max **2 GPUs / 32 cores / 6 h**. GPU types L40S(44GB),
    H100(80GB), H200(140GB). Request H200 explicitly: `-G h200:2` (default is
    L40S). 8× H200 per node.
  - `mit_preemptable`: 4 GPUs / 48 h, killable anytime (use `--requeue`).
  - `mit_normal`: CPU-only, 96 cores, 12 h (used for the container build).
- **Login node internet:** YES (HTTP 200 from huggingface.co). Downloads
  happen on the login node.
- **CPU throttling:** the login node throttles CPU — do NOT run heavy builds
  there; use a `salloc` on `mit_normal`.
- **Containers:** NO `singularity` module that loads by version, but there IS
  an **`apptainer/1.4.2`** module (apptainer = singularity successor,
  command-compatible). On compute nodes you MUST `module load apptainer/1.4.2`;
  the login node happened to have a system `singularity` on PATH but compute
  nodes do not.
- **Python:** login default is 3.6 (too old for modern HF tools). Use
  `module load miniforge/24.3.0-0` for a modern Python; `hf` CLI installed via
  `pip install --user "huggingface_hub"`.
- **CUDA modules** on the host are ancient (max 11.3) — IRRELEVANT, the vLLM
  container brings its own CUDA 12.x. H200 node drivers are recent enough.

---

## 5. EXACT STATE as of this handoff (what is DONE on the cluster)

Everything below is already on the cluster under
`/orcd/scratch/orcd/011/ncomati/`:

1. **Model weights: COMPLETE.**
   `models/qwen35-122b-fp8/` — 119 GB, all **39 safetensors shards** +
   `config.json` + 9.3 MB `model.safetensors.index.json`. This is
   `Qwen/Qwen3.5-122B-A10B-FP8` (official FP8, Apache 2.0, ~127 GB, MoE 122B
   total / 10B active, 262K native context window, hybrid attention with tiny
   KV growth).
2. **vLLM container: COMPLETE** (as a SANDBOX, not a .sif).
   `containers/vllm_dir/` — an apptainer sandbox directory built from
   `docker://vllm/vllm-openai:latest`. (We could NOT produce a `.sif` because
   the squashfs step kept getting OOM-killed; the sandbox skips squashfs. See
   error log below.)
3. **Repo: CLONED.**
   `state-and-local-pension/` — cloned from GitHub (repo was made PUBLIC to
   avoid the private-repo auth hassle; can be flipped back to private, the
   clone persists). Contains all pipeline code + this beta kit.
4. **Test data: STAGED.**
   `state-and-local-pension/Data/Plans/Cities/<plan>_modeldata/` each hold the
   AV PDF (+ workbook for mil/phx/chi/sd/bos; aus PDF only). Uploaded as a
   6.3 MB tarball via `scp` from the laptop, untarred in place. Verified the
   four scored plans have both PDF and workbook.
5. **Apptainer cache/temp** on scratch: `apptainer_cache/` (holds the ~8 GB
   image layers, so rebuilds skip the download) and `apptainer_tmp/`.

**NOT yet done:** booting the vLLM server on GPUs, and running any extraction.
The user stopped right before the GPU `salloc` step.

---

## 6. NEXT ACTION (verbatim — pick up exactly here)

You are on `orcd-login.mit.edu`, nothing running. Do this:

### Step A — grab 2× H200 (the current/previous CPU alloc, if any, is gone):
```bash
salloc -p mit_normal_gpu -G h200:2 -c 16 --mem=200G -t 6:00:00
```
Wait for `Nodes nodeXXXX are ready`; prompt changes to `[ncomati@nodeXXXX ...]$`.
(If the queue is slow, that's kill-test #2 data — note the wait.)

### Step B — boot the server in the background and watch it load:
```bash
module load apptainer/1.4.2
cd /orcd/scratch/orcd/011/ncomati
apptainer exec --nv -B /orcd/scratch/orcd/011/ncomati \
  containers/vllm_dir \
  vllm serve /orcd/scratch/orcd/011/ncomati/models/qwen35-122b-fp8 \
    --served-model-name qwen35-122b-fp8 \
    --tensor-parallel-size 2 \
    --max-model-len 131072 \
    --gpu-memory-utilization 0.90 \
    --port 8000 \
  > /orcd/scratch/orcd/011/ncomati/vllm.log 2>&1 &
tail -f /orcd/scratch/orcd/011/ncomati/vllm.log
```
Loading 127 GB across two GPUs takes a few minutes. Look for:
- **SUCCESS:** `Application startup complete` / `Uvicorn running on
  http://0.0.0.0:8000`. Ctrl+C the `tail` (server stays up in background).
- **FAILURE MODES to expect and their fixes:**
  - `unknown/unsupported architecture` or a Qwen3.5 model-registry miss →
    the image's vLLM is too old for Qwen3.5. Fix: rebuild the sandbox from a
    newer pinned tag, e.g. `docker://vllm/vllm-openai:vX.Y.Z` (check the vLLM
    release that added Qwen3.5 support), same `apptainer build --sandbox`
    procedure with `--mem=64G` on `mit_normal`.
  - CUDA OOM at load → lower `--max-model-len` (131072 is already modest; our
    biggest doc is 90K tokens so you can go as low as ~110000) or
    `--gpu-memory-utilization 0.95`.
  - tensor-parallel/NCCL errors → confirm both GPUs visible with
    `nvidia-smi` inside the alloc.

### Step C — run the first scored extraction (the actual test):
Because the vLLM server runs on the GPU node and binds `127.0.0.1:8000`, run
the pipeline **in the same shell / same node** (the server is backgrounded, so
the prompt is free). Set up the environment and run the hardest case first:
```bash
module load miniforge/24.3.0-0
pip install --user -q pdfplumber pypdf openpyxl    # deps; NO anthropic needed
export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL=qwen35-122b-fp8
export OPENAI_API_KEY=dummy
cd /orcd/scratch/orcd/011/ncomati/state-and-local-pension/"Data Extraction"
python pipeline/run_test.py --plan mil --target Age_Serv_Num
```
`mil Age_Serv_Num` is the hard case: 90K-token doc, three group tables summed.
It scores itself against the archived human workbook. **Adjudicate like any
live run:** a mismatch is NOT a model error until checked against the PDF.
Judge the GATE = did it transcribe the digits exactly? (ops/judgment
differences are secondary and expected.)

Then the rest of the battery:
```bash
python pipeline/run_test.py --plan phx --target Age_Serv_Num
python pipeline/run_test.py --plan phx --target Age_Serv_Wage
python pipeline/run_test.py --plan phx --target Retirement
python pipeline/run_test.py --plan chi_pol --target Age_Serv_Num
python pipeline/run_test.py --plan sd --target Age_Serv_Num
```
Artifacts land in `Data Extraction/runs/<plan>_<target>_<timestamp>/`
(extraction.json, derived.json, record.json, report.json) — same as the
Anthropic runs, fully auditable.

(There is also `engaging_beta/serve_and_run.sbatch` that does boot→health→
battery as one non-interactive job, but references singularity/`vllm.sif`;
update it to `module load apptainer/1.4.2` and `apptainer exec ...
containers/vllm_dir ...` before using it. For the first interactive test,
Steps A-C above are the path.)

---

## 7. ERROR LOG — everything that went wrong and the fix (so you don't repeat it)

1. **OnDemand shell → deprecated login node, password denied.** The OnDemand
   "Engaging Shell Access" dropped onto the retired `login001`, which rejects
   passwords. FIX: SSH directly to `orcd-login.mit.edu` from the laptop.
2. **`git clone` failed on a private repo** (headless gnome-ssh-askpass can't
   prompt). FIX chosen: made the repo PUBLIC, plain clone. (Alt: a GitHub PAT
   in the clone URL, then scrub it from `.git/config`.)
3. **`hf download` deadlocked** — "Still waiting to acquire lock ..." spam,
   elapsed times climbing, nothing transferring. Cause: 8 parallel workers
   fighting file locks on the InfiniBand parallel FS (`fstor018.ib`), slow
   POSIX locking. It ACTUALLY completed anyway on the Xet path despite the
   noise (119 GB landed). If it recurs: `--max-workers 1` and/or
   `export HF_HUB_DISABLE_XET=1` serializes it. NOTE: an HF token was NOT
   needed; the weights are already down. "16.4 MB total / SCRATCH 0.0 GB" in a
   QUOTA REPORT was a STALE cached report, not the real state — always verify
   with `du -sh` / `ls -lh` on the actual files.
4. **`module load singularity/3.7.0` → "unknown module".** That version string
   isn't registered. FIX: use `apptainer/1.4.2` instead (works on compute
   nodes; login node had a bare `singularity` on PATH but compute nodes don't).
5. **`scp` hung after Duo** on the first try (non-legacy). It worked on retry
   from PowerShell (the user's second attempt). If it hangs again, use
   `scp -O` (legacy protocol) and/or `scp -Ov` to see where it stalls.
   IMPORTANT: `scp` runs on the LAPTOP (where the files are), pointing at
   `ncomati@orcd-login.mit.edu:/orcd/scratch/orcd/011/ncomati/`. Everything
   else runs on the cluster. (User once pasted PowerShell output into the bash
   shell and vice-versa — keep straight which shell is which.)
6. **Container build kept "stalling," THEN kept dying — root cause was
   MEMORY, discovered late.** The chain of red herrings and the real fix:
   - First theory (WRONG): `/tmp` full. It wasn't — `/tmp` was 378 GB / 7%.
   - Real issues, compounded: (a) building on the throttled LOGIN node was
     slow; (b) the `salloc` requested cores but **no `--mem`**, so it got the
     small default and the extraction/squashfs got **OOM-KILLED**; (c) the
     squashfs (.sif creation) is extremely slow on this FS (~75 min ETA) and
     memory-hungry.
   - A `ps` check showed "no process" — MISLEADING: it was run on `login007`
     while the build ran on the compute node `nodeXXXX`; processes are
     per-node, so login can't see them. Always check on the SAME node.
   - **THE FIX:** allocate real memory and time, and build a **sandbox**
     (skips squashfs entirely):
     ```
     salloc -p mit_normal -c 8 --mem=64G -t 3:00:00
     module load apptainer/1.4.2
     export APPTAINER_CACHEDIR=/orcd/scratch/orcd/011/ncomati/apptainer_cache
     export APPTAINER_TMPDIR=/orcd/scratch/orcd/011/ncomati/apptainer_tmp
     cd /orcd/scratch/orcd/011/ncomati/containers
     apptainer build --sandbox vllm_dir docker://vllm/vllm-openai:latest \
       2>&1 | tee /orcd/scratch/orcd/011/ncomati/build.log \
       | grep -viE 'Unrecognised xattr|EPERM|ignoring'
     ```
     Completed in minutes: "Build complete: vllm_dir". The
     `Unrecognised xattr prefix system.nfs4_acl` and
     `harmless EPERM on setxattr security.capability` lines are HARMLESS
     (the FS can't store those xattrs; the container is fine).
   - LESSON: on Engaging, ALWAYS pass `--mem=` on `salloc`; default memory is
     tiny and silently OOM-kills. Prefer sandbox over .sif on this filesystem.

---

## 8. Candidate models (for reference / fallback)

- **PRIMARY (downloaded): `Qwen/Qwen3.5-122B-A10B-FP8`** — MoE 122B/10B active,
  262K native ctx, hybrid attention (tiny KV growth), Apache 2.0. Official FP8,
  ~127 GB, fits 2× H200 (280 GB) with headroom. This is what's staged.
- **Single-GPU screeners (if 122B is overkill or you want a cheap A/B):**
  `Qwen/Qwen3-Next-80B-A3B-Instruct` (RULER ~96/94/93.5 at 128K/192K/256K —
  strongest published long-ctx evidence; non-thinking by design; on vLLM's
  batch-invariance-tested list) and a smaller Qwen3.5 dense (~27-35B). Both
  Apache 2.0. Swapping is just re-downloading weights + changing
  `--served-model-name`/`EXTRACT_MODEL`.
- Quantization rule: **FP8 weights + default (BF16) KV first.** NEVER INT4 at
  our context length (research shows large long-context degradation). Try
  `--kv-cache-dtype fp8` only as a separately-scored config if VRAM demands.
- Paper pin-list (record when we certify a GO): model repo commit SHA +
  weight-shard hashes, vLLM container digest/tag, TP size, `--kv-cache-dtype`,
  `--max-model-len`, sampling params, and the chat template from
  `tokenizer_config.json`.

---

## 9. Cross-machine continuation checklist

To continue from another machine you need:
1. **This repo** (it's public; `git clone` or `git pull`). All pipeline code +
   this handoff + runbook are in it. The open-weights adapter is committed.
2. **SSH access to Engaging:** `ssh ncomati@orcd-login.mit.edu` (MIT Kerberos +
   Duo). All the heavy state (weights, container, data) already lives on the
   cluster scratch — nothing to re-upload.
3. Nothing else. The laptop only needs a terminal; all compute is on Engaging.

The moment you're on `orcd-login.mit.edu`, go to Section 6 Step A and continue.
