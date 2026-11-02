"""M0.1 data and split audit. Held-out task rows remain sealed.

Usage:
    python research/m0/prepare_m0.py                     # download CA PUMS from Census
    python research/m0/prepare_m0.py --raw-dir FILES     # fully offline; FILES/{2016,2017}
"""

# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SliceAudit contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import platform
import re
import shutil
import subprocess
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


def _weighted_mean(values: Any, weights: Any) -> float:
    """Return a weighted mean after aligning non-missing value/weight pairs."""
    value_series = pd.Series(values).reset_index(drop=True)
    weight_series = pd.Series(weights).reset_index(drop=True)
    if len(value_series) != len(weight_series):
        raise ValueError("Weighted-mean values and weights must have equal lengths")
    valid = value_series.notna() & weight_series.notna()
    if not valid.any():
        return float("nan")
    valid_weights = weight_series.loc[valid].astype(float)
    if (valid_weights < 0).any():
        raise ValueError("Weighted-mean weights must be non-negative")
    total_weight = float(valid_weights.sum())
    if total_weight <= 0:
        return float("nan")
    return float(np.average(value_series.loc[valid].astype(float), weights=valid_weights))


def _portable_provenance(record: dict[str, Any], year: int) -> dict[str, Any]:
    """Replace operator-specific local paths with stable, publishable labels."""
    portable = dict(record)
    if record.get("mode") == "local_file":
        source_name = Path(str(record["source_path"])).name
        portable["source_path"] = f"operator-supplied/{year}/{source_name}"
        portable["staged_csv"] = f"data/{year}/1-Year/{PUMS_CSV_NAME[year]}"
    return portable


