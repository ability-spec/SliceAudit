"""M0.1 data and split audit. Held-out task rows remain sealed."""
from __future__ import annotations

import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path
from typing import Any

import pandas as pd

OUT = Path(__file__).resolve().parent
DATA_DIR = OUT / "data"
SALT = "sliceaudit-acsincome-ca-2016-2017-v1"
FEATURES = ["AGEP", "COW", "SCHL", "MAR", "OCCP", "POBP", "RELP", "WKHP", "SEX", "RAC1P"]
BUCKETS = {
    2017: [(0, 5000, "train"), (5000, 6000, "validation"), (6000, 8000, "discovery"), (8000, 10000, "confirmation")],
    2016: [(0, 5000, "train"), (5000, 6000, "validation"), (6000, 10000, "unused")],
}


def household_digest(serialno: Any) -> str:
    if pd.isna(serialno):
        raise ValueError("SERIALNO contains missing values")
    raw = f"{SALT}|{str(serialno).strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def assign_household_splits(raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """Return exactly one deterministic split assignment per household."""
    if "SERIALNO" not in raw:
        raise KeyError("SERIALNO missing from raw PUMS data")
    serials = sorted(raw["SERIALNO"].dropna().astype(str).str.strip().unique())
    if not serials:
        raise ValueError(f"No SERIALNO values found for {year}")
    if year not in BUCKETS:
        raise ValueError(f"Unsupported survey year: {year}")
    rows = []
    for serial in serials:
        digest = household_digest(serial)
        bucket = int(digest, 16) % 10_000
        split = next((name for lo, hi, name in BUCKETS[year] if lo <= bucket < hi), None)
        if split is None:
            raise AssertionError(f"Uncovered hash bucket: {bucket}")
        rows.append({"year": year, "SERIALNO": serial, "split": split, "household_hash": digest})
    return pd.DataFrame(rows).sort_values("SERIALNO", kind="mergesort").reset_index(drop=True)


def assert_no_household_leakage(manifest: pd.DataFrame) -> None:
    if manifest["SERIALNO"].isna().any():
        raise AssertionError("Missing SERIALNO in manifest")
    if manifest.duplicated(["year", "SERIALNO"]).any():
        raise AssertionError("Manifest contains duplicate household IDs")
    counts = manifest.groupby(["year", "SERIALNO"])["split"].nunique()
    if (counts > 1).any():
        raise AssertionError("A household appears in multiple splits")


def _version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def describe_safe_partition(raw: pd.DataFrame, year: int, manifest: pd.DataFrame):
    """Apply Folktables task conversion only to train/validation household rows."""
    from folktables import ACSIncome, adult_filter

    safe_ids = set(manifest.loc[
        (manifest["year"] == year) & manifest["split"].isin(["train", "validation"]),
        "SERIALNO"
    ].astype(str))
    safe_raw = raw.loc[raw["SERIALNO"].astype(str).str.strip().isin(safe_ids)].copy()
    if safe_raw.empty:
        raise RuntimeError(f"No train/validation raw rows for {year}")

    features, labels, groups = ACSIncome.df_to_pandas(safe_raw)
    filtered = adult_filter(safe_raw.copy())
    if len(filtered) != len(labels):
        raise AssertionError(f"Folktables row mismatch for {year}: {len(filtered)} vs {len(labels)}")
    expected = filtered["PINCP"].gt(50_000).astype(int).reset_index(drop=True)
    actual = pd.Series(labels).astype(int).reset_index(drop=True)
    if not expected.equals(actual):
        raise AssertionError(f"Target mismatch: ACSIncome is not PINCP > 50000 for {year}")

    stats = {
        "year": year,
        "scope": "train+validation only",
        "raw_person_rows": int(len(safe_raw)),
        "eligible_person_rows": int(len(filtered)),
        "positive_rate": float(actual.mean()),
        "households": int(safe_raw["SERIALNO"].nunique()),
        "feature_missingness": {c: float(filtered[c].isna().mean()) for c in FEATURES},
        "feature_cardinality": {c: int(filtered[c].nunique(dropna=True)) for c in FEATURES},
        "eligible_by_split": {},
    }
    for name in ("train", "validation"):
        ids = set(manifest.loc[(manifest.year == year) & (manifest.split == name), "SERIALNO"])
        stats["eligible_by_split"][name] = int(
            filtered["SERIALNO"].astype(str).str.strip().isin(ids).sum()
        )
    return stats


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from folktables import ACSDataSource, adult_filter
    except Exception as exc:
        raise RuntimeError("Install project dependencies in Python 3.13 before running M0.1") from exc

    frames, manifests = {}, []
    for year in (2016, 2017):
        source = ACSDataSource(survey_year=str(year), horizon="1-Year", survey="person")
        raw = source.get_data(states=["CA"], download=True)
        if not isinstance(raw, pd.DataFrame):
            raw = pd.DataFrame(raw)
        required = {"SERIALNO", "SPORDER", "PWGTP", "ST", "ADJINC", "PINCP", *FEATURES}
        missing = sorted(required - set(raw.columns))
        if missing:
            raise KeyError(f"{year} PUMS missing required fields: {missing}")
        frames[year] = raw
        manifests.append(assign_household_splits(raw, year))

    manifest = pd.concat(manifests, ignore_index=True)
    assert_no_household_leakage(manifest)
    stats = {year: describe_safe_partition(frames[year], year, manifest) for year in (2016, 2017)}

    parquet_path = OUT / "splits.parquet"
    manifest.to_parquet(parquet_path, index=False)
    digest = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    (OUT / "splits.parquet.sha256").write_text(f"{digest}  splits.parquet\n", encoding="utf-8")

    split_counts = {
        str(year): {str(k): int(v) for k, v in manifest.loc[manifest.year == year, "split"].value_counts().items()}
        for year in (2016, 2017)
    }
    payload = {
        "salt": SALT,
        "assignment": "SHA256(salt + '|' + SERIALNO) mod 10000",
        "unit": "household",
        "households_by_year_and_split": split_counts,
        "eligible_person_counts_train_validation": {
            str(y): stats[y]["eligible_by_split"] for y in (2016, 2017)
        },
        "splits_parquet_sha256": digest,
        "heldout_task_rows_inspected": False,
    }
    (OUT / "split_manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    versions = {p: _version(p) for p in ("numpy", "scipy", "pandas", "pyarrow", "scikit-learn", "folktables")}
    (OUT / "ENV.md").write_text(
        "# M0.1 runtime environment\n\n"
        f"- Python: {platform.python_version()}\n"
        + "".join(f"- {k}: {v}\n" for k, v in versions.items())
        + "\nReview the installed Folktables version and task filter before accepting this report.\n",
        encoding="utf-8",
    )
    lines = [
        "# M0.1 data report",
        "",
        "> Train/validation summaries only. Discovery and confirmation task rows were not filtered or summarized.",
        "",
    ]
    for year in (2016, 2017):
        lines.extend([
            f"## {year}",
            "",
            f"- Raw train/validation person rows: {stats[year]['raw_person_rows']:,}",
            f"- Eligible person rows: {stats[year]['eligible_person_rows']:,}",
            f"- Positive rate (safe partitions only): {stats[year]['positive_rate']:.6f}",
            f"- Unique households in safe raw rows: {stats[year]['households']:,}",
            f"- Eligible persons by split: {json.dumps(stats[year]['eligible_by_split'], sort_keys=True)}",
            "",
        ])
    lines.extend([
        "## Execution boundaries",
        "",
        "- Household split assignment precedes task filtering.",
        "- No model training, prediction generation, or metrics on discovery/confirmation.",
        "- No inflation adjustment; primary target is nominal PINCP > 50000.",
        "- Match eligible training cohort sizes by whole-household subsampling before M0.2.",
        "- Cluster-aware confirmation test must be validated by simulation before G0.",
    ])
    (OUT / "01_data_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("M0.1 complete; manifest rows:", len(manifest), "SHA-256:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
