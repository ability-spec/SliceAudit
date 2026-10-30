# SliceAudit

**Find model-update regressions that aggregate metrics can hide.**

SliceAudit is an early-stage research prototype for paired comparisons of two model versions on the same examples. Its narrow question is:

> Did a model update improve the overall score while making a particular, prespecified slice meaningfully worse?

The intended workflow separates slice discovery from independent confirmation, applies multiplicity-aware inference, records the evidence behind every reported result, and optionally turns that evidence into a ManimGX animation. The renderer is an optional presentation layer; the statistical core must not depend on ManimGX.

## Project status

<small>Research prototype — M0/M0.1 only. No model comparison results are claimed.</small>

The current work establishes a data and split audit for the ACSIncome task using California ACS PUMS 2016 and 2017 records. The real data download and Parquet export have **not** been completed in the current environment because package-index access was unavailable. See [`research/m0/01_data_report.md`](research/m0/01_data_report.md) and [`research/m0/ENV.md`](research/m0/ENV.md).

No model has been trained, no discovery or confirmation metrics have been calculated, and no ManimGX video has been rendered. The animation fixture is synthetic and labelled accordingly.

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
  test_split_logic.py     Determinism, household isolation, and held-out filter guard tests
  01_data_report.md       Honest record of what has and has not run
  ENV.md                 Environment status and reproduction instructions

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

The preparation script assigns households using a salted SHA-256 hash of `SERIALNO` before applying the Folktables task filter. Raw PUMS data is fetched so household membership can be assigned, but only train/validation rows are passed into `adult_filter`, `ACSIncome.df_to_pandas`, or task-level diagnostic summaries. Discovery and confirmation feature/outcome values are not analyzed at M0.1.

The script writes a household split manifest, its SHA-256 digest, a runtime copy of the Folktables task definition, an environment record, and a train/validation-only report. It intentionally fails if Folktables or PyArrow is missing; it does not substitute another dataset or silently fall back to CSV.

## ManimGX proof of concept

ManimGX is kept out of the statistical environment. Follow [`manimgx_poc/README.md`](manimgx_poc/README.md) to create a separate Python 3.13 environment, inspect the synthetic scene, and test 720p30 and 1080p60 rendering. Record actual command output and resource use in `manimgx_poc/RESULTS.md`. Do not describe the synthetic fixture as an empirical result.

## Research gate

Do not start model training (M0.2) until the protocol revisions have been reviewed, owner decisions in `prereg.yaml` are resolved, and the cluster-aware confirmation test has been calibrated by simulation. The current draft is a research plan, not a validated statistical method or production monitoring system.

## Sources

See [`SOURCES.md`](SOURCES.md) for upstream task, data, and ManimGX documentation. Those sources support dataset/tooling details only; they do not prove novelty or validate SliceAudit's statistical method.

## Licensing

No project-wide license has been selected yet. Until a `LICENSE` file is added, do not assume the repository grants permission to redistribute or reuse its code. The ManimGX optional dependency retains its own upstream license terms.
