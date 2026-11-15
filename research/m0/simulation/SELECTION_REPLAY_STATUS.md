# Discovery-selection and independent-confirmation replay

**Status: preliminary synthetic replay completed; overall simulation gate remains NOT PASSED.**

## Design

- Two scenarios, S-A and S-B, each with six candidate slices.
- Independent discovery and confirmation household samples.
- Discovery ranks eligible candidates by the most-negative CR2/Satterthwaite statistic.
- Greedy Jaccard selection skips a candidate when overlap with any selected slice is greater than 0.5; up to three slices are selected per scenario.
- Holm is applied once across the selected confirmation family, maximum six tests.
- Eligibility requires at least 200 people and a technical floor of 10 households. The 10-household floor is not an approved production rule.

## Complete-null replay

At G=300, ICC 0.15, latent overlap 0.5, and moderate household sizes, 500 repetitions produced **15 family rejections / 500 (3.0%)**, with exact binomial 95% interval **1.69%–4.90%**. Mean selected family size was 5.352.

## Partial-null strong-FWER replay

The partial-null DGP assigns three candidate slice means per scenario to -2 percentage points and the other three to exactly zero, using one common paired outcome per person across overlapping slices. A conditional mean surface is solved so the overall expected paired difference is zero and all six marginal slice means match their targets. The household-level Dirichlet concentration is algebraically calibrated to the requested unconditional scalar paired-difference ICC under heterogeneous household means.

Across six non-overlapping seed blocks (**800 total repetitions**), there were 19 replications with at least one false rejection among true-null selected tests: partial-null strong FWER **2.375%**, exact 95% interval **1.44%–3.68%**. Mean selected family size was 5.398. A pre-correction partial-null pilot was discarded after its concentration formula was found not to preserve the requested unconditional ICC; its results are excluded.

## Power and household-count screen

At G=300, a 400-repetition power substudy found a **16.5%** probability of rejecting at least one selected true alternative (exact 95% interval **13.0%–20.5%**); the per-selected-alternative rejection rate was **6.47%**. At G=500 (100 repetitions), those figures were **27.0%** (18.6%–36.8%) and **11.35%**. At G=1,000 (100 repetitions), **35.0%** (25.7%–45.2%) and **14.10%**. The G=100 run selected no eligible slices in all 100 repetitions under n_floor=200, so it formed no confirmation family and has no meaningful power or FWER estimate.

The G=500 and G=1,000 partial-null FWER estimates were 2.0% (95% interval 0.24%–7.04%) and 4.0% (1.10%–9.93%), respectively; these intervals are too wide to assess calibration. These are exploratory screening points, not a power curve or an acceptable operating region.

## Limitations and decision

1. Slice membership is synthetic and does not reproduce ACS AGEP/WKHP/SCHL/COW/OCCP/RELP dependence.
2. Only one partial-null pattern (-2 pp), ICC, overlap, and size profile were tested in the selection replay.
3. S-A and S-B are modeled as independent scenario panels; dependence in a real shared-prediction setting may differ.
4. Independent package-level verification of CR2 and final wild-cluster-bootstrap calibration remain outstanding.
5. No real PUMS discovery/confirmation rows or trained model predictions were accessed.

**Decision: preliminary evidence only, not a gate pass.** Expand the partial-null, power, and coverage grid across household counts, effect sizes, ICC, overlap, and size profiles; complete the final 20,000-repetition critical cells before opening held-out data or starting M0.2.
