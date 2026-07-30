"""Confirm the beta engine differs from production ONLY in the intended way.

Run this before trusting any beta result. If production changes and the beta is not
updated, this fails and tells you exactly where they diverged.
"""
import difflib, pathlib, sys, re

HERE = pathlib.Path(__file__).resolve().parent
PROD = HERE.parent / "fast" / "Main_PensionModel.py"
BETA = HERE / "Main_PensionModel_payrollbeta.py"

# Every differing line must relate to the contribution-rate denominator. Anything
# else means production moved and the beta did not follow.
EXPECTED = [
    "ContributionRate",        # the two rates being set differently
    "payroll",                 # the denominator itself
    "_model_payroll", "_ee_dollars", "_er_dollars",
    "BETA",
    "CONTRIB_RATE_NA_CHECK",   # the special case the change makes redundant
]

def body(path):
    """Source with the module docstring stripped, so headers do not count as drift."""
    t = path.read_text(encoding="utf-8")
    i = t.index("import argparse")
    return t[i:].splitlines()

p, b = body(PROD), body(BETA)
diff = [l for l in difflib.unified_diff(p, b, "production", "beta", n=0)
        if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]

print(f"production : {PROD.relative_to(HERE.parent.parent.parent)}  ({len(p)} lines)")
print(f"beta       : {BETA.relative_to(HERE.parent.parent.parent)}  ({len(b)} lines)")
print(f"differing lines: {len(diff)}\n")
for l in diff:
    print("   " + l[:150])

def is_decoration(line):
    """Pure comment or separator lines carry no logic."""
    t = line[1:].strip()
    return t == "" or t.startswith("#")

unexpected = [l for l in diff
              if not any(k.lower() in l.lower() for k in EXPECTED)
              and not is_decoration(l)]
print()
if unexpected:
    print(f"UNEXPECTED DIFFERENCES: {len(unexpected)} line(s) that are not part of the")
    print("intended change. The beta has drifted from production - reconcile before use.")
    for l in unexpected:
        print("   " + l[:150])
    sys.exit(1)
print("OK - the only differences are the intended contribution-rate change.")
