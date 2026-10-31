# M0 protocol compliance note

**The user-supplied SliceAudit engineering roadmap is authoritative.** This note records implementation boundaries; it does not amend the research protocol.

## M0.1 rules to preserve

- Use `ACSDataSource(survey_year=..., horizon="1-Year", survey="person")` for California PUMS 2016 and 2017.
- Assign households before task filtering with SHA-256 of the direct concatenation `salt + SERIALNO` (no delimiter).
- 2017 household buckets: train 50%, validation 10%, discovery 20%, confirmation 20%.
- 2016 household buckets: train 85%, validation 15%.
- Apply the Folktables task filter and descriptive task summaries only to train/validation at M0.1. Discovery and confirmation receive only raw household split assignments; do not inspect their labels/features or compute metrics.
- Preserve `SERIALNO`, `PWGTP`, and `ST`; retain `SPORDER` and `ADJINC` where available.
- Compare train/validation OCCP and POBP code sets across years; report row counts, positive-class share, missingness, feature cardinality, and household-size distribution.
- Save household assignments as `splits.parquet` with its SHA-256 checksum. Test household isolation and row-order invariance.
- If Folktables does not install or work on Python 3.13, stop and report the error. Do not silently substitute Python 3.12, OpenML, or a hand-written task implementation.

## Statistical protocol precedence

The original roadmap remains binding for later M0 stages. Discovery uses `z_S = (C_S - B_S) / sqrt(D_S)`, household-level sign-flip screening with `P=2000`, and selection of up to `k=3` slices per scenario. Confirmation uses exact one-sided McNemar with Holm correction over the selected S-A/S-B family. The roadmap explicitly documents the independence assumption for person-level McNemar despite household clustering; this note does not replace the specified test with a different confirmatory procedure.

Confidence intervals, `K=199` retraining-noise analysis, attempt accounting, and G0-G2 gates remain as defined in the original roadmap. Owner-controlled values (`delta`, `n_floor`, eligible slice features, and model inputs) remain unresolved until explicit review.
