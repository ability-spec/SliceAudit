# Third-party notices

This file is a project-level inventory of direct dependencies and external data sources. It is not a complete Software Bill of Materials (SBOM). The installed distributions, their transitive dependencies, and platform-specific wheels may contain additional components and license texts. Preserve the notices shipped with the exact versions you install or redistribute.

Nothing in the SliceAudit LICENSE relicenses third-party software or data.

## Direct Python dependencies

The packages below are declared in `pyproject.toml`. Their own licenses continue to apply independently of SliceAudit's Apache-2.0 license.

| Dependency | Upstream project license | Role in SliceAudit |
| --- | --- | --- |
| [NumPy](https://github.com/numpy/numpy) | BSD 3-Clause for the NumPy project; binary wheels may include separately licensed bundled libraries | Numerical operations |
| [SciPy](https://github.com/scipy/scipy) | BSD | Scientific and statistical routines |
| [pandas](https://github.com/pandas-dev/pandas) | BSD 3-Clause | Data preparation and tabular analysis |
| [PyArrow](https://github.com/apache/arrow) | Apache License 2.0 | Parquet I/O |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | BSD 3-Clause | Planned model implementation |
| [Folktables](https://github.com/socialfoundations/folktables) | MIT | ACS task definitions and data loading |

Before redistributing a built environment or application, inspect the exact wheel and transitive dependency notices for the target platform. For example, NumPy wheels can bundle numerical libraries under licenses additional to the NumPy project's BSD license.

## Optional renderer: ManimGX

ManimGX is an optional dependency in the `render` extra; it is not vendored in this repository. The current dependency declaration is a lower bound (`manimgx>=0.1.1`), not an exact pin, so the license details below are a version-specific note and must be rechecked against the installed release before distributing a renderer.

For ManimGX 0.1.1, the project describes its own code as MIT-licensed. Its native wheels include x264 and are GPL-3.0-or-later as a whole; they also include FFmpeg code under LGPL-2.1-or-later. Bundled fonts and other components retain their own licenses. The browser wheel is an exception to the x264 inclusion described by the maintainers. See the [ManimGX 0.1.1 release page](https://pypi.org/project/manimgx/0.1.1/) and [upstream release notes](https://github.com/academa-labs/manimgx/releases/tag/v0.1.1) for the exact distribution details and bundled notices.

The Apache-2.0 license for SliceAudit does not change any of these ManimGX or bundled-component terms. Do not assume that redistributing a native ManimGX wheel is the same as redistributing SliceAudit's Python source.

## ACS PUMS data

M0.1 uses California American Community Survey (ACS) Public Use Microdata Sample (PUMS) files for 2016 and 2017. Folktables provides code for downloading and processing ACS PUMS, but its maintainers explicitly state that the data itself is governed by the U.S. Census Bureau's terms of use.

- [U.S. Census Bureau ACS PUMS documentation](https://www.census.gov/programs-surveys/acs/microdata.html)
- [U.S. Census Bureau terms of service](https://www.census.gov/data/developers/about/terms-of-service.html)
- [Folktables license and data terms](https://github.com/socialfoundations/folktables#license-and-terms-of-use)

The SliceAudit Apache-2.0 license applies to SliceAudit-authored code, documentation, and synthetic fixtures. It does **not** grant rights over ACS PUMS source files or derivative datasets. Raw PUMS files and generated data artifacts are kept outside version control by the repository's `.gitignore`. Anyone who redistributes source data or derived outputs must independently review the applicable Census terms and documentation; do not infer a data license from this repository's code license.

## Academic citation

When using Folktables or the ACSIncome task, consult the Folktables project and cite the paper introducing the datasets:

Ding, Frances, Moritz Hardt, John Miller, and Ludwig Schmidt. “Retiring Adult: New Datasets for Fair Machine Learning.” *Advances in Neural Information Processing Systems*, 2021.

- [Folktables repository and citation guidance](https://github.com/socialfoundations/folktables)

## Release checklist

Before publishing a package, container, rendered executable, or other bundled distribution:

1. Record exact direct and transitive dependency versions.
2. Preserve each distribution's LICENSE, NOTICE, and bundled-component notices.
3. Recheck the selected ManimGX release and platform wheel, if the renderer is included.
4. Keep ACS PUMS data outside the software package unless its applicable terms have been reviewed for the intended redistribution.
