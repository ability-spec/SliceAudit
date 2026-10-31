"""Dependency-light tests for household splits and the M0.1 data firewall."""
from __future__ import annotations

import hashlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare_m0 import (  # noqa: E402
    FEATURES,
    SALT,
    assign_household_splits,
    assert_no_household_leakage,
    describe_safe_partition,
    household_digest,
)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
