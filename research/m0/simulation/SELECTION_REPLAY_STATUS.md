## Discovery-selection and independent-confirmation replay

**Status: preliminary synthetic replay completed; overall simulation gate remains NOT PASSED.**

### Design

- Two model-comparison scenarios, S-A and S-B, each with six candidate slices.
- Independent discovery and confirmation household samples.
- Discovery ranks eligible candidates by the most-negative CR2/Satterthwaite statistic.
- Greedy Jaccard selection skips a candidate when overlap with any selected slice exceeds 0.5; up to three slices are selected per scenario.
- Holm is applied across the selected confirmation family, maximum six.
- Eligibility: at least 200 people and a technical minimum of 10 households. The 10-household floor is not an approved production rule.

### Complete-null replay

At 300 households, ICC 0.15, latent overlap 0.5, and moderate household sizes, 500 repetitions produced **15 family rejections / 500 (3.0%)**, exact binomial 95% interval **1.69%–4.90%**. Mean selected family size was 5.352.

### Partial-null strong-FWER and power replay

The partial-null DGP sets three candidate slice means per scenario to -2 percentage points and the other three to exactly zero. It uses one shared paired outcome per person. The conditional mean surface is solved to match all six marginal slice means while keeping the overall mean zero. The household Dirichlet concentration is algebraically calibrated to the requested unconditional scalar paired-difference ICC under heterogeneous household means; unit tests cover the equation and marginal constraints.

Across six non-overlapping seed blocks (**800 total repetitions**), there were **19 replications with at least one false rejection among true-null selected tests**, giving partial-null strong FWER **2.375%**, exact binomial 95% interval **1.44%–3.68%**. Mean selected family size was 5.398.

A power substudy on the latest two 200-repetition batches (**400 repetitions**) found a **16.5%** probability of rejecting at least one selected true alternative. Mean selected alternative tests was 3.555 per repetition; the per-selected-alternative rejection rate was **6.47%**. This is far below the proposed 80% power target for a -2 pp effect in this 300-household design. These are preliminary screen estimates, not final power curves.

A finite-sample ICC diagnostic using 5,000 synthetic households observed a within-household paired-difference ICC of 0.137 for a 0.15 target. This is consistent with the target within Monte Carlo variation; see the local companion package's partial_null_icc_diagnostic.json.

### Limitations

1. Slice membership does not reproduce ACS AGEP/WKHP/SCHL/COW/OCCP/RELP dependence.
2. Only one partial-null pattern, -2 pp effect, ICC, overlap, and household-size profile were run.
3. S-A and S-B are simulated as independent scenario panels; dependence in a real shared-prediction setting may differ.
4. Independent software/package verification of CR2 and final wild-cluster-bootstrap calibration remain outstanding.
5. No actual discovery/confirmation PUMS records or trained model predictions were accessed.

**Decision: preliminary evidence only, not a gate pass.** Expand the partial-null, power, and coverage grid across household counts, ICC, overlap, and size profiles; complete final 20,000-repetition critical cells before opening held-out data or starting M0.2.
