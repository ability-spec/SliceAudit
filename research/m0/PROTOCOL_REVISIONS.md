# SliceAudit M0 protocol — required revisions before M0.2

Status: **proposed revision; not frozen**. This file supersedes the corresponding statistical and data-handling paragraphs in the draft roadmap until owner review.

## 1. Data-access firewall (new hard rule)

1. Assign every raw PUMS household to a split using only `SERIALNO` and a preregistered SHA-256 salt.
2. For 2017, the hash buckets are train 50%, validation 10%, discovery 20%, confirmation 20% **at household level**. The proportions are assignment targets over households, not guaranteed person-level proportions.
3. For M0.1, run the Folktables task filter and `ACSIncome.df_to_pandas` only on the 2017 train/validation raw rows. Do not inspect labels, features, missingness, cardinality, code sets, or record-level summaries for discovery/confirmation.
4. For 2016, use train 50%, validation 10%, unused 40% household buckets. Report the actual eligible person counts on train/validation and the difference from 2017. Before M0.2, deterministically downsample the larger training cohort at household level to match the smaller eligible person count as closely as whole households permit. Do the analogous matching for validation when thresholds are compared. Record any residual difference.
5. `splits.parquet` stores only `year`, `SERIALNO`, `split`, and `household_hash`; do not materialize held-out task rows in M0.1. The held-out split identities are fixed, but their contents remain sealed.

This replaces the draft's proposed full-dataset `ACSIncome.df_to_pandas` count check in M0.1. Calling that function on all 2017 rows would construct labels on discovery and confirmation, contradicting the stated firewall. The M0.1 equality check is therefore performed on train/validation only. Full held-out checks happen only after G0/G1 as defined in the protocol.

## 2. Cluster-aware confirmation

The observational unit for the task remains a person, but people sharing `SERIALNO` are not assumed independent.

- Per-person paired outcome difference: `d_i = 1[pred_v2_i == y_i] - 1[pred_v1_i == y_i]`.
- For a slice S, the target is the person-weighted mean paired difference `Delta_S = sum_{i in S} d_i / n_S`.
- **Primary confirmatory test (candidate specification to validate before G0):** use a cluster-robust Wald t-test for `H1: Delta_S < 0`. For each household g represented in S, set `U_g = sum_{i in S,g} d_i` and `n_g = number of people in S in household g`; estimate `Delta_S = sum(U_g) / sum(n_g)`. Use the ratio-estimator cluster sandwich variance `V = [G/(G-1)] * sum_g[(U_g - Delta_S*n_g)^2] / [sum_g(n_g)]^2`, and a one-sided t reference with `G-1` degrees of freedom. This explicitly treats households, not people, as the independent clusters.
- **Mandatory calibration:** compare the candidate test against a null-restricted household wild-cluster-bootstrap-t test with Rademacher weights and at least 9,999 draws (minimum Monte Carlo p resolution 0.0001). The bootstrap must use cluster score residuals `U_g - Delta_S*n_g`, impose the null, studentize each replicate, and use a one-sided lower-tail p-value with the plus-one correction. Exact implementation and finite-sample decisions must be frozen before G0. If null simulations show size inflation, do not ship the method or claim confirmation; revise the method before opening held-out data.
- **Primary interval:** household-cluster bootstrap CI for person-weighted `Delta_S`, resampling whole households with all people and paired v1/v2 outcomes. Validate coverage in simulations.
- Exact person-level McNemar may be reported only as a clearly labelled sensitivity statistic; it is not the confirmatory p-value.
- Holm correction is applied to the prespecified confirmation family (all selected slices across S-A and S-B, maximum six), using the cluster-aware p-values. `alpha_attempt = 0.05 / attempt_index` remains.
- Discovery and permutation screening must also respect the household cluster. Any sign-flip test at cluster level must state its exchangeability/symmetry null; it is screening only unless separately validated for the estimand.
- The 30-cluster minimum is a provisional guardrail; make it `TODO(owner/reviewer)` until simulations and design review justify the final minimum.

M1 must not implement this method by merely aggregating person counts and passing them to `scipy.stats.binomtest`. That would still treat people in the same household as independent.

## 3. Comparable training sample sizes

The previous 2016 85% / 2017 50% training split can create a large training-volume confound. The revised raw household assignment uses 50% train and 10% validation in both years (2017 additionally has discovery/confirmation). After task filtering, compare eligible person counts. Before fitting S-A, deterministically subsample the larger training year by whole households to the smaller year's eligible person count as closely as possible. Freeze and hash the selected household list. Report actual person and household counts. Do not compare S-A as a clean “year update” if the train sizes are left materially unequal without a preregistered sensitivity analysis.

## 4. Target-dollar estimand

Primary target remains the standard Folktables nominal-dollar definition: `y = 1[PINCP > 50000]`, with the standard task's adult/work/income eligibility filter. This is a **nominal threshold**, not a constant-purchasing-power threshold. Therefore S-A intentionally includes any year-to-year change in the nominal target definition / purchasing power as part of the temporal data shift. The report must say this explicitly and must not describe the target as real-income-comparable across years.

Before G0, the owner must choose whether to include a secondary constant-dollar sensitivity using the Census `ADJINC` factor and a single explicitly named reference year. Do not improvise the inflation conversion after viewing discovery/confirmation. The primary run must preserve exact Folktables ACSIncome semantics for benchmark comparability.

## 5. Threshold estimand

The current design selects each model's decision threshold independently on its own validation set. Therefore the primary estimand compares **versioned deployed pipelines** (model + threshold selection procedure), not model parameters in isolation. Add a fixed-common-threshold sensitivity on validation only if the owner wants to isolate model-score changes. Both estimands must be named distinctly in all reports.

## 6. Retraining-noise qualification

`p_churn` comparing v2 to a distribution of v1 retrains is a comparison to the variability of the v1 training procedure, not automatically a two-sample test between exchangeable model generations. Keep it secondary/sensitivity until calibration is demonstrated under both the null and realistic drift scenarios. S-B remains descriptive because changing model family is not “ordinary retraining noise.”

## 7. Claims and survey weights

The primary claims concern the held-out PUMS sample, not the US population. Do not make population-representative claims from unweighted metrics. `PWGTP` may support a preregistered weighted sensitivity only; if population inference is later attempted, incorporate the PUMS replicate-weight/design framework and revise the estimand and uncertainty method first.

## Decisions still required from owner before G0

- `delta` (minimum practical regression worth stopping a release for).
- `n_floor`, `k`, eligible slice features, and feature/model input set.
- Whether constant-dollar sensitivity is in scope and its reference-year convention.
- Whether fixed-common-threshold sensitivity is in scope.
- Wild-cluster-bootstrap implementation details and simulation acceptance criteria (must be reviewed before G0).
