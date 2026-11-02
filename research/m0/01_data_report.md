# M0.1 data report

> **Status: M0.1 completed; model validation has not started.** Train/validation summaries only. Discovery and confirmation task rows were not filtered or summarized.

## Executive summary

- The real California ACS PUMS 2016 and 2017 data-and-split audit completed using operator-supplied local archives.
- Safe ACSIncome artifacts contain **190,187** eligible train/validation people for 2016 and **116,092** for 2017.
- Runtime checks confirmed household isolation, California-only input, the target rule, and exclusion of discovery/confirmation rows from task filtering and artifacts.
- **Open provenance limitation:** local source hashes identify the exact bytes used, but offline mode did not verify them against an upstream Census checksum.
- This report validates data preparation only. It contains no model comparison and provides no empirical evidence yet for SliceAudit's hidden-regression claim.

## Run and reproducibility

| Field | Value |
| --- | --- |
| Run date (UTC) | `2026-11-01T17:05:50+00:00` |
| Source revision | `418617a46dbe9925431791241e6044a7479e5197` |
| Execution command | `uv run python research/m0/prepare_m0.py --raw-dir <PUMS_ROOT>` |
| Python | `3.13.18` |
| Key packages | Folktables `0.0.12`, pandas `3.1.0`, PyArrow `26.0.0`, NumPy `2.5.4` |

The complete runtime record and earlier blocked attempts are in [`ENV.md`](ENV.md). Raw data, split assignments, and processed Parquet files are intentionally not committed. Independent verification therefore requires the source files and a rerun; recorded hashes support identity checks but do not by themselves authenticate the upstream release.

## Raw data provenance

- Acquisition mode: `local_files`
- 2016: `operator-supplied/2016/csv_pca.zip` (75,148,888 bytes; SHA-256 `a434bf9316f174d896766488cd5fd4ae7356a9512258321110b62110c6ded818`), staged as `data/2016/1-Year/ss16pca.csv`
- 2017: `operator-supplied/2017/csv_pca.zip` (74,948,023 bytes; SHA-256 `d28c43dabd5fdc0abcba3d0941101bf6eceda4a84c1bdd269982adb8b89d6617`), staged as `data/2017/1-Year/psam_p06.csv`

Offline staging validates the expected file layout, required columns, and California state code. It does not verify an upstream Census checksum or independently prove the survey year of a hand-supplied archive; the operator remains responsible for source authenticity.

## Audit checks

| Check | Result | Basis |
| --- | --- | --- |
| Households assigned before task filtering | Pass | Split manifest is built from raw household IDs before `adult_filter`. |
| Household cross-split assignments | **0** | `assert_no_household_leakage` rejects duplicate or conflicting assignments. |
| Raw rows restricted to California | Pass | Every raw row must have `ST = 06`. |
| ACSIncome target rule | Pass | Labels must equal `PINCP > 50000` on safe rows. |
| Held-out task firewall | Pass | Only train/validation households enter task filtering and Parquet artifacts. |
| Row-order invariance | Covered by unit test | `test_split_logic.py` compares shuffled and original assignments. |
| Upstream Census source authentication | **Not verified** | No upstream checksum comparison was performed in offline mode. |
| Artifact SHA-256 values | Recorded | Values below identify the generated artifacts; they are not an independent rerun. |

## Saved ACSIncome task artifacts

Files contain only task-eligible train/validation people and preserve `SERIALNO`, `SPORDER`, `PWGTP`, `ST`, `ADJINC`, and split assignment.

- 2016: `data/processed/acs_income_train_validation_2016.parquet` (190,187 rows; SHA-256 `e8469c68f878a33562243a812e0636411e2cdf8f06047a572d76fc2110718420`)
- 2017: `data/processed/acs_income_train_validation_2017.parquet` (116,092 rows; SHA-256 `32ca96ac7e939f12d7f0f57fc3552ab7ae2660360555333b653baf17c0b73810`)

## Safe-partition summary

| Metric | 2016 | 2017 |
| --- | ---: | ---: |
| Raw train/validation person rows | 376,035 | 227,116 |
| Eligible person rows | 190,187 | 116,092 |
| Unweighted eligibility rate | 0.505769 | 0.511157 |
| Unweighted positive rate | 0.381340 | 0.397082 |
| `PWGTP`-weighted positive rate | — | — |
| Unique households in safe raw rows | 148,285 | 89,841 |
| Eligible train people | 161,751 | 96,464 |
| Eligible validation people | 28,436 | 19,628 |

**Comparability warning:** 2016 train/validation covers all assigned households (85% + 15%), whereas 2017 train/validation covers 60% (50% + 10%). These counts are not full-year totals. The positive-rate difference is descriptive only: it is not population-weighted unless explicitly labelled, and the nominal `PINCP > 50000` target is not constant-purchasing-power comparable across years. No US-population inference is made.

