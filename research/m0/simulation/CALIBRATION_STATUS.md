# SliceAudit M0 simulation calibration status

**As of 2026-11-15. Status: screening only; Simulation Gate remains NOT PASSED.**

All work below is synthetic-only. No ACS PUMS, Folktables, discovery/confirmation partition, fitted model, or model prediction was loaded.

## Implemented and checked

- Paired-outcome DGP with household clustering and variable household-size profiles.
- IID diagnostic, CR1, CR2/Satterthwaite, null-restricted wild-cluster-bootstrap-t candidate, whole-household bootstrap intervals, weighted secondary point estimate, and Holm adjustment.
- Fixed-family overlapping-slice complete-null runner and independent discovery-selection/confirmation replay.
- 37 unit tests pass locally, including randomized CR2 matrix-reference checks and partial-null mean/ICC calibration tests.

## Main screening results

- Fixed-family overlapping-slice baseline (G=300, ICC 0.15, overlap 0.5, moderate size): **5,000 repetitions**, FWER **3.30%**, exact 95% interval **2.82%–3.83%**. The wider 11-cell fixed-family grid has 500 repetitions per cell; several upper Monte Carlo bounds exceed 5.5%.
- Independent-selection complete-null replay (G=300): **500 repetitions**, FWER **3.0%**, exact 95% interval **1.69%–4.90%**.
- Independent-selection partial-null replay (G=300; three null and three -2 pp alternative slice means per scenario): **800 repetitions**, strong FWER **2.375%**, exact 95% interval **1.44%–3.68%**.
- Power after selection and Holm: at G=300, **16.5%** chance of at least one selected alternative rejection (400-repetition substudy; interval 13.0%–20.5%); at G=500, **27%** (100 reps; 18.6%–36.8%); at G=1,000, **35%** (100 reps; 25.7%–45.2%). At G=100, n_floor=200 excluded all candidates, so no family-level power was estimable. These points are exploratory, not a power curve; per-selected-alternative rejection rates were 6.47%, 11.35%, and 14.10% for G=300/500/1,000 respectively.

The partial-null generator uses one common paired outcome per person and solves a household-mean surface for exact marginal slice targets. The household Dirichlet concentration is calibrated to the requested unconditional scalar paired-difference ICC. A 5,000-household diagnostic observed within-household ICC 0.137 for a 0.15 target; finite-sample variation remains.

## Remaining gates

1. No method has passed the Simulation Gate. Do not open discovery/confirmation or start M0.2.
2. Complete independent package-level CR2 verification and freeze the wild-cluster-bootstrap finite-sample contract.
3. Expand partial-null, power, and coverage cells across ICC, overlap, household sizes, and sample sizes; run at least 20,000 repetitions in every critical final cell.
4. Use train/validation only to estimate realistic household-size design inputs; never tune the simulation from held-out outcomes.
5. Keep ACS PWGTP replicate weights distinct from household-cluster resampling; no population-inference claims until the SDR framework is separately implemented and validated.

Source code and detailed synthetic outputs are preserved in the companion local package. The repository contains these status reports; not all local runner sources and result JSONs have been pushed into this branch.
