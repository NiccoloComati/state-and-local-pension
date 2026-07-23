# Engaging open-weights beta — full session handoff

**Written 2026-07-22.** This file captures EVERYTHING needed to continue the
open-weights migration beta on MIT Engaging from another machine: the goal,
the decision bar, the exact cluster state, every command that worked, every
error hit and its fix, and the precise next action. Read it together with
`runbook.md` (the concise procedure) in this same folder. If you only read one
thing, read the "EXACT STATE" and "NEXT ACTION" sections.

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
