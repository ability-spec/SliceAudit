# M0.1 data report

> Train/validation summaries only. Discovery and confirmation task rows were not filtered or summarized.

## Raw data provenance

- Acquisition mode: `local_files`
- 2016: local file `/Users/qobiljonerkinjonov/Desktop/SliceAudit/2016/csv_pca.zip` (75,148,888 bytes, sha256 `a434bf9316f174d896766488cd5fd4ae7356a9512258321110b62110c6ded818`), staged to `/Users/qobiljonerkinjonov/Desktop/SliceAudit-repo/research/m0/data/2016/1-Year/ss16pca.csv`
- 2017: local file `/Users/qobiljonerkinjonov/Desktop/SliceAudit/2017/csv_pca.zip` (74,948,023 bytes, sha256 `d28c43dabd5fdc0abcba3d0941101bf6eceda4a84c1bdd269982adb8b89d6617`), staged to `/Users/qobiljonerkinjonov/Desktop/SliceAudit-repo/research/m0/data/2017/1-Year/psam_p06.csv`
- Offline mode does not verify the upstream Census checksum; the operator must confirm the files.

## Saved ACSIncome task artifacts

- Files contain only task-eligible train/validation persons and preserve SERIALNO, SPORDER, PWGTP, ST, ADJINC, and split assignment.
- Discovery and confirmation household rows are excluded before the Folktables task filter and are not present in these artifacts.

- 2016: `data/processed/acs_income_train_validation_2016.parquet` (190,187 rows, SHA-256 `e8469c68f878a33562243a812e0636411e2cdf8f06047a572d76fc2110718420`)
- 2017: `data/processed/acs_income_train_validation_2017.parquet` (116,092 rows, SHA-256 `32ca96ac7e939f12d7f0f57fc3552ab7ae2660360555333b653baf17c0b73810`)

## 2016

- Raw train/validation person rows: 376,035
- Eligible person rows: 190,187
- Positive rate (safe partitions only): 0.381340
- Unique households in safe raw rows: 148,285
- Eligible persons by split: {"train": 161751, "validation": 28436}
- Household-size quantiles: {"0.0": 1.0, "0.25": 1.0, "0.5": 2.0, "0.75": 3.0, "0.9": 5.0, "0.99": 8.0, "1.0": 20.0}
- Feature missingness: {"AGEP": 0.0, "COW": 0.0, "MAR": 0.0, "OCCP": 0.0, "POBP": 0.0, "RAC1P": 0.0, "RELP": 0.0, "SCHL": 0.0, "SEX": 0.0, "WKHP": 0.0}
- Feature cardinality: {"AGEP": 75, "COW": 8, "MAR": 5, "OCCP": 477, "POBP": 212, "RAC1P": 9, "RELP": 18, "SCHL": 24, "SEX": 2, "WKHP": 97}
- Target missingness: 0.000000

## 2017

- Raw train/validation person rows: 227,116
- Eligible person rows: 116,092
- Positive rate (safe partitions only): 0.397082
- Unique households in safe raw rows: 89,841
- Eligible persons by split: {"train": 96464, "validation": 19628}
- Household-size quantiles: {"0.0": 1.0, "0.25": 1.0, "0.5": 2.0, "0.75": 3.0, "0.9": 5.0, "0.99": 8.0, "1.0": 20.0}
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

## Execution boundaries

- Household split assignment precedes task filtering.
- No model training, prediction generation, or metrics on discovery/confirmation.
- No inflation adjustment; primary target is nominal PINCP > 50000.
- Validate Newcombe score-interval coverage by simulation as specified in the roadmap.
- McNemar's person-level independence assumption remains an explicit limitation; do not silently substitute another confirmation test.
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
