"""M0.1 data and split audit. Held-out task rows remain sealed.

Usage:
    python research/m0/prepare_m0.py                     # download CA PUMS from Census
    python research/m0/prepare_m0.py --raw-dir FILES     # fully offline; FILES/{2016,2017}
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import platform
import re
import shutil
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
DATA_DIR = OUT / "data"
SALT = "sliceaudit-acsincome-ca-2016-2017-v1"
FEATURES = ["AGEP", "COW", "SCHL", "MAR", "OCCP", "POBP", "RELP", "WKHP", "SEX", "RAC1P"]
BUCKETS = {
    2017: [(0, 5000, "train"), (5000, 6000, "validation"), (6000, 8000, "discovery"), (8000, 10000, "confirmation")],
    2016: [(0, 8500, "train"), (8500, 10000, "validation")],
}
REQUIRED_RAW_FIELDS = {"SERIALNO", "SPORDER", "PWGTP", "ST", "ADJINC", "PINCP", *FEATURES}
CALIFORNIA_ST_CODE = "06"
# Folktables derives the on-disk name differently per year: 2017+ uses the numeric state
# code ("psam_p06.csv"), 2016 and earlier use the state abbreviation ("ss16pca.csv").
# Offline staging must reproduce these names exactly or get_data(download=False) fails.
PUMS_CSV_NAME = {2016: "ss16pca.csv", 2017: "psam_p06.csv"}
# The Census download is named identically for both years, so year subdirectories are required.
CENSUS_ZIP_NAME = "csv_pca.zip"
ENV_BEGIN = "<!-- BEGIN GENERATED: m0_1_runtime -->"
ENV_END = "<!-- END GENERATED: m0_1_runtime -->"


def household_digest(serialno: Any, salt: str = SALT) -> str:
    if pd.isna(serialno):
        raise ValueError("SERIALNO contains missing values")
    raw = f"{salt}{str(serialno).strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def assign_household_splits(raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """Return exactly one deterministic split assignment per household."""
    if "SERIALNO" not in raw:
        raise KeyError("SERIALNO missing from raw PUMS data")
    if raw["SERIALNO"].isna().any():
        raise ValueError("SERIALNO contains missing values; refusing to silently drop households")
    serials = sorted(raw["SERIALNO"].astype(str).str.strip().unique())
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _missing_required_columns(columns: Sequence[str]) -> list[str]:
    normalized = {str(c).strip().strip('"').upper() for c in columns}
    return sorted(REQUIRED_RAW_FIELDS - normalized)


def resolve_local_raw_source(raw_dir: Path | str, year: int) -> Path:
    """Locate an operator-supplied PUMS file for ``year`` without any network access."""
    if year not in PUMS_CSV_NAME:
        raise ValueError(f"Unsupported survey year: {year}")
    year_dir = Path(raw_dir) / str(year)
    if not year_dir.is_dir():
        raise FileNotFoundError(
            f"Offline raw directory is missing {year_dir}; expected the Census file at "
            f"{year_dir / CENSUS_ZIP_NAME} or an extracted {PUMS_CSV_NAME[year]}"
        )
    candidates = [year_dir / CENSUS_ZIP_NAME, year_dir / PUMS_CSV_NAME[year]]
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    raise FileNotFoundError(
        f"No non-empty PUMS file found in {year_dir}; expected {CENSUS_ZIP_NAME} or "
        f"{PUMS_CSV_NAME[year]}"
    )


def _validate_staged_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        header = handle.readline().strip()
        first_row = handle.readline().strip()
    if not header:
        raise ValueError(f"{path} is empty")
    if not first_row:
        raise ValueError(f"{path} contains a header but no data rows")
    missing = _missing_required_columns(header.split(","))
    if missing:
        raise KeyError(f"{path} is missing required PUMS columns: {missing}")


def stage_local_raw(raw_dir: Path | str, year: int, dest_dir: Path | str = DATA_DIR) -> dict[str, Any]:
    """Copy or extract a local PUMS file into the on-disk layout Folktables expects.

    Nothing is downloaded. The staged CSV is the same file Folktables would have fetched,
    so the split contract and firewall are unaffected by acquiring it by hand.
    """
    source = resolve_local_raw_source(raw_dir, year)
    target_dir = Path(dest_dir) / str(year) / "1-Year"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / PUMS_CSV_NAME[year]
    staging = target.with_name(target.name + ".staging")
    try:
        if source.suffix.lower() == ".zip":
            with zipfile.ZipFile(source) as archive:
                members = [
                    name for name in archive.namelist()
                    if Path(name).name.lower() == PUMS_CSV_NAME[year]
                ]
                if len(members) != 1:
                    raise ValueError(
                        f"{source} must contain exactly one {PUMS_CSV_NAME[year]} member; "
                        f"found {len(members)}"
                    )
                with archive.open(members[0]) as reader, staging.open("wb") as writer:
                    shutil.copyfileobj(reader, writer)
        else:
            if source.name.lower() != PUMS_CSV_NAME[year]:
                raise ValueError(
                    f"Expected extracted file {PUMS_CSV_NAME[year]} for {year}, got {source.name}"
                )
            shutil.copyfile(source, staging)
        _validate_staged_csv(staging)
        staging.replace(target)
    finally:
        staging.unlink(missing_ok=True)
    return {
        "mode": "local_file",
        "source_path": str(source),
        "source_sha256": _sha256_file(source),
        "source_bytes": int(source.stat().st_size),
        "staged_csv": str(target),
        "staged_csv_sha256": _sha256_file(target),
    }


def _marker_spans(text: str) -> tuple[list[re.Match], list[re.Match]]:
    """Only a marker alone on its own line delimits the block; prose mentions do not."""
    begins = list(re.finditer(rf"^{re.escape(ENV_BEGIN)}\s*$", text, re.MULTILINE))
    ends = list(re.finditer(rf"^{re.escape(ENV_END)}\s*$", text, re.MULTILINE))
    return begins, ends


def write_runtime_env(path: Path, body: str) -> None:
    """Replace only the generated runtime block so hand-written environment history survives.

    Anything ambiguous (no block, or a malformed block) is treated as hand-written history and
    a fresh block is appended, because losing history is worse than a duplicated record.
    """
    block = f"{ENV_BEGIN}\n{body.strip()}\n{ENV_END}\n"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# M0.1 environment status\n"
    begins, ends = _marker_spans(existing)
    if len(begins) == 1 and len(ends) == 1 and begins[0].start() < ends[0].start():
        head = existing[: begins[0].start()]
        tail = existing[ends[0].end():].lstrip("\n")
        updated = head + block + tail
    else:
        updated = existing.rstrip("\n") + "\n\n## Generated runtime record\n\n" + block
    path.write_text(updated, encoding="utf-8")



def _labels_as_series(labels: Any, year: int) -> pd.Series:
    """Normalize Folktables df_to_pandas labels, returned as a one-column DataFrame."""
    values = labels.to_numpy() if hasattr(labels, "to_numpy") else np.asarray(labels)
    if values.ndim == 2:
        if values.shape[1] != 1:
            raise AssertionError(
                f"Expected one ACSIncome target column for {year}; got shape {values.shape}"
            )
        values = values[:, 0]
    elif values.ndim != 1:
        raise AssertionError(f"Expected one-dimensional ACSIncome labels for {year}; got shape {values.shape}")
    return pd.Series(values).astype(int).reset_index(drop=True)


def _callable_source(value: Any) -> str:
    if value is None:
        return "None"
    try:
        return inspect.getsource(value).strip()
    except (OSError, TypeError):
        return f"<source unavailable; callable repr={value!r}>"


def describe_safe_partition(
    raw: pd.DataFrame, year: int, manifest: pd.DataFrame
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Build and summarize ACSIncome rows from train/validation households only.

    The returned task frame contains no discovery or confirmation feature/target values.
    It preserves household, weight, state, and source-row identifiers for auditing.
    """
    from folktables import ACSIncome, adult_filter

    safe_ids = set(manifest.loc[
        (manifest["year"] == year) & manifest["split"].isin(["train", "validation"]),
        "SERIALNO"
    ].astype(str))
    safe_raw = raw.loc[raw["SERIALNO"].astype(str).str.strip().isin(safe_ids)].copy()
    if safe_raw.empty:
        raise RuntimeError(f"No train/validation raw rows for {year}")

    features, labels, groups = ACSIncome.df_to_pandas(safe_raw.copy())
    filtered = adult_filter(safe_raw.copy()).copy()
    actual = _labels_as_series(labels, year)
    if not isinstance(features, pd.DataFrame):
        raise TypeError(f"ACSIncome features for {year} must be a pandas DataFrame")
    if list(features.columns) != FEATURES:
        raise AssertionError(
            f"ACSIncome feature columns changed for {year}: {list(features.columns)}"
        )
    if len(filtered) != len(features) or len(filtered) != len(actual) or len(filtered) != len(groups):
        raise AssertionError(
            f"Folktables row mismatch for {year}: filtered={len(filtered)}, "
            f"features={len(features)}, labels={len(actual)}, groups={len(groups)}"
        )

    expected = filtered["PINCP"].gt(50_000).astype(int).reset_index(drop=True)
    if not expected.equals(actual):
        raise AssertionError(f"Target mismatch: ACSIncome is not PINCP > 50000 for {year}")

    split_lookup = (
        manifest.loc[manifest["year"] == year]
        .set_index("SERIALNO")["split"]
    )
    metadata_columns = ["SERIALNO", "SPORDER", "PWGTP", "ST", "ADJINC"]
    task_metadata = filtered.loc[:, metadata_columns].reset_index(drop=True).copy()
    task_metadata["split"] = (
        task_metadata["SERIALNO"].astype(str).str.strip().map(split_lookup)
    )
    if task_metadata["split"].isna().any():
        raise AssertionError(f"Eligible rows without a household split assignment for {year}")
    if not task_metadata["split"].isin(["train", "validation"]).all():
        raise AssertionError(f"Held-out rows entered the ACSIncome task artifact for {year}")

    task_frame = pd.concat(
        [
            task_metadata,
            features.reset_index(drop=True),
            actual.rename("target"),
        ],
        axis=1,
    )
    if task_frame.columns.duplicated().any():
        raise AssertionError(f"Duplicate columns in ACSIncome artifact for {year}")

    stats = {
        "year": year,
        "scope": "train+validation only",
        "raw_person_rows": int(len(safe_raw)),
        "eligible_person_rows": int(len(filtered)),
        "positive_rate": float(actual.mean()),
        "households": int(safe_raw["SERIALNO"].nunique()),
        "feature_missingness": {c: float(filtered[c].isna().mean()) for c in FEATURES},
        "feature_cardinality": {c: int(filtered[c].nunique(dropna=True)) for c in FEATURES},
        "target_missingness": float(filtered["PINCP"].isna().mean()),
        "occ_codes": sorted(str(x) for x in filtered["OCCP"].dropna().unique()),
        "pobp_codes": sorted(str(x) for x in filtered["POBP"].dropna().unique()),
        "household_size_quantiles": {
            str(q): float(v)
            for q, v in safe_raw.groupby("SERIALNO").size().quantile(
                [0, 0.25, 0.5, 0.75, 0.9, 0.99, 1]
            ).items()
        },
        "eligible_by_split": {},
    }
    for name in ("train", "validation"):
        stats["eligible_by_split"][name] = int(task_frame["split"].eq(name).sum())
    if sum(stats["eligible_by_split"].values()) != len(task_frame):
        raise AssertionError(f"Train/validation row counts do not sum to the task artifact for {year}")
    return stats, task_frame

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="M0.1 household split and safe-partition audit (held-out rows stay sealed)."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Fully offline: read already-downloaded Census PUMS files from DIR/{2016,2017} "
            "instead of contacting www2.census.gov. Accepts csv_pca.zip or an extracted "
            "psam_p06.csv (2017) / ss16pca.csv (2016)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    offline = args.raw_dir is not None
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from folktables import ACSDataSource, ACSIncome, adult_filter
    except Exception as exc:
        raise RuntimeError("Install project dependencies in Python 3.13 before running M0.1") from exc

    task_definition = [
        f"Folktables version: {_version('folktables')}",
        "## adult_filter source",
        inspect.getsource(adult_filter),
        "",
        "## ACSIncome task definition",
        f"features = {getattr(ACSIncome, 'features', None)!r}",
        f"target = {getattr(ACSIncome, 'target', None)!r}",
        f"target_transform source = {_callable_source(getattr(ACSIncome, 'target_transform', None))}",
        f"group = {getattr(ACSIncome, 'group', None)!r}",
        f"preprocess source = {_callable_source(getattr(ACSIncome, '_preprocess', None))}",
        f"postprocess source = {_callable_source(getattr(ACSIncome, '_postprocess', None))}",
    ]
    (OUT / "folktables_definition.txt").write_text(
        "\n".join(task_definition) + "\n", encoding="utf-8"
    )

    frames, manifests, provenance = {}, [], {}
    for year in (2016, 2017):
        source_kwargs = {"survey_year": str(year), "horizon": "1-Year", "survey": "person"}
        if "root_dir" in inspect.signature(ACSDataSource).parameters:
            source_kwargs["root_dir"] = str(DATA_DIR)
        source = ACSDataSource(**source_kwargs)
        if offline:
            provenance[str(year)] = stage_local_raw(args.raw_dir, year, DATA_DIR)
            download = False
        else:
            provenance[str(year)] = {"mode": "census_download", "source": "www2.census.gov"}
            download = True
        raw = source.get_data(states=["CA"], download=download)
        if not isinstance(raw, pd.DataFrame):
            raw = pd.DataFrame(raw)
        missing = sorted(REQUIRED_RAW_FIELDS - set(raw.columns))
        if missing:
            raise KeyError(f"{year} PUMS missing required fields: {missing}")
        states = set(raw["ST"].astype(str).str.strip().str.zfill(2).unique())
        if states != {CALIFORNIA_ST_CODE}:
            raise AssertionError(f"{year} PUMS is not California-only; ST values: {sorted(states)}")
        frames[year] = raw
        manifests.append(assign_household_splits(raw, year))

    manifest = pd.concat(manifests, ignore_index=True)
    assert_no_household_leakage(manifest)
    stats, task_frames = {}, {}
    for year in (2016, 2017):
        stats[year], task_frames[year] = describe_safe_partition(
            frames[year], year, manifest
        )

    task_output_dir = DATA_DIR / "processed"
    task_output_dir.mkdir(parents=True, exist_ok=True)
    task_artifacts = {}
    for year in (2016, 2017):
        task_path = task_output_dir / f"acs_income_train_validation_{year}.parquet"
        task_frames[year].to_parquet(task_path, index=False)
        task_digest = _sha256_file(task_path)
        task_digest_path = task_path.with_suffix(task_path.suffix + ".sha256")
        task_digest_path.write_text(
            f"{task_digest}  {task_path.name}\n", encoding="utf-8"
        )
        task_artifacts[str(year)] = {
            "path": task_path.relative_to(OUT).as_posix(),
            "rows": int(len(task_frames[year])),
            "columns": list(task_frames[year].columns),
            "scope": "train+validation only",
            "sha256": task_digest,
        }

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
        "assignment": "SHA256(salt + SERIALNO) mod 10000",
        "unit": "household",
        "raw_data_acquisition": "local_files" if offline else "census_download",
        "raw_source": provenance,
        "households_by_year_and_split": split_counts,
        "eligible_person_counts_train_validation": {
            str(y): stats[y]["eligible_by_split"] for y in (2016, 2017)
        },
        "acs_income_task_artifacts": task_artifacts,
        "splits_parquet_sha256": digest,
        "heldout_task_rows_inspected": False,
    }
    (OUT / "split_manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    versions = {p: _version(p) for p in ("numpy", "scipy", "pandas", "pyarrow", "scikit-learn", "folktables")}
    env_body = "\n".join([
        f"- Run date (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Python: {platform.python_version()}",
        *(f"- {k}: {v}" for k, v in versions.items()),
        f"- Raw data acquisition: {'local_files (offline)' if offline else 'census_download'}",
        *(f"- {y} source: `{provenance[str(y)].get('source_path', 'www2.census.gov')}` sha256 `{provenance[str(y)].get('source_sha256', 'n/a')}`" for y in (2016, 2017)),
        "",
        "Review the installed Folktables version and task filter before accepting this report.",
    ])
    write_runtime_env(OUT / "ENV.md", env_body)
    lines = [
        "# M0.1 data report",
        "",
        "> Train/validation summaries only. Discovery and confirmation task rows were not filtered or summarized.",
        "",
        "## Raw data provenance",
        "",
        f"- Acquisition mode: `{'local_files' if offline else 'census_download'}`",
    ]
    for year in (2016, 2017):
        record = provenance[str(year)]
        if record["mode"] == "local_file":
            lines.append(
                f"- {year}: local file `{record['source_path']}` "
                f"({record['source_bytes']:,} bytes, sha256 `{record['source_sha256']}`), "
                f"staged to `{record['staged_csv']}`"
            )
        else:
            lines.append(
                f"- {year}: downloaded by Folktables from "
                f"`https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/{CENSUS_ZIP_NAME}`"
            )
    lines.extend([
        "- Offline mode does not verify the upstream Census checksum; the operator must confirm the files.",
        "",
    ])
    lines.extend([
        "## Saved ACSIncome task artifacts",
        "",
        "- Files contain only task-eligible train/validation persons and preserve SERIALNO, SPORDER, PWGTP, ST, ADJINC, and split assignment.",
        "- Discovery and confirmation household rows are excluded before the Folktables task filter and are not present in these artifacts.",
        "",
    ])
    for year in (2016, 2017):
        artifact = task_artifacts[str(year)]
        lines.append(
            f"- {year}: `{artifact['path']}` ({artifact['rows']:,} rows, "
            f"SHA-256 `{artifact['sha256']}`)"
        )
    lines.append("")
    for year in (2016, 2017):
        lines.extend([
            f"## {year}",
            "",
            f"- Raw train/validation person rows: {stats[year]['raw_person_rows']:,}",
            f"- Eligible person rows: {stats[year]['eligible_person_rows']:,}",
            f"- Positive rate (safe partitions only): {stats[year]['positive_rate']:.6f}",
            f"- Unique households in safe raw rows: {stats[year]['households']:,}",
            f"- Eligible persons by split: {json.dumps(stats[year]['eligible_by_split'], sort_keys=True)}",
            f"- Household-size quantiles: {json.dumps(stats[year]['household_size_quantiles'], sort_keys=True)}",
            f"- Feature missingness: {json.dumps(stats[year]['feature_missingness'], sort_keys=True)}",
            f"- Feature cardinality: {json.dumps(stats[year]['feature_cardinality'], sort_keys=True)}",
            f"- Target missingness: {stats[year]['target_missingness']:.6f}",
            "",
        ])
    for code in ("occ_codes", "pobp_codes"):
        left = set(stats[2016][code])
        right = set(stats[2017][code])
        lines.extend([
            f"## {code.upper()} code-set comparison (train/validation only)",
            "",
            f"- 2016 unique codes: {len(left)}",
            f"- 2017 unique codes: {len(right)}",
            f"- 2016 only: {json.dumps(sorted(left - right))}",
            f"- 2017 only: {json.dumps(sorted(right - left))}",
            "",
        ])
    lines.extend([
        "## Execution boundaries",
        "",
        "- Household split assignment precedes task filtering.",
        "- No model training, prediction generation, or metrics on discovery/confirmation.",
        "- No inflation adjustment; primary target is nominal PINCP > 50000.",
        "- Validate Newcombe score-interval coverage by simulation as specified in the roadmap.",
        "- McNemar's person-level independence assumption remains an explicit limitation; do not silently substitute another confirmation test.",
    ])
    definition_text = (OUT / "folktables_definition.txt").read_text(encoding="utf-8")
    lines.extend([
        "## Exact installed Folktables task definition",
        "",
        "```text",
        definition_text.rstrip(),
        "```",
        "",
    ])
    (OUT / "01_data_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("M0.1 complete; manifest rows:", len(manifest), "SHA-256:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
