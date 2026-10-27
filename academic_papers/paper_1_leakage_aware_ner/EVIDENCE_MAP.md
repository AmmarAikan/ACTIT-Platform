# Evidence Map

| Manuscript claim | Primary local evidence |
|---|---|
| Original split sizes, malformed lines, duplicates, conflicts, BIO defects, and overlap | `ml/experiments_clean_v2/20261014T110000Z/dataset_construction.json` |
| Clean-v2 construction policy and quality gates | `ml/experiments_clean_v2/20261014T110000Z/DATASET_CONSTRUCTION_REPORT.md`; `dataset_construction.json` |
| Clean split sizes and SHA-256 values | `dataset_construction.json` under `derived_files` |
| Training command and hyperparameters | `ml/experiments_clean_v2/20261014T110000Z/training_state.json` |
| Clean model summary and production decision | `ml/experiments_clean_v2/20261014T110000Z/final_decision.json` |
| Clean exact-span micro/macro/per-type results | `first_subword/entity_metrics.json`; `bio_aware/entity_metrics.json` |
| Clean token accuracy and O-excluded metrics | `first_subword/token_metrics.json`; `bio_aware/token_metrics.json` |
| Original full-test results | `ml/experiments/bert_paper_parity/20260924T000911Z/PAPER_PARITY_REPORT.md`; alignment metric JSON files |
| Original unique-unseen results | `ml/experiments/bert_paper_parity/20260924T000911Z/readiness_evaluation/unique_unseen_alignment_a.json`; alignment B counterpart |
| Original tokenization fragmentation | `ml/experiments/bert_paper_parity/20260924T000911Z/tokenization_audit.json` |
| Missing earlier training utility limitation | `ml/experiments/bert_paper_parity/20260924T000911Z/reproduction_limitations.json`; `utility_disappearance_analysis.json` |
| No production promotion | Both experiment final-decision/readiness evidence; production was not modified for this paper |

No credential, token, private key, production record, or sensitive environment value is used in the manuscript.
