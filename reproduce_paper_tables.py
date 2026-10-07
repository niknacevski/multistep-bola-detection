"""Recompute the headline numbers of the paper from the released predictions.

Usage:  python reproduce_paper_tables.py          (needs numpy, scikit-learn)

Reads only files in this repository. Prints:
  1. pooled metrics (546 predictions per model, threshold 0.5)
  2. per-fold recall, mean +/- s.d. (population) over the 3 runs
  3. paired bootstrap of the F1 difference (LSTM minus Longformer)
  4. full-benchmark union (549 predictions, from the per-run files)
  5. learning-rate robustness check (1e-4)
  6. Ample POS (6 attack exemplars), run by run
  7. Second-request-only ablation: pair versus single-request networks

Layout of pooled_predictions.npz: folds in alphabetical order, 3 runs per fold,
rows in the order of 02_loao_folds/<app>/eval.jsonl. In the primary result the
Spree fold omits its last eval row (the single-step case CVE-2026-25757, which
only enters the union analysis), so Spree has 11 rows there and 12 in the
per-run files.
"""
import glob, json, os
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "04_results")
MODELS = {"Longformer": "longformer_finetune_v2", "LSTM": "lstm_comparator"}


def pooled(d):
    z = np.load(os.path.join(RES, d, "pooled_predictions.npz"))
    return z["probs"], z["labels"]


def metrics(p, y, thr=0.5):
    pr = p >= thr
    tp = int((pr & (y == 1)).sum()); fp = int((pr & (y == 0)).sum())
    fn = int(((~pr) & (y == 1)).sum()); tn = int(((~pr) & (y == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn)
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(auc=roc_auc_score(y, p), pr_auc=average_precision_score(y, p),
                precision=prec, recall=rec, fpr=fp / (fp + tn), f1=f1, hits=tp, alerts=tp + fp)


def show(name, m):
    print(f"  {name:11s} ROC-AUC {m['auc']:.3f}  PR-AUC {m['pr_auc']:.3f}  P {m['precision']:.3f}  "
          f"R {m['recall']:.3f}  FPR {m['fpr']:.3f}  F1 {m['f1']:.3f}  ({m['hits']} hits, {m['alerts']} alerts)")


print("1. Pooled primary result (546 predictions, 96 positive / 450 negative)")
P = {}
for n, d in MODELS.items():
    P[n] = pooled(d); show(n, metrics(*P[n]))

print("\n2. Per-fold recall, mean +/- s.d. over 3 runs (threshold 0.5)")
folds = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "02_loao_folds", "*")))
for n, d in MODELS.items():
    p, y = P[n]; pos = 0; cells = {}; ok = 0
    for f in folds:
        rows = [json.loads(l) for l in open(os.path.join(HERE, "02_loao_folds", f, "eval.jsonl"))]
        lab = [r["label"] for r in rows]
        if f == "Spree": lab = lab[:-1]
        k = len(lab); rec = []
        for _ in range(3):
            pp, yy = p[pos:pos + k], y[pos:pos + k]; pos += k
            assert list(yy) == lab
            rec.append(((pp >= .5) & (yy == 1)).sum() / yy.sum())
        cells[f] = (np.mean(rec), np.std(rec)); ok += np.mean(rec) >= .5
    print(f"  {n}: {ok} of {len(folds)} folds at or above 0.5")
    print("   ", "; ".join(f"{f} {m:.3f}+/-{s:.3f}" for f, (m, s) in cells.items()))

print("\n3. Paired bootstrap, F1(LSTM) - F1(Longformer), 10,000 resamples within the pool")
(p1, y), (p2, _) = P["Longformer"], P["LSTM"]
f1 = lambda p, y: 2 * ((p >= .5) & (y == 1)).sum() / ((p >= .5).sum() + y.sum())
rng = np.random.default_rng(0); d = []
for _ in range(10000):
    i = rng.integers(0, len(y), len(y)); d.append(f1(p2[i], y[i]) - f1(p1[i], y[i]))
print(f"  delta F1 {f1(p2, y) - f1(p1, y):.3f}, 95% interval {np.percentile(d, [2.5, 97.5]).round(3).tolist()}")

