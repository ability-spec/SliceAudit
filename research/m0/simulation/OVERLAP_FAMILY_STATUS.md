# Overlapping-slice and selection-replay calibration status

**Updated:** 2026-11-25  
**Overall Simulation Gate:** **NOT PASSED**. The new results below are synthetic screening, not final calibration.

## Earlier complete-null pilot (2026-11-14)

A data-level complete-null simulation used six correlated slice-membership masks and household-clustered paired correctness differences.

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

This is one complete-null cell only; it does not establish calibration across the design space.

## New partial-null end-to-end selection replay (2026-11-25)

The synthetic discovery-selection-confirmation replay was extended to 4,000 independent repetitions at the previously high-power operating point.

| Setting | Value |
|---|---:|
| Replications | 4,000 |
| Households per split | 5,000 |
| Paired-difference household ICC | 0.15 |
| Latent slice-overlap correlation | 0.50 |
| Household-size profile | moderate |
| Candidate slices | 6 per scenario, 2 scenarios |
| Slices selected | up to 3 per scenario |
| Minimum people per candidate | 200 |
| Alternative slice effect | -2 percentage points |
| Confirmation family | Holm, up to 6 tests |

Three of six slice hypotheses per scenario are true nulls; the other three have a -2 pp effect. Discovery and confirmation use independently generated household samples. The same paired correctness outcome is shared across overlapping slices.

| Result | Estimate |
|---|---:|
| Partial-null strong FWER | **4.65%** (186 / 4,000) |
| Exact binomial Monte Carlo 95% interval | **4.02%–5.35%** |
| Probability of at least one selected alternative rejection | **98.50%** |
| Rejection rate among selected alternative tests | **79.19%** |
| Mean selected family size | 5.648 |

The FWER interval is below the currently proposed 5.5% upper-bound for this particular cell. This is encouraging screening evidence, not a Simulation Gate pass: it is one synthetic operating point, and the preregistered final plan requires at least 20,000 repetitions in critical cells, wider ICC/overlap/cluster-size coverage, and a validated inference implementation.

## Prespecified true-null diagnostic without discovery selection

A separate diagnostic isolates the marginal CR2/Satterthwaite p-value layer from the selection process. All six prespecified true-null slices were tested in each repetition.

| Result | Estimate |
|---|---:|
| Repetitions | 2,000 |
| Raw tests | 12,000 |
| Raw pointwise rejection | 4.842% |
| Exact binomial Monte Carlo 95% interval | 4.464%–5.241% |
| Mean null p-value | 0.5008 |
| Holm FWER | **4.05%** |
| Exact binomial Monte Carlo 95% interval | **3.23%–5.01%** |

This supports the marginal p-value layer under this one synthetic partial-null design. It does not validate discovery selection, other operating points, or the exact wild-cluster bootstrap.

## Implementation and tests

The local simulation package's selection replay now generates household-level Dirichlet probabilities and person outcomes with vectorized NumPy operations instead of a Python RNG loop per household. This made larger-G screening runs practical while retaining household-constant slice membership and independent discovery/confirmation panels.

**Unit suite: 40/40 passed** after the change, including new determinism, household-alignment, and partial-null target-mean tests.

## Remaining gates

1. Run at least 20,000 repetitions in each critical final null and interval-coverage cell, with Monte Carlo intervals reported.
2. Extend data-level partial-null selection replay across ICC, overlap, household-size profiles, and sample sizes.
3. Complete an independent software/package cross-check of CR2/Satterthwaite.
4. Validate the wild-cluster-bootstrap finite-sample contract with at least 9,999 draws per test in final calibration.
5. Re-run M0.1 with the revised household split allocation before M0.2. The committed 2026-11-01 2016 artifacts use the superseded 85%/15% allocation and must not be used for model fitting.

The simulations use synthetic data only. No ACS PUMS discovery/confirmation records or fitted model predictions were read. **M0.2 remains blocked.**
