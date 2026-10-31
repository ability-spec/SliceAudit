"""Synthetic ManimGX render test: 1,000 cells, with illustrative corrected/broken flips."""

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
from pathlib import Path

import manimgx as m

FIXTURE = json.loads(Path(__file__).with_name("fixture.json").read_text(encoding="utf-8"))


class SliceAuditGridPoC(m.Scene):
    def construct(self) -> None:
        rows = int(FIXTURE["rows"])
        cols = int(FIXTURE["cols"])
        corrected = set(int(x) for x in FIXTURE["corrected_indices"])
        broken = set(int(x) for x in FIXTURE["broken_indices"])

        title = m.Text("SliceAudit · 1,000 paired examples", font_size=34)
        title.to_edge(m.UP, buff=0.32)
        subtitle = m.Text("SYNTHETIC FIXTURE — illustrative flips only", font_size=19, color=m.YELLOW)
        subtitle.next_to(title, m.DOWN, buff=0.12)

        side = 0.115
        x_gap = 0.025
        y_gap = 0.07
        x0 = -((cols - 1) * (side + x_gap)) / 2
        y0 = ((rows - 1) * (side + y_gap)) / 2 - 0.2
        cells = []
        for idx in range(rows * cols):
            r, c = divmod(idx, cols)
            cell = m.Square(side_length=side, stroke_width=0.35, color=m.GREY_B)
            cell.set_fill(m.GREY_E, opacity=0.9)
            cell.move_to([x0 + c * (side + x_gap), y0 - r * (side + y_gap), 0])
            cells.append(cell)
        grid = m.VGroup(*cells)

        legend = m.VGroup(
            m.Text("Corrected", font_size=20, color=m.GREEN),
            m.Text("Broken", font_size=20, color=m.RED),
            m.Text("Unchanged", font_size=20, color=m.GREY_B),
        ).arrange(m.RIGHT, buff=0.55)
        legend.to_edge(m.DOWN, buff=0.3)

        self.add(title, subtitle, grid, legend)
        self.wait(0.5)
        self.play(
            *[cells[i].animate.set_fill(m.GREEN, opacity=1) for i in sorted(corrected)],
            run_time=1.2,
        )
        self.play(
            *[cells[i].animate.set_fill(m.RED, opacity=1) for i in sorted(broken)],
            run_time=1.2,
        )
        self.wait(1.0)
