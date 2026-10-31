"""Dependency-light tests for household splits and the M0.1 data firewall."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare_m0 import (  # noqa: E402
    ENV_BEGIN,
    ENV_END,
    FEATURES,
    PUMS_CSV_NAME,
    SALT,
    assign_household_splits,
    assert_no_household_leakage,
    describe_safe_partition,
    household_digest,
    parse_args,
    resolve_local_raw_source,
    stage_local_raw,
    write_runtime_env,
)

PUMS_COLUMNS = ["SERIALNO", "SPORDER", "PWGTP", "ST", "ADJINC", "PINCP", *FEATURES]


def write_synthetic_pums_csv(path: Path, rows: int = 3, drop: str | None = None) -> Path:
    """Write a minimal CA-shaped PUMS CSV. Never used as an empirical artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [c for c in PUMS_COLUMNS if c != drop]
    lines = [",".join(columns)]
    for index in range(rows):
        values = {column: "1" for column in columns}
        values["SERIALNO"] = f"2017CA{index:08d}"
        values["ST"] = "6"
        values["PINCP"] = "60000"
        lines.append(",".join(values[column] for column in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_zip(source_csv: Path, zip_path: Path, member_name: str | None = None) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(source_csv, arcname=member_name or source_csv.name)
    return zip_path


class TestHashContract(unittest.TestCase):
    def test_digest_uses_direct_salt_serialno_concatenation(self):
        serialno = "2017CA00000001"
        expected = hashlib.sha256(f"{SALT}{serialno}".encode("utf-8")).hexdigest()
        self.assertEqual(household_digest(serialno), expected)

    def test_salt_changes_digest(self):
        self.assertNotEqual(
            household_digest("HH-1", "salt-a"),
            household_digest("HH-1", "salt-b"),
        )

    def test_missing_serialno_is_rejected(self):
        raw = pd.DataFrame({"SERIALNO": ["HH-1", None, "HH-2"]})
        with self.assertRaises(ValueError):
            assign_household_splits(raw, 2017)

    def test_unsupported_year_is_rejected(self):
        raw = pd.DataFrame({"SERIALNO": ["HH-1"]})
        with self.assertRaises(ValueError):
            assign_household_splits(raw, 2018)


class TestHouseholdSplit(unittest.TestCase):
    def test_one_manifest_row_per_household(self):
        raw = pd.DataFrame({"SERIALNO": ["A", "A", "B", "C", "C", "D"]})
        manifest = assign_household_splits(raw, 2017)
        self.assertEqual(len(manifest), raw["SERIALNO"].nunique())
        assert_no_household_leakage(manifest)

    def test_assignment_is_invariant_to_input_order(self):
        raw = pd.DataFrame({"SERIALNO": [f"HH{i:05d}" for i in range(3000)]})
        shuffled = raw.sample(frac=1, random_state=44).reset_index(drop=True)
        self.assertTrue(assign_household_splits(raw, 2017).equals(assign_household_splits(shuffled, 2017)))

    def test_bucket_shares_approximate_preregistered_targets(self):
        raw = pd.DataFrame({"SERIALNO": [f"HH{i:06d}" for i in range(20000)]})
        manifest = assign_household_splits(raw, 2017)
        shares = manifest["split"].value_counts(normalize=True)
        self.assertAlmostEqual(shares["train"], 0.50, delta=0.015)
        self.assertAlmostEqual(shares["validation"], 0.10, delta=0.010)
        self.assertAlmostEqual(shares["discovery"], 0.20, delta=0.015)
        self.assertAlmostEqual(shares["confirmation"], 0.20, delta=0.015)

    def test_2016_bucket_shares_match_roadmap(self):
        raw = pd.DataFrame({"SERIALNO": [f"HH{i:06d}" for i in range(20000)]})
        manifest = assign_household_splits(raw, 2016)
        shares = manifest["split"].value_counts(normalize=True)
        self.assertAlmostEqual(shares["train"], 0.85, delta=0.015)
        self.assertAlmostEqual(shares["validation"], 0.15, delta=0.015)
        self.assertEqual(set(manifest["split"]), {"train", "validation"})

    def test_leakage_guard_rejects_household_in_two_splits(self):
        manifest = assign_household_splits(pd.DataFrame({"SERIALNO": ["A", "B", "C"]}), 2017)
        row = manifest.iloc[[0]].copy()
        row.loc[:, "split"] = "confirmation" if row.iloc[0]["split"] != "confirmation" else "train"
        with self.assertRaises(AssertionError):
            assert_no_household_leakage(pd.concat([manifest, row], ignore_index=True))


class TestM01Firewall(unittest.TestCase):
    def test_task_filter_only_receives_train_and_validation_households(self):
        serials = [f"HH{i:04d}" for i in range(500)]
        raw = pd.DataFrame({
            "SERIALNO": [serial for serial in serials for _ in range(2)],
            "SPORDER": [order for _ in serials for order in (1, 2)],
            "PWGTP": 1, "ST": 6, "ADJINC": 1_000_000,
            "PINCP": [60_000, 20_000] * len(serials),
            "AGEP": 35, "WKHP": 40, "COW": 1, "SCHL": 21, "MAR": 1,
            "OCCP": 100, "POBP": 100, "RELP": 0, "SEX": 1, "RAC1P": 1,
        })
        manifest = assign_household_splits(raw, 2017)
        allowed = set(manifest.loc[manifest["split"].isin(["train", "validation"]), "SERIALNO"])
        seen = []

        def fake_filter(frame):
            seen.extend(frame["SERIALNO"].astype(str).unique().tolist())
            return frame[(frame["AGEP"] > 16) & (frame["WKHP"] >= 1) & (frame["PINCP"] >= 100)].copy()

        class FakeACSIncome:
            @staticmethod
            def df_to_pandas(frame):
                filtered = fake_filter(frame.copy())
                return filtered[FEATURES].copy(), pd.DataFrame({"PINCP": filtered["PINCP"].gt(50_000).astype(int)}), filtered["RAC1P"].copy()

        fake_module = types.ModuleType("folktables")
        fake_module.ACSIncome = FakeACSIncome
        fake_module.adult_filter = fake_filter
        with patch.dict(sys.modules, {"folktables": fake_module}):
            result = describe_safe_partition(raw, 2017, manifest)

        self.assertTrue(seen)
        self.assertTrue(set(seen).issubset(allowed))
        if isinstance(result, tuple):
            stats, filtered = result
            self.assertTrue(set(filtered["SERIALNO"].astype(str)).issubset(allowed))
            self.assertEqual(stats["eligible_train_validation_person_rows"], len(filtered))
        else:
            stats = result
            self.assertEqual(stats["eligible_person_rows"], stats["raw_person_rows"])


class TestOfflineRawMode(unittest.TestCase):
    """Offline acquisition must feed Folktables the same file, without the network."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.raw_dir = self.root / "raw"
        self.dest = self.root / "data"

    def test_folktables_file_names_match_installed_convention(self):
        # 2017+ uses the numeric state code, 2016 uses the state abbreviation.
        self.assertEqual(PUMS_CSV_NAME[2017], "psam_p06.csv")
        self.assertEqual(PUMS_CSV_NAME[2016], "ss16pca.csv")

    def test_default_run_still_uses_census_download(self):
        self.assertIsNone(parse_args([]).raw_dir)

    def test_raw_dir_flag_is_parsed(self):
        self.assertEqual(parse_args(["--raw-dir", "files"]).raw_dir, Path("files"))

    def test_missing_year_directory_is_rejected(self):
        self.raw_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            resolve_local_raw_source(self.raw_dir, 2016)

    def test_empty_year_directory_is_rejected(self):
        (self.raw_dir / "2017").mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):
            resolve_local_raw_source(self.raw_dir, 2017)

    def test_census_zip_is_preferred_over_extracted_csv(self):
        year_dir = self.raw_dir / "2017"
        csv_path = write_synthetic_pums_csv(year_dir / PUMS_CSV_NAME[2017])
        zip_path = write_zip(csv_path, year_dir / "csv_pca.zip")
        self.assertEqual(resolve_local_raw_source(self.raw_dir, 2017), zip_path)

    def test_extracted_csv_is_used_when_no_zip_exists(self):
        year_dir = self.raw_dir / "2016"
        csv_path = write_synthetic_pums_csv(year_dir / PUMS_CSV_NAME[2016])
        self.assertEqual(resolve_local_raw_source(self.raw_dir, 2016), csv_path)

    def test_staging_extracts_zip_into_folktables_layout(self):
        year_dir = self.raw_dir / "2017"
        csv_path = write_synthetic_pums_csv(year_dir / PUMS_CSV_NAME[2017])
        zip_path = write_zip(csv_path, year_dir / "csv_pca.zip")
        source_bytes = zip_path.read_bytes()

        record = stage_local_raw(self.raw_dir, 2017, self.dest)

        staged = self.dest / "2017" / "1-Year" / PUMS_CSV_NAME[2017]
        self.assertEqual(Path(record["staged_csv"]), staged)
        self.assertEqual(staged.read_text(encoding="utf-8"), csv_path.read_text(encoding="utf-8"))
        self.assertEqual(record["source_sha256"], hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(record["staged_csv_sha256"], hashlib.sha256(staged.read_bytes()).hexdigest())
        self.assertEqual(record["mode"], "local_file")
        self.assertEqual(zip_path.read_bytes(), source_bytes, "source zip must not be modified")
        self.assertEqual(list((self.dest / "2017" / "1-Year").glob("*.staging")), [])

    def test_staging_accepts_extracted_csv_for_2016_naming(self):
        year_dir = self.raw_dir / "2016"
        write_synthetic_pums_csv(year_dir / PUMS_CSV_NAME[2016])
        record = stage_local_raw(self.raw_dir, 2016, self.dest)
        self.assertTrue(Path(record["staged_csv"]).is_file())
        self.assertEqual(Path(record["staged_csv"]).name, "ss16pca.csv")

    def test_unrelated_files_are_not_accepted_as_pums_sources(self):
        year_dir = self.raw_dir / "2017"
        year_dir.mkdir(parents=True)
        (year_dir / "some_other_dataset.csv").write_text("SERIALNO,ST\\nX,6\\n", encoding="utf-8")
        (year_dir / "some_other_dataset.zip").write_bytes(b"not a census archive")
        with self.assertRaises(FileNotFoundError):
            resolve_local_raw_source(self.raw_dir, 2017)

    def test_zip_without_exact_folktables_member_is_rejected(self):
        year_dir = self.raw_dir / "2017"
        other_csv = write_synthetic_pums_csv(year_dir / "not_psam_p06.csv")
        write_zip(other_csv, year_dir / "csv_pca.zip")
        with self.assertRaisesRegex(ValueError, "psam_p06.csv"):
            stage_local_raw(self.raw_dir, 2017, self.dest)
        self.assertFalse((self.dest / "2017" / "1-Year" / "psam_p06.csv").exists())

    def test_corrupt_zip_does_not_leave_staging_file(self):
        year_dir = self.raw_dir / "2017"
        year_dir.mkdir(parents=True)
        (year_dir / "csv_pca.zip").write_bytes(b"not a zip file")
        with self.assertRaises(zipfile.BadZipFile):
            stage_local_raw(self.raw_dir, 2017, self.dest)
        target_dir = self.dest / "2017" / "1-Year"
        self.assertFalse(list(target_dir.glob("*.staging")))

    def test_staging_rejects_file_without_required_columns(self):
        year_dir = self.raw_dir / "2017"
        write_synthetic_pums_csv(year_dir / PUMS_CSV_NAME[2017], drop="ADJINC")
        with self.assertRaises(KeyError):
            stage_local_raw(self.raw_dir, 2017, self.dest)
        self.assertFalse((self.dest / "2017" / "1-Year" / PUMS_CSV_NAME[2017]).exists())

    def test_staging_rejects_header_only_file(self):
        year_dir = self.raw_dir / "2017"
        write_synthetic_pums_csv(year_dir / PUMS_CSV_NAME[2017], rows=0)
        with self.assertRaises(ValueError):
            stage_local_raw(self.raw_dir, 2017, self.dest)


class TestRuntimeEnvWriter(unittest.TestCase):
    """The generated runtime block must never erase hand-written environment history."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "ENV.md"
        self.path.write_text("# M0.1 environment status\n\nHand-written history.\n", encoding="utf-8")

    def test_first_run_appends_block_and_keeps_history(self):
        write_runtime_env(self.path, "- Python: 3.13.5")
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("Hand-written history.", text)
        self.assertIn(ENV_BEGIN, text)
        self.assertIn("- Python: 3.13.5", text)

    def test_second_run_replaces_block_without_duplicating(self):
        write_runtime_env(self.path, "- Python: 3.13.5")
        write_runtime_env(self.path, "- Python: 3.13.6")
        text = self.path.read_text(encoding="utf-8")
        self.assertEqual(text.count(ENV_BEGIN), 1)
        self.assertEqual(text.count(ENV_END), 1)
        self.assertIn("Hand-written history.", text)
        self.assertIn("- Python: 3.13.6", text)
        self.assertNotIn("- Python: 3.13.5", text)

    def test_marker_mentioned_in_prose_is_not_a_block_delimiter(self):
        self.path.write_text(
            "# M0.1 environment status\n\n"
            f"A generated block, delimited by `{ENV_BEGIN}` and `{ENV_END}`, holds the runtime record.\n"
            "Second hand-written paragraph.\n",
            encoding="utf-8",
        )
        write_runtime_env(self.path, "- Python: 3.13.5")
        write_runtime_env(self.path, "- Python: 3.13.6")
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("Second hand-written paragraph.", text)
        self.assertIn("- Python: 3.13.6", text)
        self.assertNotIn("- Python: 3.13.5", text)
        self.assertEqual(text.count(f"{ENV_BEGIN}\n- Run") + text.count(f"{ENV_BEGIN}\n- Python"), 1)

    def test_duplicated_marker_lines_append_instead_of_destroying_history(self):
        self.path.write_text(
            f"{ENV_BEGIN}\n- stale\n{ENV_END}\n\nHand-written after the block.\n"
            f"{ENV_BEGIN}\n- second stray block\n{ENV_END}\n",
            encoding="utf-8",
        )
        write_runtime_env(self.path, "- Python: 3.13.5")
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("Hand-written after the block.", text)
        self.assertIn("- stale", text)
        self.assertIn("- Python: 3.13.5", text)

    def test_block_can_be_replaced_inside_existing_history(self):
        write_runtime_env(self.path, "- Python: 3.13.5")
        self.path.write_text(
            self.path.read_text(encoding="utf-8") + "\nLater hand-written note.\n", encoding="utf-8"
        )
        write_runtime_env(self.path, "- Python: 3.13.7")
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("Later hand-written note.", text)
        self.assertIn("- Python: 3.13.7", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