print("\n4. Full-benchmark union (549 predictions, per-run files)")
for n, dname in MODELS.items():
    ps, ys = [], []
    for f in sorted(glob.glob(os.path.join(RES, dname, "fold_*.json"))):
        j = json.load(open(f)); ps += j["probs"]; ys += j["labels"]
    show(n, metrics(np.array(ps), np.array(ys)))

print("\n5. Longformer at learning rate 1e-4 (robustness check)")
show("Longformer", metrics(*pooled("longformer_finetune_v3_highlr")))

print("\n6. Ample POS (6 attack exemplars), run by run")
for n, dname in MODELS.items():
    for r in range(3):
        j = json.load(open(os.path.join(RES, dname, f"fold_phpapp_ample_run{r}.json")))
        p = np.array(j["probs"]); l = np.array(j["labels"])
        hits = int(((p >= .5) & (l == 1)).sum())
        print(f"  {n:11s} run {r} (seed {j['seed']}): {hits}/{int(l.sum())} above 0.5, "
              f"attack probabilities {np.round(p[l == 1], 2).tolist()}")

print("\n7. Second-request-only ablation (notebook 08), recomputed from the per-run files")
ABL = os.path.join(RES, "second_request_ablation")
SEP = " [SEP] "

def pooled_ablation(dirpath):
    """Primary rows only (two-request rows), folds alphabetical, 3 runs each."""
    P, L = [], []
    for f in sorted(glob.glob(os.path.join(dirpath, "fold_*_run*.json"))):
        r = json.load(open(f))
        ev = [json.loads(l) for l in open(os.path.join(HERE, "02_loao_folds", r["fold"], "eval.jsonl"))]
        keep = np.array([SEP in e["sequence"] for e in ev])
        P += list(np.array(r["probs"])[keep]); L += list(np.array(r["labels"])[keep])
    return np.array(P), np.array(L)

def pooled_pair_from_runs(d):
    P, L = [], []
    for f in sorted(glob.glob(os.path.join(RES, d, "fold_*_run*.json"))):
        r = json.load(open(f))
        ev = [json.loads(l) for l in open(os.path.join(HERE, "02_loao_folds", r["fold"], "eval.jsonl"))]
        keep = np.array([SEP in e["sequence"] for e in ev])
        P += list(np.array(r["probs"])[keep]); L += list(np.array(r["labels"])[keep])
    return np.array(P), np.array(L)

A = {"Longformer, pair": pooled_pair_from_runs("longformer_finetune_v2"),
     "LSTM, pair": pooled_pair_from_runs("lstm_comparator"),
     "Longformer, second only": pooled_ablation(os.path.join(ABL, "longformer_second_only")),
     "LSTM, second only": pooled_ablation(os.path.join(ABL, "lstm_second_only"))}
for n, (p, y) in A.items():
    m = metrics(p, y)
    print(f"  {n:24s} recall {m['recall']:.3f}  precision {m['precision']:.3f}  FPR {m['fpr']:.3f}  "
          f"F1 {m['f1']:.3f}  ROC-AUC {m['auc']:.3f}  PR-AUC {m['pr_auc']:.3f}")
f1 = lambda p, y: 2 * ((p >= .5) & (y == 1)).sum() / ((p >= .5).sum() + y.sum())
rng = np.random.default_rng(0)   # one generator for both architectures, as in notebook 08
for arch in ("Longformer", "LSTM"):
    (pp, yp), (pa, ya) = A[f"{arch}, pair"], A[f"{arch}, second only"]
    d = []
    for _ in range(10000):
        i = rng.integers(0, len(yp), len(yp)); d.append(f1(pp[i], yp[i]) - f1(pa[i], ya[i]))
    lo, hi = np.percentile(d, [2.5, 97.5])
    print(f"  {arch}: F1(pair) - F1(second only) = {f1(pp, yp) - f1(pa, ya):+.3f}, 95% interval [{lo:+.3f}, {hi:+.3f}]")
print("  (bootstrap uses a fixed seed; the pair rows come from the per-run files and differ from the paper's")
print("   Table 1 only in the Spree fold, which was re-scored after it gained the single-step case)")
saved = json.load(open(os.path.join(ABL, "ablation_second_summary.json")))["pooled"]
ok = all(abs(metrics(*A[k])["f1"] - saved[k]["f1"]) < 1e-9 for k in A)
print("  matches the saved summary:", ok)
