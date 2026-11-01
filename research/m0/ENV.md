# M0.1 environment status

M0.1 has not produced empirical artifacts yet. This file is the audit trail of every
execution environment that was tried, oldest first. The last section is authoritative
for the environment currently in use.

On a successful run `prepare_m0.py` writes one generated block, delimited by the
`m0_1_runtime` HTML comment markers. Everything outside those markers is hand-written history
and is never overwritten; a marker that is not alone on its own line is treated as prose, not as
the start of the block.

## 2026-10-30 — first attempt, blocked before dependency install

**Status: blocked before Folktables installation and before PUMS download.**

### Environment observed

- Python interpreter: `3.13.5`
- uv: `0.10.0`
- Host environment NumPy: `2.3.5`
- Host environment SciPy: `1.17.0`
- Host environment pandas: `2.2.3`
- Host environment scikit-learn: `1.8.0`
- PyArrow: not installed
- Folktables: not installed

A project virtual environment was created by `uv sync --python 3.13`, but dependency resolution failed before packages could be installed:

```text
Failed to fetch: https://pypi.org/simple/folktables/
DNS error: failed to lookup address information: Temporary failure in name resolution
```

This is a network/DNS failure in that execution environment. It does **not** establish that Folktables is incompatible with Python 3.13. In accordance with M0.1, execution stopped there. No Python 3.12 fallback, alternate dataset, manual PUMS downloader, or substitute implementation was used.

### Completed before the stop

- Python 3.13 interpreter and uv versions recorded.
- Household split contract aligned to the roadmap: SHA-256 of `salt + SERIALNO`, 2017 split 50/10/20/20, 2016 split 85/15.
- Split/firewall unit tests: 10 passed.
- Python syntax compilation: passed.

### Not completed

- Folktables installation and version confirmation.
- PUMS 2016/2017 download.
- `adult_filter` source capture and ACSIncome task verification.
- Real row counts, class balance, missingness, cardinalities, OCCP/POBP code-set comparison, and household-size distribution.
- `splits.parquet`, Parquet checksum, and train/validation ACSIncome Parquet files.
- No model training, hyperparameter selection, predictions, discovery metrics, or confirmation metrics.

## 2026-10-31 — re-check in a different container (PyPI open, data still closed)

**Status: still blocked before data access, but the blocker moved.** The dependency
blocker from 2026-10-30 does not reproduce here; the data blocker does. This section
records what was observed, so the older "cannot resolve pypi.org" note is not read as a
current fact.

### Network reachability

| Host | Result | Consequence |
| --- | --- | --- |
| `pypi.org`, `files.pythonhosted.org` | reachable | packages can be resolved here |
| `www2.census.gov`, `api.census.gov` | `SSL_ERROR_SYSCALL` on connect | no PUMS download possible here |
| `release-assets.githubusercontent.com` | blocked (redirect target of GitHub release downloads) | no Python 3.13 standalone build |

- `folktables 0.0.12` is published on PyPI (`requires-python >=3.7`, pure-Python wheel) and **installs and imports** in this container. The 2026-10-30 DNS failure was environmental, not a Folktables/Python 3.13 incompatibility.
- Folktables fetches PUMS from `https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/csv_pca.zip` (`folktables/load_acs.py`), and the PUMS data dictionary from the same host. Neither host is reachable here, so no real rows exist in this container.
- No Python 3.13 interpreter could be provisioned: `uv python install 3.13` fails because the GitHub release asset redirects to a blocked host. The container's only interpreter is Python 3.11.2, which the project does not support.

### Verified here (no empirical claim)

- Python 3.11.2 with NumPy 2.4.6, pandas 3.1.0, SciPy 1.17.1, scikit-learn 1.9.1, PyArrow 26.0.0, Folktables 0.0.12.
- `research/m0/test_split_logic.py` passed in this synthetic plumbing run, including on pandas 3.x. This Python 3.11.2 run is not the project's supported Python 3.13 validation and is not an M0.1 data result.
- Offline acquisition path (`prepare_m0.py --raw-dir`) exercised end-to-end against real Folktables 0.0.12 using **synthetic** CSVs in a throwaway copy of the module outside this repository. It staged the files, loaded them through `ACSIncome.df_to_pandas`, and wrote the manifest, checksum, and report. No synthetic artifact was written into this repository, and none of it is an M0.1 result.

### Contract detail confirmed by that dry run

Folktables names the local CSV differently per survey year, and offline staging must match exactly:

- 2017: `psam_p06.csv` (numeric state code, not `psam_pca.csv`)
- 2016: `ss16pca.csv` (state abbreviation)

Both years download as `csv_pca.zip`, so local files must live in per-year subdirectories.

### Still not done, and why

- No PUMS data, therefore no `splits.parquet`, checksum, real row counts, positive rate, missingness, OCCP/POBP comparison, or household-size distribution.
- No `adult_filter`/ACSIncome verification against real rows.
- No model training, predictions, discovery, confirmation, or ManimGX render.

### To run M0.1 on a machine with Census access and Python 3.13

Online, as before:

```powershell
uv sync --python 3.13
uv run python research/m0/test_split_logic.py
uv run python research/m0/prepare_m0.py
```

Or fully offline with files downloaded by hand from
`https://www2.census.gov/programs-surveys/acs/data/pums/{2016,2017}/1-Year/csv_pca.zip`:

```powershell
uv run python research/m0/prepare_m0.py --raw-dir C:\pums
```

`C:\pums\2016\csv_pca.zip` and `C:\pums\2017\csv_pca.zip` (or the extracted `ss16pca.csv` /
`psam_p06.csv`). Offline mode records the SHA-256 of each source file in `split_manifest.json`,
`ENV.md`, and `01_data_report.md`; it does not verify them against an upstream checksum, so the
operator must confirm the download.

## Generated runtime record

<!-- BEGIN GENERATED: m0_1_runtime -->
- Run date (UTC): 2026-11-01T17:05:50+00:00
- Python: 3.13.18
- numpy: 2.5.4
- scipy: 1.18.1
- pandas: 3.1.0
- pyarrow: 26.0.0
- scikit-learn: 1.9.1
- folktables: 0.0.12
- Raw data acquisition: local_files (offline)
- 2016 source: `/Users/qobiljonerkinjonov/Desktop/SliceAudit/2016/csv_pca.zip` sha256 `a434bf9316f174d896766488cd5fd4ae7356a9512258321110b62110c6ded818`
- 2017 source: `/Users/qobiljonerkinjonov/Desktop/SliceAudit/2017/csv_pca.zip` sha256 `d28c43dabd5fdc0abcba3d0941101bf6eceda4a84c1bdd269982adb8b89d6617`

Review the installed Folktables version and task filter before accepting this report.
<!-- END GENERATED: m0_1_runtime -->
