## Discovery-selection and independent-confirmation replay

**Status: preliminary synthetic replay completed; overall simulation gate remains NOT PASSED.**

## Design

- Two model-comparison scenarios, S-A and S-B. Each has six candidate slices.
- Discovery and confirmation are generated from independent household samples.
- Discovery ranks eligible candidates by the most negative CR2/Satterthwaite t statistic.
- Greedy selection skips a candidate when its person-level Jaccard overlap with any already selected slice is greater than 0.5; up to three are selected per scenario.
- Holm is applied once across the selected confirmation family, which can contain up to six tests.
- Candidate eligibility requires at least 200 people and at least 10 households in this simulation runner. The 10-household threshold is only a technical simulation guard, not an approved protocol decision.

## Complete-null replay

At 300 households, ICC 0.15, latent overlap 0.5, and the moderate size profile, 500 repetitions produced **15 family rejections / 500 (3.0%)**, with exact binomial 95% interval **1.69%–4.90%**. The mean selected family size was 5.352. This is a preliminary complete-null selection replay, not a 20,000-repetition calibration. See selection_replay_complete_null_g300_500_v2.json.

## Partial-null strong-FWER replay

The partial-null DGP sets three candidate slice means per scenario to -2 percentage points and the other three to exactly zero, while using one common paired outcome per person across all six overlapping slices. The conditional mean surface is solved so the overall expected paired difference is zero and all six marginal slice means match their targets. The household-level Dirichlet concentration is algebraically calibrated to the requested **unconditional scalar paired-difference ICC** under the heterogeneous mean surface; unit tests verify the concentration equation and exact marginal slice-mean constraints. Discovery and confirmation use independent household samples.

Across four non-overlapping 100-repetition seed blocks (**400 total**), there were **7 replications with at least one false rejection among true-null selected tests**, giving partial-null strong FWER **1.75%**, exact binomial 95% interval **0.71%–3.57%**. The mean selected family size was 5.38. This is preliminary because only one partial-null pattern, one alternative effect size, and one parameter cell were run. See selection_replay_partial_null_400_pooled.json and the four component JSON files.

A pre-correction partial-null pilot was discarded after review found that its household Dirichlet concentration formula did not preserve the requested unconditional ICC in the presence of heterogeneous household means. Those superseded numbers must not be used.

## Limitations

1. Candidate-slice membership is synthetic and does not reproduce the real ACS AGEP/WKHP/SCHL/COW/OCCP/RELP dependence structure.
2. Only one partial-null pattern and one effect size (-2 pp) were run. More patterns, effect sizes, ICCs, overlap levels, and size profiles are required.
3. The selection replay models two independent scenario panels. Dependence between S-A and S-B model-comparison outcomes may differ in the real paired-prediction setting.
4. This is not an independent package-level verification of CR2, nor does it validate the exact wild-cluster bootstrap.
5. It does not access actual discovery/confirmation PUMS records and does not authorize M0.2.

**Decision: useful preliminary evidence, not a gate pass.** Expand the partial-null grid and calibrate the production candidate procedure with at least 20,000 repetitions in final cells before opening held-out data.