def _git_revision() -> str:
    """Identify the source revision without making Git a runtime dependency."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=OUT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else "unknown"


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
        "eligible_rate_unweighted": float(len(filtered) / len(safe_raw)),
        "positive_rate_unweighted": float(actual.mean()),
        "positive_rate_pwgtp_weighted": _weighted_mean(
            actual, filtered["PWGTP"].reset_index(drop=True)
        ),
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

def build_report(
    *,
    offline: bool,
    provenance: dict[str, dict[str, Any]],
    task_artifacts: dict[str, dict[str, Any]],
    stats: dict[int, dict[str, Any]],
    run_timestamp: str,
    source_revision: str,
    python_version: str,
    versions: dict[str, str],
    definition_text: str,
) -> str:
    """Render a self-contained M0.1 audit report without held-out task data."""
    command = (
        "uv run python research/m0/prepare_m0.py --raw-dir <PUMS_ROOT>"
        if offline
        else "uv run python research/m0/prepare_m0.py"
    )

    def rate(value: Any) -> str:
        return "—" if value is None else f"{float(value):.6f}"

    lines = [
        "# M0.1 data report",
        "",
        "> **Status: M0.1 completed; model validation has not started.** "
        "Train/validation summaries only. Discovery and confirmation task rows were not filtered or summarized.",
        "",
        "## Executive summary",
        "",
        "- The real California ACS PUMS 2016 and 2017 data-and-split audit completed using "
        f"{'operator-supplied local archives' if offline else 'Folktables Census downloads'}.",
        f"- Safe ACSIncome artifacts contain **{stats[2016]['eligible_person_rows']:,}** eligible "
        f"train/validation people for 2016 and **{stats[2017]['eligible_person_rows']:,}** for 2017.",
        "- Runtime checks confirmed household isolation, California-only input, the target rule, and "
        "exclusion of discovery/confirmation rows from task filtering and artifacts.",
        "- **Open provenance limitation:** local source hashes identify the exact bytes used, but offline "
        "mode did not verify them against an upstream Census checksum.",
        "- This report validates data preparation only. It contains no model comparison and provides no "
        "empirical evidence yet for SliceAudit's hidden-regression claim.",
        "",
        "## Run and reproducibility",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Run date (UTC) | `{run_timestamp}` |",
        f"| Source revision | `{source_revision}` |",
        f"| Execution command | `{command}` |",
        f"| Python | `{python_version}` |",
        f"| Key packages | Folktables `{versions['folktables']}`, pandas `{versions['pandas']}`, "
        f"PyArrow `{versions['pyarrow']}`, NumPy `{versions['numpy']}` |",
        "",
        "The complete runtime record and earlier blocked attempts are in [`ENV.md`](ENV.md). Raw data, "
        "split assignments, and processed Parquet files are intentionally not committed. Independent "
        "verification therefore requires the source files and a rerun; recorded hashes support identity "
        "checks but do not by themselves authenticate the upstream release.",
        "",
        "## Raw data provenance",
        "",
        f"- Acquisition mode: `{'local_files' if offline else 'census_download'}`",
    ]
    for year in (2016, 2017):
        record = provenance[str(year)]
        if record["mode"] == "local_file":
            lines.append(
                f"- {year}: `{record['source_path']}` ({record['source_bytes']:,} bytes; SHA-256 "
                f"`{record['source_sha256']}`), staged as `{record['staged_csv']}`"
            )
        else:
            lines.append(
                f"- {year}: downloaded by Folktables from "
                f"`https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/{CENSUS_ZIP_NAME}`"
            )
    lines.extend([
        "",
        "Offline staging validates the expected file layout, required columns, and California state code. "
        "It does not verify an upstream Census checksum or independently prove the survey year of a "
        "hand-supplied archive; the operator remains responsible for source authenticity.",
        "",
        "## Audit checks",
        "",
        "| Check | Result | Basis |",
        "| --- | --- | --- |",
        "| Households assigned before task filtering | Pass | Split manifest is built from raw household IDs before `adult_filter`. |",
        "| Household cross-split assignments | **0** | `assert_no_household_leakage` rejects duplicate or conflicting assignments. |",
        "| Raw rows restricted to California | Pass | Every raw row must have `ST = 06`. |",
        "| ACSIncome target rule | Pass | Labels must equal `PINCP > 50000` on safe rows. |",
        "| Held-out task firewall | Pass | Only train/validation households enter task filtering and Parquet artifacts. |",
        "| Row-order invariance | Covered by unit test | `test_split_logic.py` compares shuffled and original assignments. |",
        "| Upstream Census source authentication | **Not verified** | No upstream checksum comparison was performed in offline mode. |",
        "| Artifact SHA-256 values | Recorded | Values below identify the generated artifacts; they are not an independent rerun. |",
        "",
        "## Saved ACSIncome task artifacts",
        "",
        "Files contain only task-eligible train/validation people and preserve `SERIALNO`, `SPORDER`, "
        "`PWGTP`, `ST`, `ADJINC`, and split assignment.",
        "",
    ])
    for year in (2016, 2017):
        artifact = task_artifacts[str(year)]
        lines.append(
            f"- {year}: `{artifact['path']}` ({artifact['rows']:,} rows; SHA-256 "
            f"`{artifact['sha256']}`)"
        )
    lines.extend([
        "",
        "## Safe-partition summary",
        "",
        "| Metric | 2016 | 2017 |",
        "| --- | ---: | ---: |",
        f"| Raw train/validation person rows | {stats[2016]['raw_person_rows']:,} | {stats[2017]['raw_person_rows']:,} |",
        f"| Eligible person rows | {stats[2016]['eligible_person_rows']:,} | {stats[2017]['eligible_person_rows']:,} |",
        f"| Unweighted eligibility rate | {rate(stats[2016]['eligible_rate_unweighted'])} | {rate(stats[2017]['eligible_rate_unweighted'])} |",
        f"| Unweighted positive rate | {rate(stats[2016]['positive_rate_unweighted'])} | {rate(stats[2017]['positive_rate_unweighted'])} |",
        f"| `PWGTP`-weighted positive rate | {rate(stats[2016].get('positive_rate_pwgtp_weighted'))} | {rate(stats[2017].get('positive_rate_pwgtp_weighted'))} |",
        f"| Unique households in safe raw rows | {stats[2016]['households']:,} | {stats[2017]['households']:,} |",
        f"| Eligible train people | {stats[2016]['eligible_by_split']['train']:,} | {stats[2017]['eligible_by_split']['train']:,} |",
        f"| Eligible validation people | {stats[2016]['eligible_by_split']['validation']:,} | {stats[2017]['eligible_by_split']['validation']:,} |",
        "",
        "**Comparability warning:** 2016 train/validation covers all assigned households (85% + 15%), "
        "whereas 2017 train/validation covers 60% (50% + 10%). These counts are not full-year totals. "
        "The positive-rate difference is descriptive only: it is not population-weighted unless explicitly "
        "labelled, and the nominal `PINCP > 50000` target is not constant-purchasing-power comparable "
        "across years. No US-population inference is made.",
        "",
    ])
    if any(stats[y].get("positive_rate_pwgtp_weighted") is None for y in (2016, 2017)):
        lines.extend([
            "The original 2026-11-01 run calculated only unweighted positive rates, so weighted cells are "
            "shown as unavailable rather than backfilled. The current generator calculates `PWGTP`-weighted "
            "rates on subsequent runs.",
            "",
        ])
    lines.extend([
        "## Interpretation and implications",
        "",
        "- The code-set differences below are **observed support differences**, not evidence that Census "
        "code definitions changed. Sparse categories can appear or disappear through sampling alone.",
        "- Before model training, freeze the official OCCP major-group mapping and specify how unseen or "
        "invalid codes are handled. Do not claim cross-year encoding drift solely from these lists.",
        "- POBP is excluded from eligible slice features by default in the draft preregistration; its "
        "support comparison remains a data audit, not a modeling result.",
        "- The next research gate is protocol validation and preregistration freezing—not model training. "
        "Owner-controlled values and interval-coverage checks remain unresolved.",
        "",
    ])
    for year in (2016, 2017):
        lines.extend([
            f"## {year} detailed diagnostics",
            "",
            f"- Household-size quantiles (unweighted, safe raw rows): {json.dumps(stats[year]['household_size_quantiles'], sort_keys=True)}",
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
        "## Remaining limitations and research gate",
        "",
        "- No model training, prediction generation, or discovery/confirmation metrics were produced.",
        "- No inflation adjustment was applied; the primary target is nominal `PINCP > 50000`.",
        "- Validate Newcombe score-interval coverage by simulation before relying on the interval procedure.",
        "- McNemar's person-level independence assumption remains an explicit limitation under household "
        "clustering; do not silently substitute another confirmation test.",
        "- Resolve and freeze the preregistration's owner TODOs before M0.2.",
        "",
        "## Exact installed Folktables task definition",
        "",
        "```text",
        definition_text.rstrip(),
        "```",
        "",
    ])
    return "\n".join(lines)


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
            staged_record = stage_local_raw(args.raw_dir, year, DATA_DIR)
            provenance[str(year)] = _portable_provenance(staged_record, year)
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
    run_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source_revision = _git_revision()
    python_version = platform.python_version()
    versions = {
        package: _version(package)
        for package in ("numpy", "scipy", "pandas", "pyarrow", "scikit-learn", "folktables")
    }
    command = (
        "uv run python research/m0/prepare_m0.py --raw-dir <PUMS_ROOT>"
        if offline
        else "uv run python research/m0/prepare_m0.py"
    )
    payload = {
        "salt": SALT,
        "assignment": "SHA256(salt + SERIALNO) mod 10000",
        "unit": "household",
        "run": {
            "timestamp_utc": run_timestamp,
            "source_revision": source_revision,
            "python": python_version,
            "command": command,
        },
        "raw_data_acquisition": "local_files" if offline else "census_download",
        "raw_source": provenance,
        "households_by_year_and_split": split_counts,
        "eligible_person_counts_train_validation": {
            str(y): stats[y]["eligible_by_split"] for y in (2016, 2017)
        },
        "acs_income_task_artifacts": task_artifacts,
        "splits_parquet_sha256": digest,
        "audit_checks": {
            "household_cross_split_count": 0,
            "california_only_raw_rows": True,
            "target_rule_verified_on_safe_rows": True,
            "heldout_task_rows_inspected": False,
            "row_order_invariance": "unit_tested",
            "upstream_checksum_verified": False,
        },
        "heldout_task_rows_inspected": False,
    }
    (OUT / "split_manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    env_body = "\n".join([
        f"- Run date (UTC): {run_timestamp}",
        f"- Source revision: `{source_revision}`",
        f"- Execution command: `{command}`",
        f"- Python: {python_version}",
        *(f"- {k}: {v}" for k, v in versions.items()),
        f"- Raw data acquisition: {'local_files (offline)' if offline else 'census_download'}",
        *(f"- {y} source: `{provenance[str(y)].get('source_path', 'www2.census.gov')}` sha256 `{provenance[str(y)].get('source_sha256', 'n/a')}`" for y in (2016, 2017)),
        "",
        "Review the installed Folktables version and task filter before accepting this report.",
    ])
    write_runtime_env(OUT / "ENV.md", env_body)
    definition_text = (OUT / "folktables_definition.txt").read_text(encoding="utf-8")
    report = build_report(
        offline=offline,
        provenance=provenance,
        task_artifacts=task_artifacts,
        stats=stats,
        run_timestamp=run_timestamp,
        source_revision=source_revision,
        python_version=python_version,
        versions=versions,
        definition_text=definition_text,
    )
    (OUT / "01_data_report.md").write_text(report, encoding="utf-8")
    print("M0.1 complete; manifest rows:", len(manifest), "SHA-256:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
