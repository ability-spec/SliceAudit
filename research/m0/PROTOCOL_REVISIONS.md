# M0 protocol revision before M0.2

**Status: proposed revision; not frozen.** This document supersedes the corresponding statistical and data-handling paragraphs in the draft roadmap until owner review. It does not authorize access to discovery or confirmation data.

## 1. Data-access firewall

1. Assign every raw PUMS household to a split using only `SERIALNO` and the preregistered SHA-256 salt.
2. For 2017, assign household buckets 50% train, 10% validation, 20% discovery, and 20% confirmation. These are household-level assignment targets, not guaranteed person-level proportions.
3. For M0.1, run the Folktables task filter and `ACSIncome.df_to_pandas` only on 2017 train/validation raw rows. Do not inspect labels, features, missingness, cardinality, code sets, or record-level summaries for discovery/confirmation.
4. For 2016, assign 50% train, 10% validation, and 40% unused at household level. Report eligible person counts on train/validation for both years.
5. Before M0.2 model fitting, deterministically downsample the larger eligible training cohort by whole households to match the smaller eligible person count as closely as possible. Apply analogous matching to validation when thresholds are compared. Record the selected household IDs, person and household counts, and residual person-count difference.
6. `splits.parquet` stores only `year`, `SERIALNO`, `split`, and `household_hash`. Held-out split identities are fixed, but their contents remain sealed until the registered gates permit access.

The M0.1 task firewall is strict: only train/validation rows may enter Folktables task filtering, safe Parquet artifacts, or task-level descriptive summaries. Do not materialize held-out task rows during M0.1.

## 2. Cluster-aware confirmation

The observational unit is a person, but people sharing `SERIALNO` are not assumed independent.

- Per-person paired outcome difference: d_i = 1[pred_v2_i = y_i] - 1[pred_v1_i = y_i].
- For slice S, the target is the person-weighted mean paired difference: Delta_S = sum(d_i for i in S) / n_S.
- **Primary confirmatory candidate:** a cluster-robust Wald t-test for H1: Delta_S < 0. For each household g represented in S, define U_g as the sum of paired correctness differences in that household and n_g as the number of people in S in that household. Estimate Delta_S = sum(U_g) / sum(n_g), with ratio-estimator cluster sandwich variance
  V = [G/(G-1)] * sum_g[(U_g - Delta_S*n_g)^2] / [sum_g(n_g)]^2
  and a one-sided t reference with G-1 degrees of freedom.
- **Mandatory calibration:** compare the candidate test against a null-restricted household wild-cluster-bootstrap-t test with Rademacher weights and at least 9,999 draws. Use cluster score residuals U_g - Delta_S*n_g, impose the null, studentize each replicate, and calculate a one-sided lower-tail p-value with the plus-one correction. Exact null imposition, studentization, finite-sample correction, RNG seed, and cluster ordering must be frozen before G0.
- If null simulations show size inflation, do not ship the method or claim confirmation. Revise and recalibrate before opening held-out data.
- **Primary interval:** household-cluster bootstrap CI for person-weighted Delta_S, resampling whole households with all people and paired outcomes. Validate coverage in simulations.
- Exact person-level McNemar may be reported only as a clearly labelled sensitivity statistic, not as the confirmatory p-value.
- Apply Holm correction to the prespecified confirmation family (all selected slices across S-A and S-B, maximum six under the current design), using cluster-aware p-values. Keep alpha_attempt = 0.05/A.
- Discovery and permutation screening must respect household clustering and state the exchangeability/symmetry null. Screening remains contextual, not confirmatory, unless separately validated.
- The 30-cluster minimum is provisional; keep it as an owner/reviewer TODO until simulations and design review justify it.

Do not implement this method by aggregating person counts and passing them to `scipy.stats.binomtest`. That still assumes people in a household are independent.

## 3. Comparable training sample sizes

The old 2016 85% / 15% train/validation assignment can create a training-volume confound. The revised assignment is 50% / 10% / 40% train/validation/unused in 2016, matching the 2017 train/validation shares. After task filtering, compare eligible person counts. Before fitting S-A, deterministically subsample the larger training year by whole households to the smaller year's eligible person count as closely as possible. Freeze and hash the selected household list. Record actual person and household counts. Do not interpret S-A as a clean year update if training sizes remain materially unequal without a preregistered sensitivity analysis.

## 4. Target-dollar estimand

The primary target remains the standard Folktables nominal-dollar definition, y = 1[PINCP > 50000], with the standard ACSIncome eligibility filter. This is a nominal threshold, not a constant-purchasing-power threshold. S-A therefore includes year-to-year changes in nominal purchasing power as part of the temporal data shift. Reports must state this and must not describe the target as real-income-comparable across years.

Before G0, the owner must decide whether to include a secondary constant-dollar sensitivity using Census `ADJINC` and one explicitly named reference year. Do not improvise the conversion after viewing discovery/confirmation. The primary run must retain exact Folktables ACSIncome semantics.

## 5. Threshold estimand

Each model's threshold is selected independently on its own validation set. The primary estimand therefore compares versioned deployed pipelines (model plus threshold-selection procedure), not model parameters in isolation. Add a fixed-common-threshold sensitivity on validation only if the owner elects to isolate model-score changes. Name the estimands distinctly in all reports.

## 6. Retraining-noise qualification

`p_churn` comparing v2 to v1 retrains measures v2 relative to variability in the v1 training procedure; it is not automatically a two-sample test between exchangeable model generations. Keep it secondary/sensitivity until calibrated under both the null and realistic drift scenarios. S-B remains descriptive because changing model family is not ordinary retraining noise.

## 7. Claims and survey weights

Primary claims concern the held-out PUMS sample, not the US population. Do not make population-representative claims from unweighted metrics. `PWGTP` may support a preregistered weighted sensitivity only. Any population inference requires the PUMS replicate-weight/design framework and a revised estimand and uncertainty method.

## 8. Owner decisions required before G0

- delta: minimum practical regression worth stopping a release for.
- n_floor, k, eligible slice features, and model input feature set.
- Whether constant-dollar sensitivity is in scope and its reference-year convention.
- Whether fixed-common-threshold sensitivity is in scope.
- Wild-cluster-bootstrap finite-sample implementation, RNG contract, minimum cluster count, and simulation acceptance criteria.
