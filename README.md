# State and Local Pension â€” Project Root

Reorganized 2026-06-11 into a single clean tree (see `Documentation/reorg_plan.md` for the executed manifest, `Documentation/project_context.md` Â§2 for the directory map).

| Folder | Contents |
|---|---|
| `Code/python/` | THE production simulation engine (fast runner, asset simulation with common shocks, scenario layer, `launcher.ipynb`, `analysis/results.ipynb`) |
| `Code/R/` | Verified R reference implementation (2022 scripts + Common_Code) |
| `Data/Plans/States/` | 40 state plan folders (workbooks + AV/CAFR PDFs), fully intact |
| `Data/Plans/Cities/` | Canonical municipal collection (FY2019, ~16 cities) + `_migration/` bridge |
| `Data/Common/` | Common data, split symmetric: `states/` (active model inputs; ppd-data-latest covers both tracks) + `municipal/` |
| `Data/Returns/` | Asset-class return series + correlation matrices |
| `Data/Sources/` | Brookings replication package, Airtable export, collection templates |
| `Results/Runs/062026/` | Canonical run outputs + scenario folders |
| `Documentation/` | project_context.md, working_context.md, audits, guidebook, lit review, media |
| `Drafts/` | Paper drafts |
| `Backup/` | Pre-reorg backup (file manifest + code/docs zip) |
| `_ARCHIVE/` | Everything superseded (state R legacy, 2022 city system, snapshots). Do not work from here. |

**For AI/code sessions:** open the session at THIS folder and read, in order: `Documentation/project_context.md` (full), `Documentation/session_handoff.md` (full — tacit knowledge, norms, quirks), and `Documentation/working_context.md` (at least the 2026-06-10/11 sections including the "*** PARKED ***" scenario plan). For the city track also read `Documentation/city_data_audit.md` and `Documentation/data_sources_map.md`. Always update contextss when working. The current tree is self-contained: everything needed for work lives in the folders above. `_ARCHIVE/` and `Backup/` exist only for provenance and disaster recovery — they never need to be read.

Known post-reorg caveats:
- `Code/python/engaging/` Slurm scripts still assume the old tree; rework before the next Engaging run.
- The empty `State Pension Model/` shell can be moved to `_ARCHIVE/` once no session is rooted in it.
