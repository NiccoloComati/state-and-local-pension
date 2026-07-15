# Engaging beta runbook — open-weights Stage A

**Goal:** decide in ~1 week whether a pinned open-weights model can replace
`claude-opus-4-8` for Stage A. **Gate: digit-exact transcription at full
context.** Bit-reproducible decoding is a bonus, NOT a gate — our
reproducibility claim rests on archived transcriptions + the deterministic
executor, which hold on any backend.

The pipeline is already backend-agnostic: set two env vars and every part of
it (contract, validator, retry loop, scoring) runs unchanged against a local
server:

```bash
export EXTRACT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export EXTRACT_MODEL=qwen35-122b-fp8          # the name vllm serves
python pipeline/run_test.py --plan mil --target Age_Serv_Num   # scored!
```

The local backend automatically: puts the document FIRST in the prompt
(byte-identical prefix across the 6 targets -> vLLM prefix cache hits),
decodes greedily (temperature 0), disables Qwen thinking mode
(`chat_template_kwargs`), and aborts loudly on output truncation.
Structured/grammar decoding stays OFF: our retry loop depends on loud
failures, and grammar enforcement can convert them into silent wrong-content
successes.

## Kill-test ladder (cheapest first; each can end the project)

### 1. Tokenizer inflation — DONE 2026-07-15, PASS (decisively)
Measured with the actual `Qwen/Qwen3.5-122B-A10B` and
`Qwen/Qwen3-Next-80B-A3B-Instruct` tokenizers on our layout-preserved text:

| plan | chars | chars/4 (est.) | Qwen3.5 tokens | Qwen3-Next tokens |
|---|---|---|---|---|
| phx | 284,014 | 71,003 | 34,428 | 34,444 |
| chi_pol | 543,466 | 135,866 | 80,082 | 79,937 |
| sd | 423,168 | 105,792 | 68,466 | 68,570 |
| aus | 356,243 | 89,060 | 44,607 | 44,668 |
| mil | 642,512 | 160,628 | **90,179** | 90,170 |
| bos | 413,311 | 103,327 | 51,861 | 51,892 |

The predicted per-digit blowup did NOT materialize: layout whitespace
dominates our documents and Qwen compresses it into multi-space tokens. The
worst document is 90K tokens — inside even the conservatively-characterized
~128K zone, with full room for prompt + 30K output inside the 262K window.
No two-pass locate stage needed. (Per-digit tokenization is retained for the
numbers themselves — good for transcription fidelity.)

### 2. Queue reality (~5 min effort, one week calendar)
Submit `queue_probe.sbatch` a few times a day; log pending times with
`sacct -j <id> --format=Submit,Start`. **Kill if median wait > ~4h.**

### 3. Boot + one real call (one salloc session)
Bring up vLLM per below; run one scored extraction. **Kill if** OOM at
262K max-model-len on 2x H200, or one call takes > ~10 min.

### 4. Digit fidelity — THE gate (one session, ~6 scored runs)
`run_test.py` against the local endpoint on plans with archived truth:
`mil Age_Serv_Num` (161K-token doc, three tables — the hard case), then
`phx Age_Serv_Num`, `phx Age_Serv_Wage`, `phx Retirement`, `chi_pol
Age_Serv_Num`, `sd Age_Serv_Num`. Adjudicate like any live run (mismatch !=
error until checked against the PDF). **Kill if the model drops/alters
digits** — that is unfixable by us. Judgment differences in ops declarations
are the retry loop's and register's business, and expected to be worse than
Opus; count them separately from transcription errors.
Optional A/B at zero extra setup: point EXTRACT_MODEL at the single-GPU
screener (Qwen3-Next-80B or Qwen3.5-35B) first; if IT passes, the 122B
almost surely does and everything gets cheaper.

### 5. Determinism probe (optional — bonus, not gate, ~20 calls)
Same request 10x with prefix caching on; 10x with
`VLLM_BATCH_INVARIANT=1` + `--no-enable-prefix-caching`. Byte-compare.
Whatever the outcome, the paper's pin list is: model repo commit SHA +
weight-shard hashes, vLLM container digest, TP size, kv-cache dtype,
max-model-len, sampling params, chat template.

## Engaging facts (verified against orcd-docs.mit.edu 2026-07-15)
- Account: any MIT Kerberos user via the OnDemand portal, no PI approval.
- `mit_normal_gpu`: max 2 GPUs / 32 cores / **6 h**; L40S, H100, H200
  (H200 140GB — request explicitly: `-G h200:2`, default is L40S).
- `mit_preemptable`: 4 GPUs / 48 h, killable anytime; use `--requeue`.
  Our harness is naturally preemption-safe (one artifact dir per run).
- Apptainer supported (`module load apptainer`); pull the official
  `vllm/vllm-openai` image at a PINNED tag from a login node.
- Storage: Home 200GB (backed up), Pool 1TB, Scratch 1TB flash (purged after
  6 months idle). Weights (~127GB FP8) -> Scratch; archive copy -> Pool.
- Download weights from a LOGIN node; record the HF revision SHA.

## Bring-up (interactive first)
```bash
# login node:
module load apptainer
apptainer pull vllm.sif docker://vllm/vllm-openai:<PINNED_TAG>
hf download Qwen/Qwen3.5-122B-A10B-FP8 --local-dir $SCRATCH/models/qwen35-122b-fp8
# record: hf revision SHA + sha256 of shards

salloc -p mit_normal_gpu -G h200:2 -c 30 --mem=400G -t 6:00:00
apptainer exec --nv -B $SCRATCH vllm.sif \
  vllm serve $SCRATCH/models/qwen35-122b-fp8 \
    --served-model-name qwen35-122b-fp8 \
    --tensor-parallel-size 2 \
    --max-model-len 262144 \
    --language-model-only \
    --gpu-memory-utilization 0.92 \
    --enable-prefix-caching \
    --max-num-seqs 2 \
    --seed 0 --port 8000
```
Notes: FP8 weights + default (BF16) KV first; try `--kv-cache-dtype fp8`
only as a separately scored config. Never INT4 anything at this context
length. Batch runs: `serve_and_run.sbatch`.

## Repo + data on Engaging
```bash
git clone https://github.com/NiccoloComati/state-and-local-pension.git
pip install --user pdfplumber pypdf openpyxl        # no anthropic needed
# copy the six AV PDFs + truth workbooks (not in git) into
#   Data/Plans/Cities/<plan>_modeldata/  (same layout as on Windows)
```

## Decision bar
- **GO** = kill tests 1-4 pass on any pinned FP8 config: adopt for the
  corpus sweep; Opus stays the cross-check baseline.
- **NO-GO** = digit errors at any precision, or operational cost clearly
  exceeds Parley friction: stay on Parley/direct API; optionally revisit as
  a post-publication robustness appendix (certifying against archived truth
  never expires).
