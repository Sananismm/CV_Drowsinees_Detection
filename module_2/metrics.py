"""CLOSED-positive binary metrics, with explicit abstention coverage.
Definitions: https://scikit-learn.org/stable/modules/model_evaluation.html
"""
import numpy as np


def binary_metrics(truth, predictions):
    if len(truth) != len(predictions) or not truth or any(y not in (0,1) for y in truth):
        raise ValueError("nonempty equal-length binary labels required")
    if any(p not in (0,1,None) for p in predictions):
        raise ValueError("predictions must be 0, 1, or None")
    cm = [[0,0],[0,0]]
    for y,p in zip(truth,predictions):
        if p is not None: cm[y][p] += 1
    tn,fp,fn,tp = cm[0][0],cm[0][1],cm[1][0],cm[1][1]
    n = tn+fp+fn+tp
    div=lambda a,b: a/b if b else None
    return dict(n_total=len(truth), n_scored=n, coverage=n/len(truth),
        accuracy=div(tn+tp,n), accuracy_with_abstentions_as_errors=(tn+tp)/len(truth),
        precision=div(tp,tp+fp), recall=div(tp,tp+fn), f1=div(2*tp,2*tp+fp+fn),
        confusion_matrix=cm, matrix_order=["OPEN","CLOSED"], false_open=fn, false_closed=fp)


def latency_summary(values):
    return dict(mean_ms=float(np.mean(values)), p50_ms=float(np.median(values)),
                p95_ms=float(np.percentile(values,95)), n=len(values)) if values else None
