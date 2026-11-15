# M0 simulation calibration status

**As of 2026-11-15. Status: screening only; Simulation Gate remains NOT PASSED.**

## New synthetic screening completed

- Fixed-family overlapping-slice complete-null screen: 11 data-level cells, 500 repetitions each, 300 households, six correlated candidate slices, CR2/Satterthwaite tests, and Holm correction. Slice candidates below n_floor=200 are ineligible. The first-slice eligibility rate varied by household-size profile (84.4%–99.4%).
- Fixed-family baseline at ICC 0.15 / latent overlap 0.5 / moderate household sizes: 5,000 repetitions, 165 family rejections, FWER 3.30%, exact binomial 95% interval 2.82%–3.83%.
- Independent discovery-selection replay: six candidates per scenario, greedy Jaccard > 0.5 exclusion, up to three selected per S-A/S-B, separate confirmation households, and one Holm family up to six tests. Complete-null screen: 15/500, FWER 3.0%, 95% interval 1.69%–4.90%.
- Partial-null selection replay: three true-null and three -2 pp alternative slice means per scenario, one common paired outcome per person, exact marginal mean constraints, and household Dirichlet concentration calibrated to the requested unconditional scalar-D ICC. Four independent 100-repetition batches (400 total) produced 7 replications with any false rejection among true-null selected tests: strong FWER 1.75%, exact 95% interval 0.71%–3.57%.

## Limitations

These are synthetic screening experiments, not ACS empirical results. Slice membership does not reproduce the real ACS feature dependence structure. The partial-null replay covers one effect pattern and one parameter cell only. The fixed-family grid has only 500 repetitions per cell; the higher-repetition baseline covers one cell. CR2 has an internal matrix-form cross-check, but an independent software/package cross-check remains outstanding. The exact production wild-cluster-bootstrap contract and its final calibration remain outstanding. No ACS PUMS discovery/confirmation records or model predictions were accessed; M0.2 remains blocked.

## Decision

**Do not open discovery/confirmation data and do not start M0.2.** Complete the broader partial-null/overlap/ICC/size grid, independently verify CR2, freeze the wild-bootstrap contract, and run at least 20,000 repetitions in every critical final cell before reconsidering the gate.

Detailed reports: OVERLAP_FAMILY_STATUS.md and SELECTION_REPLAY_STATUS.md. The runnable synthetic implementation and machine-readable result bundle are maintained in the accompanying local artifact package, not yet incorporated as source files in this repository branch.
