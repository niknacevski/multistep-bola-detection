# Reproducibility Artifact — LOAO Benchmark for Multi-Step BOLA/BFLA Detection

This repository accompanies the M.Sc. thesis and the associated JISA (Journal
of Information Security and Applications) manuscript on detecting
authorization-vulnerability exploitation traces (BOLA / BFLA / BOPLA / UASBF)
in HTTP/API traffic, using a Longformer-based sequence classifier evaluated
under Leave-One-Application-Out (LOAO) cross-validation, with an LSTM model
as a comparator baseline.

**All 16 benchmark applications are included with no structural exclusions
in the experiment part, including the Zammad case (BOLA on ticket groups).**
The one item intentionally *excluded* from the LOAO benchmark itself is
`CVE-2023-32310` (DataEase), because the corresponding attack could not be
successfully deployed in the lab environment — this is documented as a
deployment failure in the benchmark annotation table
(`01_benchmark_annotations/`), not a structural exclusion of an application
from the experiment.

## Directory structure

```
00_README.md                     — this file
LICENSE                          — license for this repository's own content
01_benchmark_annotations/        — CVE / vulnerability annotation tables (CSV)
02_loao_folds/                   — per-application LOAO train/eval JSONL folds (16 apps)
03_notebooks/                    — the 7 pipeline notebooks, in run order
04_results/                      — per-fold, per-run prediction outputs + pooled predictions
                                    for both models (Longformer and LSTM)
05_tokenizer_phase3_final/       — final tokenizer artifacts (config + vocab), no model weights
```

### `01_benchmark_annotations/`
- `cve_benchmark_table_v4_final.csv` — the final, verified benchmark table used
  in the paper (application, vulnerability class, endpoint, precondition,
  confidence, source). Includes the Zammad-IDOR (BOLA, ticket group) row,
  verified by GitHub Security Lab advisory (no CVE ID assigned).
- `unified_benchmark_cve_annotations_complete.csv` — the full sourced CVE
  annotation set (BACFuzz- and BolaZ-derived cases) used to build and cross-check
  the benchmark, including classification basis, precondition/unauthorized-request
  API pairs, and confidence ratings for each case.

### `02_loao_folds/`
One subfolder per application (16 total), each containing:
- `train.jsonl` — benign + malicious training traces for that LOAO fold
  (all applications except the held-out one)
- `eval.jsonl` — the held-out application's evaluation traces

Applications: Grafana, IceCMS, Langflow, OpenWebUI, Spree, Wekan, **Zammad**,
phpapp_ample, phpapp_filemgmt, phpapp_leaveborrow, phpapp_leavemgmt2,
phpapp_lms, phpapp_notes, phpapp_oews, phpapp_quiz, phpapp_studentmgmt.

Note: `phpapp_studentmgmt/eval.jsonl` has no positive (attack) examples in its
held-out fold by construction — this is a known, documented special case
(see notebook 03's markdown cells), not a data error.

### `03_notebooks/`
Run in this order to reproduce the full pipeline://
1. `01_pretraining.ipynb` — domain-adaptive pretraining of the base Longformer
   encoder on unlabeled API traffic.
2. `02_benign_trace_tokenization.ipynb` — tokenization pipeline for benign
   traffic traces.
3. `03_loao_fold_generation_v2.ipynb` — builds the 16 LOAO folds from the
   annotated benchmark cases and benign trace pool.
4. `04_longformer_finetuning_v2_PRIMARY.ipynb` — primary Longformer fine-tuning
   and evaluation across all 16 folds x 3 runs (the model reported in the paper).
5. `05_longformer_v3_highlr_robustness_check.ipynb` — robustness/ablation check
   at a higher learning rate.
6. `06_lstm_comparator.ipynb` — LSTM baseline model, trained/evaluated on the
   same folds for direct comparison.
7. `07_secondary_metrics_and_significance_test.ipynb` — computes secondary
   metrics and statistical significance tests (e.g. paired comparison between
   Longformer and LSTM) from the pooled predictions.

### `04_results/`
- `longformer_finetune_v2/` and `lstm_comparator/` each contain 48
  `fold_<Application>_run<0|1|2>.json` files (16 apps × 3 runs) plus a
  `pooled_predictions.npz` aggregating all fold/run predictions
  (546 total predictions per model: 96 positive / 450 negative).

### `05_tokenizer_phase3_final/`
The final tokenizer configuration and vocabulary (`tokenizer.json`,
`tokenizer_config.json`, `config.json` for the Longformer model architecture).
**Fine-tuned model weights (`model.safetensors`) are intentionally not
included**, per this artifact's "no fine-tuned weights retained" policy
(see the manuscript's Data and Code Availability statement) — the released
artifact allows full reproduction of the pipeline from data + notebooks
rather than distribution of trained checkpoints.

## Reproducing the pooled metrics

Given `04_results/<model>/pooled_predictions.npz`, the pooled precision,
recall, F1, and any significance tests reported in the paper can be
recomputed directly from the stored predictions/labels without re-running
training — see `03_notebooks/07_secondary_metrics_and_significance_test.ipynb`
for the exact computation.

To reproduce end-to-end (data → folds → training → pooled metrics), run
notebooks 01 through 07 in order against the data in `02_loao_folds/`.

## License

See `LICENSE`. This repository's own code, notebooks, and annotations are
released under CC BY 4.0. The base Longformer model architecture and any
pretrained weights it depends on retain their own upstream licenses (see the
respective model cards); no fine-tuned weights are redistributed here. The
CVE-derived benchmark cases draw on the BACFuzz and BolaZ published works,
credited in `01_benchmark_annotations/`.