The original 2026-11-01 run calculated only unweighted positive rates, so weighted cells are shown as unavailable rather than backfilled. The current generator calculates `PWGTP`-weighted rates on subsequent runs.

## Interpretation and implications

- The code-set differences below are **observed support differences**, not evidence that Census code definitions changed. Sparse categories can appear or disappear through sampling alone.
- Before model training, freeze the official OCCP major-group mapping and specify how unseen or invalid codes are handled. Do not claim cross-year encoding drift solely from these lists.
- POBP is excluded from eligible slice features by default in the draft preregistration; its support comparison remains a data audit, not a modeling result.
- The next research gate is protocol validation and preregistration freezing—not model training. Owner-controlled values and interval-coverage checks remain unresolved.

## 2016 detailed diagnostics

- Household-size quantiles (unweighted, safe raw rows): {"0.0": 1.0, "0.25": 1.0, "0.5": 2.0, "0.75": 3.0, "0.9": 5.0, "0.99": 8.0, "1.0": 20.0}
- Feature missingness: {"AGEP": 0.0, "COW": 0.0, "MAR": 0.0, "OCCP": 0.0, "POBP": 0.0, "RAC1P": 0.0, "RELP": 0.0, "SCHL": 0.0, "SEX": 0.0, "WKHP": 0.0}
- Feature cardinality: {"AGEP": 75, "COW": 8, "MAR": 5, "OCCP": 477, "POBP": 212, "RAC1P": 9, "RELP": 18, "SCHL": 24, "SEX": 2, "WKHP": 97}
- Target missingness: 0.000000

## 2017 detailed diagnostics

- Household-size quantiles (unweighted, safe raw rows): {"0.0": 1.0, "0.25": 1.0, "0.5": 2.0, "0.75": 3.0, "0.9": 5.0, "0.99": 8.0, "1.0": 20.0}
- Feature missingness: {"AGEP": 0.0, "COW": 0.0, "MAR": 0.0, "OCCP": 0.0, "POBP": 0.0, "RAC1P": 0.0, "RELP": 0.0, "SCHL": 0.0, "SEX": 0.0, "WKHP": 0.0}
- Feature cardinality: {"AGEP": 75, "COW": 8, "MAR": 5, "OCCP": 476, "POBP": 219, "RAC1P": 9, "RELP": 18, "SCHL": 24, "SEX": 2, "WKHP": 96}
- Target missingness: 0.000000

## OCC_CODES code-set comparison (train/validation only)

- 2016 unique codes: 477
- 2017 unique codes: 476
- 2016 only: ["6740.0", "7930.0"]
- 2017 only: ["8420.0"]

## POBP_CODES code-set comparison (train/validation only)

- 2016 unique codes: 212
- 2017 unique codes: 219
- 2016 only: ["168", "208", "464", "511"]
- 2017 only: ["142", "166", "203", "219", "228", "338", "420", "423", "425", "456", "469"]

## Remaining limitations and research gate

- No model training, prediction generation, or discovery/confirmation metrics were produced.
- No inflation adjustment was applied; the primary target is nominal `PINCP > 50000`.
- Validate Newcombe score-interval coverage by simulation before relying on the interval procedure.
- McNemar's person-level independence assumption remains an explicit limitation under household clustering; do not silently substitute another confirmation test.
- Resolve and freeze the preregistration's owner TODOs before M0.2.

## Exact installed Folktables task definition

```text
Folktables version: 0.0.12
## adult_filter source
def adult_filter(data):
    """Mimic the filters in place for Adult data.

    Adult documentation notes: Extraction was done by Barry Becker from
    the 1994 Census database. A set of reasonably clean records was extracted
    using the following conditions:
    ((AAGE>16) && (AGI>100) && (AFNLWGT>1)&& (HRSWK>0))
    """
    df = data
    df = df[df['AGEP'] > 16]
    df = df[df['PINCP'] > 100]
    df = df[df['WKHP'] > 0]
    df = df[df['PWGTP'] >= 1]
    return df


## ACSIncome task definition
features = ['AGEP', 'COW', 'SCHL', 'MAR', 'OCCP', 'POBP', 'RELP', 'WKHP', 'SEX', 'RAC1P']
target = 'PINCP'
target_transform source = target_transform=lambda x: x > 50000,
group = 'RAC1P'
preprocess source = def adult_filter(data):
    """Mimic the filters in place for Adult data.

    Adult documentation notes: Extraction was done by Barry Becker from
    the 1994 Census database. A set of reasonably clean records was extracted
    using the following conditions:
    ((AAGE>16) && (AGI>100) && (AFNLWGT>1)&& (HRSWK>0))
    """
    df = data
    df = df[df['AGEP'] > 16]
    df = df[df['PINCP'] > 100]
    df = df[df['WKHP'] > 0]
    df = df[df['PWGTP'] >= 1]
    return df
postprocess source = postprocess=lambda x: np.nan_to_num(x, -1),
```
