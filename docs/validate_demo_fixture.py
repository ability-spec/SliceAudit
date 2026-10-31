"""Validate the README explainer against its synthetic, machine-readable fixture."""

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

import json
import xml.etree.ElementTree as ET
from pathlib import Path

DOCS = Path(__file__).resolve().parent


def main() -> int:
    fixture = json.loads((DOCS / "demo_fixture.json").read_text(encoding="utf-8"))
    examples = fixture["examples"]
    if fixture.get("provenance") != "SYNTHETIC_ILLUSTRATION_NOT_MEASURED":
        raise AssertionError("Demo fixture must be explicitly marked synthetic")
    if len(examples) != 10:
        raise AssertionError(f"Expected 10 synthetic examples, got {len(examples)}")

    ids = [row["id"] for row in examples]
    if len(set(ids)) != len(ids):
        raise AssertionError("Demo example IDs must be unique")
    if any(row["group"] not in {"orange", "everyone_else"} for row in examples):
        raise AssertionError("Fixture contains an unknown group")
    for row in examples:
        for key in ("truth", "old_prediction", "new_prediction"):
            if row[key] not in (0, 1):
                raise AssertionError(f"{row['id']}: {key} must be binary")

    def correct(rows: list[dict], prediction_key: str) -> int:
        return sum(row[prediction_key] == row["truth"] for row in rows)

    orange = [row for row in examples if row["group"] == "orange"]
    everyone_else = [row for row in examples if row["group"] == "everyone_else"]
    old_correct = correct(examples, "old_prediction")
    new_correct = correct(examples, "new_prediction")
    fixed = sum(
        row["old_prediction"] != row["truth"] and row["new_prediction"] == row["truth"]
        for row in examples
    )
    broken = sum(
        row["old_prediction"] == row["truth"] and row["new_prediction"] != row["truth"]
        for row in examples
    )
    calculated = {
        "all_examples": {
            "count": len(examples),
            "old_correct": old_correct,
            "new_correct": new_correct,
        },
        "orange_group": {
            "count": len(orange),
            "old_correct": correct(orange, "old_prediction"),
            "new_correct": correct(orange, "new_prediction"),
        },
        "everyone_else": {
            "count": len(everyone_else),
            "old_correct": correct(everyone_else, "old_prediction"),
            "new_correct": correct(everyone_else, "new_prediction"),
        },
        "transitions": {
            "fixed": fixed,
            "broken": broken,
            "net_change": fixed - broken,
        },
    }
    if calculated != fixture["expected_summary"]:
        raise AssertionError(
            f"Fixture summary mismatch. Expected {fixture['expected_summary']}; got {calculated}"
        )
    if len(orange) != 4 or len(everyone_else) != 6:
        raise AssertionError("SVG layout expects four orange and six other examples")

    svg_root = ET.parse(DOCS / "sliceaudit-demo.svg").getroot()
    logo_root = ET.parse(DOCS / "logo.svg").getroot()
    if svg_root.attrib.get("viewBox") != "0 0 1280 720":
        raise AssertionError("Demo SVG canvas changed unexpectedly")
    if logo_root.attrib.get("viewBox") != "0 0 200 200":
        raise AssertionError("Logo SVG viewBox changed unexpectedly")

    svg_text = " ".join(node.strip() for node in svg_root.itertext() if node.strip())
    required = (
        "4/4", "2/4", "7/10", "8/10",
        "3 people got fixed.", "2 got broken.",
        "RECHECK", "Synthetic illustration",
    )
    for label in required:
        if label not in svg_text:
            raise AssertionError(f"Demo SVG missing expected label: {label}")

    styles = " ".join(node.text or "" for node in svg_root.iter() if node.tag.endswith("style"))
    media_start = styles.find("@media (prefers-reduced-motion: reduce)")
    media_end = styles.find(chr(10) + "}", media_start) if media_start >= 0 else -1
    reduced_rule = styles[media_start:media_end] if media_start >= 0 and media_end > media_start else ""
    if ".sx-reduced" not in reduced_rule or "display: block !important" not in reduced_rule:
        raise AssertionError("Reduced-motion users must receive the static summary panel")
    if "animation-play-state:paused" in styles:
        raise AssertionError("Do not freeze the full animation at an arbitrary partial frame")
    if fixture.get("confirmation_stage", {}).get("provenance") != "PROCESS_ILLUSTRATION_ONLY_NOT_TESTED":
        raise AssertionError("The independent re-check panel must not imply a measured confirmation result")
    if "CONFIRMED" in svg_text:
        raise AssertionError("The demo must not claim an uncomputed confirmation result")

    print(
        "README demo fixture valid: "
        f"all={old_correct}/{len(examples)}->{new_correct}/{len(examples)}, "
        f"orange={calculated['orange_group']['old_correct']}/{len(orange)}"
        f"->{calculated['orange_group']['new_correct']}/{len(orange)}, "
        f"fixed={fixed}, broken={broken}, net={fixed-broken}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
