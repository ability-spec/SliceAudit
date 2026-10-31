# M0.1 data report

**Status: BLOCKED BEFORE DATA ACCESS.** This is an execution record, not an empirical data report.

## What was completed

- Confirmed the required interpreter is Python `3.13.5` and uv is `0.10.0`.
- Aligned household split implementation and preregistration with the original roadmap:
  - SHA-256 input is the direct concatenation `salt + SERIALNO` (no delimiter).
  - 2017 household buckets: train 50%, validation 10%, discovery 20%, confirmation 20%.
  - 2016 household buckets: train 85%, validation 15%.
- Ran the dependency-light split and firewall tests: **10 passed**.
- Python syntax compilation passed.

## Environment blocker

> **2026-10-31 addendum:** this execution record is unchanged, but the PyPI/DNS failure below did
> not reproduce in a later container. The blocker that did reproduce is Census access, plus the
> absence of a Python 3.13 interpreter. See [`ENV.md`](ENV.md) for the dated history. A real run
> overwrites this file with the actual report.

The required command `uv sync --python 3.13` created a project virtual environment but could not resolve the Folktables package index:

```text
Failed to fetch: https://pypi.org/simple/folktables/
DNS error: failed to lookup address information: Temporary failure in name resolution
```

The host Python environment has NumPy `2.3.5`, SciPy `1.17.0`, pandas `2.2.3`, and scikit-learn `1.8.0`; PyArrow and Folktables are not installed. This is a DNS/network blocker, not evidence of Python 3.13 incompatibility.

The roadmap explicitly requires stopping if Folktables cannot be installed or used on Python 3.13. No fallback to Python 3.12, OpenML, an alternate downloader, or a hand-written task implementation was attempted.

## Not run

- No PUMS downloads for CA 2016 or 2017.
- No call to `ACSIncome.df_to_pandas` or the installed Folktables `adult_filter`.
- No real row counts, positive-class rates, missingness/cardinality summaries, OCCP/POBP code-set comparisons, or household-size distributions.
- No `splits.parquet`, checksum, or ACSIncome task Parquet data.
- No model training, predictions, discovery metrics, or confirmation metrics.

## Next action

Repeat the documented setup on a network-enabled Python 3.13 machine. Once Folktables and PyArrow install, run `research/m0/prepare_m0.py`, review every generated artifact, and stop for owner review as required by M0.1.
