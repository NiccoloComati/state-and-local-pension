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
| `Documentation/` | project_context.md, working_context.md, session_handoff.md, city/provenance narrative docs, guidebook copy, variable glossary, media (incl. recorded code-walkthrough call); `provenance/` subfolder holds the generator scripts + their audit CSVs |
| `Papers/` | Reference literature (Brookings papers, Dan_Papers) — moved out of Documentation 2026-07-07 |
| `Drafts/` | Paper drafts |
| `Backup/` | Pre-reorg backup (file manifest + code/docs zip) |
| `_ARCHIVE/` | Everything superseded, reshaped 2026-06-11 to mirror the PRE-reorg layout for legibility: the whole old `State Pension Model/` tree intact, the 2022 `city_2022_system/`, plus `BrookingsData/`, `Pension_Data/`, `PDFs/`, `Data_Daily/` under their original names, the `reorg_check_scratch/` validation snapshot, and snapshot zips. Do not work from here. |

**For AI/code sessions:** open the session at THIS folder and read, in order: `Documentation/project_context.md` (full), `Documentation/session_handoff.md` (full — tacit knowledge, norms, quirks), and `Documentation/working_context.md` (the most recent sections). **For the ACTIVE extraction-pipeline workstream also read `Data Extraction/data_extraction_context.md` (full)** — the living methodology + dev log of every attempt and fix. `Documentation/variable_glossary.md` defines every model input and simulation variable (Part I inputs / Part II code; names are shared R↔Python) — consult it whenever touching the engine. For the city track also read `Documentation/city_data_audit.md`, `Documentation/data_sources_map.md`, `Documentation/model_input_dictionary.md` (what every model input is + where it comes from), and `Documentation/city_extraction_catalogue.md` (per-plan extraction status + sources + collector logs — the working doc for finishing city extraction by hand). Always update contexts when working.

**Cross-machine note:** git (GitHub `origin`) tracks CODE + DOCUMENTATION only. The DATA (state workbooks, AV/CAFR PDFs, `ppd-data-latest.xlsx`, Results outputs, most city data) is gitignored and lives in OneDrive — a fresh `git clone` will NOT have it. Continue from the OneDrive-synced copy (has everything), or sync `Data/` + `Results/` separately. Claude memory (`.claude/`) is machine-local and does not transfer; all durable knowledge is in `Documentation/`. The current tree is self-contained: everything needed for work lives in the folders above. `_ARCHIVE/` and `Backup/` exist only for provenance and disaster recovery — they never need to be read.

Known post-reorg caveats:
- `Code/python/engaging/` Slurm scripts still assume the old tree; rework before the next Engaging run.
- A leftover `Github/pensions-basecode` husk remains at the root; safe to delete once OneDrive releases its lock.
