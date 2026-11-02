# SliceAudit

**Find model-update regressions that aggregate metrics can hide.**

SliceAudit is an early-stage research prototype for paired comparisons of two model versions on the same examples. Its narrow question is:

> Did a model update improve the overall score while making a particular, prespecified slice meaningfully worse?

The intended workflow separates slice discovery from independent confirmation, applies multiplicity-aware inference, records the evidence behind every reported result, and optionally turns that evidence into a ManimGX animation. The renderer is an optional presentation layer; the statistical core must not depend on ManimGX.

<p><img src="docs/logo.svg" alt="SliceAudit logo" width="88" height="88" /></p>

## A hidden regression, in 40 seconds

![Animated explainer: the overall score improves while the orange group gets worse](docs/sliceaudit-demo.svg)

*This is a synthetic 10-example illustration, not an empirical SliceAudit result or a ManimGX render. The underlying examples and expected totals live in [`docs/demo_fixture.json`](docs/demo_fixture.json), and CI checks that the animation's numbers match the fixture. The final card illustrates the independent re-check step; it does not claim that a confirmation test has passed. Browsers with reduced-motion enabled show a static summary instead of the animation.*

## Project status

<small>Research prototype — M0.1 data audit complete. No model comparison results are claimed.</small>

The M0.1 data and split audit completed on 2026-11-01 using operator-supplied California ACS PUMS 2016 and 2017 archives in fully offline mode. The safe ACSIncome artifacts contain 190,187 eligible train/validation people for 2016 and 116,092 for 2017. Source and artifact SHA-256 values are recorded, but the local archives were not verified against upstream Census checksums. See [`research/m0/01_data_report.md`](research/m0/01_data_report.md) for findings and limitations, and [`research/m0/ENV.md`](research/m0/ENV.md) for the dated execution history.

No model has been trained, no discovery or confirmation metrics have been calculated, and no ManimGX video has been rendered. The animation fixture is synthetic and labelled accordingly. M0.1 validates data preparation only; it does not yet validate SliceAudit's hidden-regression detection method.

## Design principles

1. **Paired comparison:** compare versioned predictions on the same held-out examples.
2. **Discovery is not confirmation:** select candidate slices on one partition and test them on an independent confirmation partition.
3. **Cluster-aware data boundaries:** split at household level before task filtering, and never let a household cross partitions.
4. **Inference before storytelling:** uncertainty, multiplicity, and retraining variability must be handled before a regression is described as credible.
5. **Evidence-linked visuals:** an animation may display only values contained in a machine-readable evidence record.
6. **Optional renderer:** core data and statistics code must remain usable without ManimGX.

## Repository map

```text
research/m0/
  PROTOCOL_REVISIONS.md   Statistical and data-firewall decisions required before M0.2
  prereg.yaml             Preregistration draft; unresolved owner decisions remain TODOs
  prepare_m0.py           Household split, safe-partition audit, Parquet manifest, report
                          (Census download by default, --raw-dir for a fully offline run)
  test_split_logic.py     Determinism, household isolation, held-out filter guard, offline staging, ENV history
  01_data_report.md       Audit findings, checks, provenance, and limitations
  ENV.md                  Dated execution history plus the generated runtime block

docs/
  logo.svg                SliceAudit mark (blue pie, orange slice)
  sliceaudit-demo.svg     Animated synthetic explainer shown near the top of this README
  demo_fixture.json       Ten synthetic paired examples behind the explainer
  validate_demo_fixture.py Checks fixture arithmetic and SVG accessibility/reduced-motion fallback

manimgx_poc/
  fixture.json            Synthetic paired-flip fixture
  scene.py                1,000-cell ManimGX layout/render smoke test
  README.md               Renderer setup and acceptance checklist
  RESULTS.md              Explicitly records that rendering has not run yet
```

## M0.1: run the data and split audit

Requires Python 3.13 and `uv` on a machine that can access PyPI and the Census PUMS source.

```powershell
uv sync --python 3.13
uv run python research/m0/test_split_logic.py
uv run python research/m0/prepare_m0.py
```

If Census access is unavailable but the two PUMS archives were downloaded elsewhere, run the
same audit fully offline:

```powershell
uv run python research/m0/prepare_m0.py --raw-dir C:\pums
```

`C:\pums\2016\csv_pca.zip` and `C:\pums\2017\csv_pca.zip` (both years share the Census file
name), or the already-extracted `ss16pca.csv` / `psam_p06.csv`. Offline mode never touches the
network: it validates each file, stages it under the exact name Folktables expects, and records
its SHA-256 in `split_manifest.json`, `ENV.md`, and `01_data_report.md`. It does not verify the
files against an upstream checksum, so the operator is responsible for the download.

The preparation script assigns households using a salted SHA-256 hash of `SERIALNO` before applying the Folktables task filter. Raw PUMS data is either downloaded by Folktables or staged from the exact Census archives supplied with `--raw-dir`; only train/validation rows are passed into `adult_filter`, `ACSIncome.df_to_pandas`, or task-level diagnostic summaries. Offline staging accepts only the expected year-specific CSV or `csv_pca.zip` containing that exact CSV member. Discovery and confirmation feature/outcome values are not analyzed at M0.1.

The script writes a household split manifest and checksum, train/validation-only ACSIncome Parquet datasets for each year (with SERIALNO, SPORDER, PWGTP, ST, ADJINC, split, features, and target), checksums for those datasets, a runtime copy of the Folktables task definition, an environment record, and a train/validation-only report. It intentionally fails if Folktables or PyArrow is missing; it does not substitute another dataset or silently fall back to CSV.

## ManimGX proof of concept

ManimGX is kept out of the statistical environment. Follow [`manimgx_poc/README.md`](manimgx_poc/README.md) to create a separate Python 3.13 environment, inspect the synthetic scene, and test 720p30 and 1080p60 rendering. Record actual command output and resource use in `manimgx_poc/RESULTS.md`. Do not describe the synthetic fixture as an empirical result.

## Research gate

Do not start model training (M0.2) until the protocol and owner decisions in `prereg.yaml` have been reviewed, the preregistration is frozen, and the registered confirmation and interval-coverage checks have been validated. The current draft is a research plan, not a validated statistical method or production monitoring system.

## Sources

See [`SOURCES.md`](SOURCES.md) for upstream task, data, and ManimGX documentation. Those sources support dataset/tooling details only; they do not prove novelty or validate SliceAudit's statistical method.

## License and third-party materials

SliceAudit-authored source code, documentation, and the synthetic ManimGX fixture in this repository are licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Third-party dependencies retain their own licenses; they are not relicensed under Apache-2.0 by this repository. ACS Public Use Microdata Sample (PUMS) data and any derived data artifacts are also outside this project's code license and remain subject to the applicable U.S. Census Bureau terms. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) before redistributing software, data, or rendered binaries.
