# Engaging open-weights beta — full session handoff

**Written 2026-07-22.** This file captures EVERYTHING needed to continue the
open-weights migration beta on MIT Engaging from another machine: the goal,
the decision bar, the exact cluster state, every command that worked, every
error hit and its fix, and the precise next action. Read it together with
`runbook.md` (the concise procedure) in this same folder. If you only read one
thing, read the "EXACT STATE" and "NEXT ACTION" sections.

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
