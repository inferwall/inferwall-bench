"""Statistical rigor helpers for the benchmark harness.

Pure-stdlib (no numpy/scipy dependency) so the lite CI smoke job can import it
without the ML stack. Provides:

* ``bootstrap_ci`` — non-parametric 95% bootstrap confidence intervals for any
  metric computed from per-sample ``(label, score)`` records.
* metric functions (``recall``, ``precision``, ``f1``, ``fpr``) that take a
  decision threshold so they compose with the bootstrap and the sweep.
* ``threshold_sweep`` — recall/precision/FPR across a grid of score thresholds,
  plus trapezoidal PR-AUC and ROC-AUC.
* ``ci_precision`` — picks a sane rounding precision from sample size, so we do
  not report 91.13% on an n=116 set whose CI is ±6 points.

A "record" is a ``(label, score)`` tuple: ``label`` is 1 (malicious) or 0
(benign); ``score`` is the pipeline's anomaly score for that sample. A sample
is predicted positive when ``score >= threshold``.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence

Record = tuple[int, float]
MetricFn = Callable[[Sequence[Record], float], float]


# --- threshold-parameterized metrics -------------------------------------


def _counts(records: Sequence[Record], threshold: float) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for label, score in records:
        pred = score >= threshold
        if label == 1 and pred:
            tp += 1
        elif label == 0 and pred:
            fp += 1
        elif label == 0 and not pred:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def recall(records: Sequence[Record], threshold: float) -> float:
    tp, _fp, _tn, fn = _counts(records, threshold)
    return tp / (tp + fn) if (tp + fn) else 0.0


def precision(records: Sequence[Record], threshold: float) -> float:
    tp, fp, _tn, _fn = _counts(records, threshold)
    return tp / (tp + fp) if (tp + fp) else 0.0


def fpr(records: Sequence[Record], threshold: float) -> float:
    _tp, fp, tn, _fn = _counts(records, threshold)
    return fp / (fp + tn) if (fp + tn) else 0.0


def f1(records: Sequence[Record], threshold: float) -> float:
    p = precision(records, threshold)
    r = recall(records, threshold)
    return 2 * p * r / (p + r) if (p + r) else 0.0


# --- bootstrap confidence intervals --------------------------------------


def bootstrap_ci(
    values: Sequence[Record],
    metric_fn: MetricFn,
    *,
    threshold: float,
    n: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Non-parametric percentile bootstrap CI for ``metric_fn``.

    Resamples ``values`` with replacement ``n`` times, recomputes the metric at
    the fixed ``threshold`` each time, and returns
    ``(point_estimate, lo, hi)`` for a ``1 - alpha`` two-sided interval.

    The point estimate is computed on the original sample (not the bootstrap
    mean) so it matches the headline number. Deterministic given ``seed``.
    """
    point = metric_fn(values, threshold)
    if not values:
        return point, point, point
    rng = random.Random(seed)
    m = len(values)
    samples = [v for v in values]  # local ref for speed
    stats: list[float] = []
    for _ in range(n):
        resample = [samples[rng.randrange(m)] for _ in range(m)]
        stats.append(metric_fn(resample, threshold))
    stats.sort()
    lo = stats[int((alpha / 2) * n)]
    hi = stats[min(n - 1, int((1 - alpha / 2) * n))]
    return point, lo, hi


def ci_precision(n: int) -> int:
    """Decimal places to report given sample size.

    Small sets (n < 300) have CI widths of several points, so whole-percent
    reporting is honest. Larger sets earn one decimal place. This implements
    the brief's "round to a precision justified by the CI width" rule with a
    simple, defensible heuristic.
    """
    return 0 if n < 300 else 1


def fmt_pct_ci(point: float, lo: float, hi: float, n: int) -> str:
    """Render ``point ± 95% CI`` as a percentage string, rounded by ``n``."""
    dp = ci_precision(n)
    half = (hi - lo) / 2 * 100
    return f"{point * 100:.{dp}f}% ±{half:.{dp}f}"


# --- threshold sweep + AUC -----------------------------------------------


def threshold_sweep(
    records: Sequence[Record],
    *,
    grid: Sequence[float] | None = None,
    points: int = 41,
) -> list[dict[str, float]]:
    """Recall / precision / FPR across a grid of score thresholds.

    If ``grid`` is None, builds a linear grid from 0 to just past the max
    observed score (so the top of the grid yields zero positives). Returns a
    list of dicts sorted by ascending threshold.
    """
    if grid is None:
        hi = max((s for _, s in records), default=1.0)
        hi = max(hi, 1.0)
        grid = [hi * i / (points - 1) for i in range(points)]
    rows: list[dict[str, float]] = []
    for t in grid:
        tp, fp, tn, fn = _counts(records, t)
        r = tp / (tp + fn) if (tp + fn) else 0.0
        p = tp / (tp + fp) if (tp + fp) else (1.0 if tp == 0 and fp == 0 else 0.0)
        f = fp / (fp + tn) if (fp + tn) else 0.0
        rows.append(
            {
                "threshold": round(t, 4),
                "recall": round(r, 4),
                "precision": round(p, 4),
                "fpr": round(f, 4),
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
            }
        )
    return rows


def _trapz(xs: list[float], ys: list[float]) -> float:
    """Trapezoidal integral of ys over xs, robust to unsorted/duplicate xs."""
    pairs = sorted(zip(xs, ys))
    area = 0.0
    for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
        area += (x1 - x0) * (y0 + y1) / 2
    return area


def roc_auc(records: Sequence[Record]) -> float:
    """ROC-AUC via the Mann-Whitney U statistic (handles ties).

    Equivalent to the probability a random positive scores above a random
    negative. Returns 0.5 when one class is absent.
    """
    pos = [s for label, s in records if label == 1]
    neg = [s for label, s in records if label == 0]
    if not pos or not neg:
        return 0.5
    # Rank-based U. For modest n this O(p*n) form is plenty fast and exact.
    greater = 0.0
    for ps in pos:
        for ns in neg:
            if ps > ns:
                greater += 1.0
            elif ps == ns:
                greater += 0.5
    return greater / (len(pos) * len(neg))


def pr_auc(sweep: list[dict[str, float]]) -> float:
    """PR-AUC (average precision) from a sweep.

    Sorts rows by ascending recall and integrates precision as a step function
    of the recall increment (the standard average-precision estimator, robust
    to the coarse/duplicate recall values a fixed threshold grid produces).
    """
    rows = sorted(sweep, key=lambda r: r["recall"])
    area = 0.0
    prev_rec = 0.0
    for row in rows:
        d = row["recall"] - prev_rec
        if d > 0:
            area += d * row["precision"]
            prev_rec = row["recall"]
    return area


if __name__ == "__main__":
    # Smoke: a separable toy problem should give recall~1, AUC~1.
    recs: list[Record] = [(1, 12.0), (1, 9.0), (1, 7.0), (0, 1.0), (0, 0.5), (0, 2.0)]
    pt, lo, hi = bootstrap_ci(recs, recall, threshold=4.0, n=500)
    print("recall@4.0", fmt_pct_ci(pt, lo, hi, len(recs)))
    print("roc_auc", round(roc_auc(recs), 3))
    sw = threshold_sweep(recs, points=13)
    print("pr_auc", round(pr_auc(sw), 3))
    for row in sw[:4]:
        print(row)
