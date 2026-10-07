# Stateful Sequence Detection of Multi-Step BOLA in REST APIs: replication artefact

Benchmark, leave-one-application-out (LOAO) folds, notebooks and per-run predictions for the manuscript
*Stateful Sequence Detection of Multi-Step Broken Object Level Authorization in REST APIs*
(Nachevski, Schwarz, Creutzburg, Ballı; submitted to the Journal of Information Security and Applications).
A Longformer encoder and a matched-budget LSTM are compared on 32 labelled attack-sequence exemplars from a
benchmark of 31 confirmed cases, under LOAO cross-validation (16 held-out applications, 3 seeds, 96 runs).

Fine-tuned weights were not retained. The released predictions are the authoritative record of the reported figures.

## Check the paper's numbers in one command

```
pip install numpy scikit-learn
python reproduce_paper_tables.py
```

This reads only the files below and prints the pooled metrics, the per-fold recall table, the paired bootstrap of the
F1 difference, the full-benchmark union result, the learning-rate check and the run-by-run Ample POS scores. `SHA256SUMS` lists a checksum for every file.

### Ample POS, run by run

The Longformer's recall on Ample POS (6 attack exemplars) is 0.667 +/- 0.471 because the six attacks move together with the seed:

| Run (seed) | Longformer attack probabilities | Hits | LSTM hits |
|---|---|---|---|
| 0 (42) | 0.18 to 0.23 | 0/6 | 6/6 |
| 1 (43) | 0.51 to 0.63 | 6/6 | 6/6 |
| 2 (44) | 0.80 to 0.87 | 6/6 | 6/6 |

## Layout

| Folder | Content |
|---|---|
| `01_benchmark_annotations/` | `cve_benchmark_table_v4_final.csv` (the benchmark table) and `unified_benchmark_cve_annotations_complete.csv` (the full sourced annotation set) |
| `02_loao_folds/<application>/` | `train.jsonl` and `eval.jsonl` for each of the 16 held-out applications |
| `03_notebooks/` | The seven pipeline notebooks, in run order (pretraining, tokenisation, fold generation, Longformer fine-tuning, learning-rate check, LSTM, secondary metrics), plus `08_second_request_only_ablation.ipynb`, which retrains both models on the second request alone |
| `04_results/longformer_finetune_v2/` | Primary Longformer result: 48 per-run files (`fold_<app>_run<0-2>.json`) and `pooled_predictions.npz` |
| `04_results/lstm_comparator/` | Same for the LSTM |
| `04_results/longformer_finetune_v3_highlr/` | Longformer at fine-tuning learning rate 1e-4 (robustness check reported in Section 4) |
| `04_results/second_request_ablation/` | Second-request-only networks: `longformer_second_only/` and `lstm_second_only/` (48 per-run files each, same format as the pair results) and `ablation_second_summary.json` (pooled metrics and paired-bootstrap intervals, pair versus single request) |
| `05_tokenizer_phase3_final/` | Tokenizer and architecture config. No model weights |

## How to read the result files

- Each `pooled_predictions.npz` holds `probs` and `labels` with 546 entries (96 positive, 450 negative): folds in alphabetical order, three
  runs per fold, rows in the order of the matching `eval.jsonl`.
- The primary result uses 32 exemplars. The Spree per-run files in `longformer_finetune_v2/` and `lstm_comparator/` also contain
  the single-step case CVE-2026-25757 as a twelfth row, so the 48 per-run files together hold 549 predictions. These are the
  inputs of the full-benchmark union analysis (33 exemplars). The primary pooled files omit that row. `reproduce_paper_tables.py` does both.
- `phpapp_studentmgmt/eval.jsonl` contains only its two attack sequences and no benign sequences, by construction of that fold.
- `fold_<app>_run<n>.json` records `fold`, `run`, `seed`, `probs`, `labels`, `n_train`, `n_eval` (and `total_steps` for the LSTM).

## Benchmark notes

- 31 confirmed cases; 32 labelled exemplars feed the primary result. The lab deployment of CVE-2023-32310 (DataEase) failed
  and is documented as such in the annotation table.
- One case, an IDOR on the `ticket_related` endpoint of Zammad, is documented in GitHub Security Lab advisory GHSL-2026-049
  and Zammad advisory ZAA-2026-05. It has no CVE identifier yet. See the annotation table for the details.
- Leave-one-application-out holds out an application's attack exemplars, not its benign traffic. See the Limitations section of the paper.

## Licence

Code is released under the MIT licence (`LICENSE-MIT`): the notebooks in `03_notebooks/` and `reproduce_paper_tables.py`.
Data and documentation are released under CC BY 4.0 (`LICENSE`): the annotations, folds, results and this README.
The base Longformer architecture and any pretrained weights it depends on keep their upstream licences.
The benchmark draws on the published BACFuzz and BolaZ work, credited in `01_benchmark_annotations/`.
