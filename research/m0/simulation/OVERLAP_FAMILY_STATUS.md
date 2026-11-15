# Overlapping-slice complete-null calibration

**Status: expanded screening completed; overall simulation gate remains NOT PASSED. Synthetic only.**

## Fixed-family screening grid

Eleven 500-repetition cells were run with 300 households, six correlated candidate slices, CR2/Satterthwaite tests, and Holm adjustment. Eight cells vary ICC (0.05, 0.15, 0.30) and latent overlap (0.1, 0.5, 0.9); two additional cells vary household-size profile at ICC 0.15 / overlap 0.5. Candidate slices below n_floor=200 or with fewer than 10 household clusters are treated as ineligible and assigned p=1. The technical 10-cluster guard is not an approved production floor.

| ICC | Latent overlap | Size profile | Realized Jaccard | FWER | 95% Monte Carlo interval | First-slice eligibility |
|---:|---:|---|---:|---:|---:|---:|
| 0.05 | 0.1 | moderate | 0.381 | 0.048 | [0.031, 0.071] | 99.4% |
| 0.05 | 0.5 | moderate | 0.500 | 0.042 | [0.026, 0.063] | 99.4% |
| 0.05 | 0.9 | moderate | 0.682 | 0.030 | [0.017, 0.049] | 99.2% |
| 0.15 | 0.1 | moderate | 0.381 | 0.042 | [0.026, 0.063] | 99.4% |
| 0.15 | 0.5 | balanced_2 | 0.498 | 0.034 | [0.020, 0.054] | 87.6% |
| 0.15 | 0.5 | moderate | 0.500 | 0.038 | [0.023, 0.059] | 99.4% |
| 0.15 | 0.5 | right_skewed | 0.503 | 0.024 | [0.012, 0.042] | 84.4% |
| 0.15 | 0.9 | moderate | 0.682 | 0.022 | [0.011, 0.039] | 99.2% |
| 0.30 | 0.1 | moderate | 0.381 | 0.052 | [0.034, 0.075] | 99.4% |
| 0.30 | 0.5 | moderate | 0.500 | 0.032 | [0.018, 0.051] | 99.4% |
| 0.30 | 0.9 | moderate | 0.683 | 0.022 | [0.011, 0.039] | 99.2% |

All cells are screening-level only (500 repetitions each). Their Monte Carlo intervals are too wide for a final acceptance decision. In particular, the ICC 0.30 / overlap 0.10 cell has an upper bound of 7.53%, and the ICC 0.05 / overlap 0.10 and ICC 0.15 / overlap 0.10 or 0.50 cells also have upper bounds above the proposed 5.5% simulation threshold.

## Higher-repetition fixed-family baseline

The ICC 0.15 / latent overlap 0.50 / moderate-size baseline was run in five non-overlapping 1,000-repetition batches (5,000 total), applying the n_floor=200 eligibility rule. Result: **165 / 5,000 family rejections, FWER 3.30%, exact binomial 95% interval 2.82%–3.83%**. Mean realized pairwise Jaccard was approximately 0.500. This is stronger evidence for this one fixed-family synthetic cell, but it still does not replay discovery selection.

## Limits and decision

1. All grid cells use synthetic Gaussian-copula membership, not the empirical ACS feature prevalence/dependence structure.
2. The fixed-family grid does not execute the greedy discovery selection process. A separate independent-selection replay was run; its preliminary results are documented in SELECTION_REPLAY_STATUS.md in the local simulation package.
3. The 10-household technical guard is a simulation safeguard only. The operational minimum-cluster rule remains unresolved.
4. This work does not use ACS replicate weights, actual PUMS discovery/confirmation rows, trained models, or prediction outputs.
5. The earlier 2,000-repetition pilot result (3.65%, interval 2.87%–4.57%) predates enforcement of n_floor=200 and must be treated as a legacy pilot, not pooled with the new grid.

**Overall Simulation Gate: NOT PASSED.** The baseline fixed-family cell looks conservative, but the wider grid is screening-only and the full design/strong-FWER evidence remains incomplete.
