# M0.1 data report — execution blocked before data access

**Status: NOT RUN**

## Completed

- Python 3.13.5 environment created.
- Household-level SHA-256 split implementation and M0.1 loader written.
- Dependency-light split tests passed (8/8).
- Protocol revised to assign raw household splits before applying the Folktables task filter.

## Not completed

- Folktables and pyarrow were unavailable; package installation failed because this environment could not resolve pypi.org.
- The 2016/2017 PUMS datasets were not downloaded.
- splits.parquet, row counts, feature summaries, and code-set comparisons have not been generated.
- No model training, predictions, or discovery/confirmation metrics were run.

## Held-out data firewall

The script assigns raw household IDs to buckets using only SERIALNO and a fixed salt. It then filters and summarizes only train/validation rows. Discovery and confirmation records are not passed to adult_filter or ACSIncome.df_to_pandas during M0.1.

## Next execution gate

Run the commands in ENV.md on a network-enabled machine. Review the exact adult_filter implementation copied from the installed Folktables package. Do not proceed to M0.2 until the owner approves PROTOCOL_REVISIONS.md and fills the required TODOs in prereg.yaml.
