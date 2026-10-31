# M0.1 environment status

**Status: blocked before Folktables installation and before PUMS download.**

## Environment observed on 2026-10-30

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

This is a network/DNS failure in the execution environment. It does **not** establish that Folktables is incompatible with Python 3.13. In accordance with M0.1, execution stops here. No Python 3.12 fallback, alternate dataset, manual PUMS downloader, or substitute implementation has been used.

## Completed before the stop

- Python 3.13 interpreter and uv versions recorded.
- Household split contract aligned to the roadmap: SHA-256 of `salt + SERIALNO`, 2017 split 50/10/20/20, 2016 split 85/15.
- Split/firewall unit tests: 10 passed.
- Python syntax compilation: passed.

## Not completed

- Folktables installation and version confirmation.
- PUMS 2016/2017 download.
- `adult_filter` source capture and ACSIncome task verification.
- Real row counts, class balance, missingness, cardinalities, OCCP/POBP code-set comparison, and household-size distribution.
- `splits.parquet`, Parquet checksum, and train/validation ACSIncome Parquet files.
- No model training, hyperparameter selection, predictions, discovery metrics, or confirmation metrics.

## Retry on a network-enabled machine

```powershell
uv sync --python 3.13
uv run python research/m0/test_split_logic.py
uv run python research/m0/prepare_m0.py
```

Do not proceed to M0.2 until the actual Folktables/PUMS artifacts and report have been reviewed.
