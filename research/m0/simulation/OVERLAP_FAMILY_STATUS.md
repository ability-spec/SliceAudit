# Overlapping-slice family calibration status

**Date:** 2026-11-14  
**Status:** preliminary calibration only; the overall simulation gate is NOT PASSED.

## Completed synthetic calibration cell

A data-level complete-null simulation was run with six correlated slice-membership masks and household-clustered paired correctness differences.

| Setting | Value |
|---|---:|
| Replications | 2,000 |
| Households | 300 |
| Household ICC | 0.15 |
| Latent overlap correlation | 0.50 |
| Tests in family | 6 |
| Mean realized pairwise Jaccard | 0.49916 |
| Holm family-wise error rate | 0.0365 |
| Exact binomial Monte Carlo 95% interval | 0.028717–0.045677 |

This single calibration cell is compatible with a 0.05 FWER target under the current Monte Carlo interval. It does not establish calibration across the design space.

## Important limitations

- The simulation uses synthetic Gaussian-copula slice membership, not the empirical ACS feature prevalence and dependence structure.
- It is a complete-null cell only. Partial-null strong-FWER behavior has not been established.
- It does not yet replay the registered discovery procedure, greedy Jaccard-overlap filtering, or the discovery-to-independent-confirmation firewall.
- The current result does not validate the whole family-wise procedure or authorize opening confirmation data.
- The synthetic generator's PWGTP-like values are not Census replicate weights and cannot support ACS design-based inference.
- CR2/Satterthwaite algebra has unit tests, but an independent package-level CR2 implementation cross-check remains outstanding.

## Next calibration work

1. Add partial-null data-level scenarios with a clearly specified common paired-outcome construction.
2. Replay the exact discovery selection rule, including the Jaccard > 0.5 exclusion rule, then test on independent confirmation data.
3. Expand complete-null calibration across ICC values 0.05, 0.15, and 0.30, household-size profiles, and overlap levels.
4. Run at least 20,000 repetitions for final calibration cells and report Monte Carlo uncertainty.
5. Cross-check the CR2/Satterthwaite implementation independently.
6. Keep M0.2 blocked until the simulation gate and protocol freeze are complete.

## Reproducibility

The companion local artifact package `SliceAudit_M0_Simulation_v0.1` contains the synthetic DGP, inference implementation, multiplicity helpers, tests, run configuration, and machine-readable results. Its unit suite passed **28/28 tests** in the local environment. No actual PUMS data, trained models, discovery slices, or confirmation outcomes were accessed in this calibration work.
