# M0.1 environment status

## Execution environment in this session

- Python: 3.13.5
- uv: 0.10.0
- numpy: 2.3.5
- scipy: 1.17.0
- pandas: 2.2.3
- scikit-learn: 1.8.0
- pyarrow: not installed
- folktables: not installed
- manimgx: not installed

A Python 3.13 virtual environment was created successfully. Dependency-light hash/split tests passed: 8/8. Package resolution stopped because this execution environment could not resolve pypi.org. Therefore, data download and Parquet generation were not run. No empirical findings are claimed.

## Reproduce on a network-enabled machine

```powershell
uv sync --python 3.13
uv run python research/m0/test_split_logic.py
uv run python research/m0/prepare_m0.py
```

The script records the installed Folktables version and task-filter implementation in its runtime environment record. Verify that generated record before accepting the data report.
