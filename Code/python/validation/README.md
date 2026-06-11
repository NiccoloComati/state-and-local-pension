# Validation Scripts

Stable comparison tools. Run from the project root (`State Pension Model/`).

---

## compare_r_python.py

Compares R deterministic/asset outputs against Python outputs.

```powershell
# Deterministic A/L comparison (R 062026 vs Python 062026_py)
python "Cluster Code\cluster_062026\Python Code\validation\compare_r_python.py" `
  --plans all --kind detal `
  --r-run-tag 062026 --py-run-tag 062026_py `
  --output "Results\Runs\062026_py\_compare_detal_vs_r.csv"

# Asset comparison
python "Cluster Code\cluster_062026\Python Code\validation\compare_r_python.py" `
  --plans all --kind asset `
  --r-run-tag 062026 --py-run-tag 062026_py `
  --output "Results\Runs\062026_py\_compare_assets_vs_r.csv"
```

**Expected clean result:** only `run_tag` (37 rows, different tag strings by design) and
`Percent_difference` (recomputed on the fly from Model_AAL/CAFR_AAL — always consistent).
All simulation matrices `ok` at max_rel ~1e-15.

**Key flags:**
- `--tolerance` (default 1e-4) / `--relative-tolerance` (default 1e-10)
- `--kind`: `detal` or `asset`

---

## compare_fast_vs_orig.py

Compares fast Python outputs against original Python outputs to verify that
optimizations produce bit-identical results.

```powershell
python "Cluster Code\cluster_062026\Python Code\validation\compare_fast_vs_orig.py" `
  --orig 062026_py --fast 062026_fast
```

**Expected clean result:** all `AAL`, `NormalCost`, `cash_outflows`, `cash_inflows`
show `max_abs = 0.0` for all 37 plans.
