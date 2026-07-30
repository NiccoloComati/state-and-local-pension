# `beta/` — experimental engine variants

**Nothing here is production.** Production is `Code/python/fast/Main_PensionModel.py`.
These exist to answer one open question each, by running them against production and
comparing. When a question is settled, the change is folded into production and the
beta file is deleted — two live engines is exactly the confusion this folder is
meant to avoid.

## `Main_PensionModel_payrollbeta.py`

Tests one thing: **which payroll the contribution rate should be measured against.**

Production divides contributions by the PPD's *covered payroll*, then charges that
rate against the payroll the engine builds for itself. Those two differ for 12 of
the 40 plans, by 0.84x to 1.60x, in both directions, and nobody has been able to
attribute why from the PPD alone. The beta divides by the engine's own payroll
instead, which makes first-year contributions equal what the plan reported
receiving.

Everything else is identical. `check_beta_drift.py` proves it and fails loudly if
production moves and the beta doesn't.

```powershell
python beta/check_beta_drift.py                 # verify before trusting anything
python run_simulation.py --plans all --stage both --beta-payroll --num-sim 10000 --run-tag YYYYMMDD_N --parallel 20 --workers 1 --seed 123
```

Compare the two runs with `Analysis/` — the metrics that discriminate are in the
session notes, and deliberately do not include closeness to reported actuarial
liability.
