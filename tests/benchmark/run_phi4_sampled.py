#!/usr/bin/env python3
"""Run Phi-4 on subsampled toxic-chat and safeguard datasets.

We already have full results for deepset (116) and jackhhao (262).
For the larger datasets, use stratified random subsamples.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.benchmark.loaders import BenchmarkSample, load_dataset_by_name
from tests.benchmark.phi4_baseline import Phi4Baseline
from tests.benchmark.run_benchmark import SystemMetrics, compute_metrics, update_counts


def stratified_subsample(
    samples: list[BenchmarkSample], n: int, seed: int = 42
) -> list[BenchmarkSample]:
    """Take a stratified random subsample preserving label ratio."""
    rng = random.Random(seed)
    pos = [s for s in samples if s.label == 1]
    neg = [s for s in samples if s.label == 0]

    ratio = len(pos) / len(samples)
    n_pos = max(1, round(n * ratio))
    n_neg = n - n_pos

    # If we have fewer positive samples than needed, take all
    n_pos = min(n_pos, len(pos))
    n_neg = min(n_neg, len(neg))

    rng.shuffle(pos)
    rng.shuffle(neg)

    return pos[:n_pos] + neg[:n_neg]


def main():
    if not os.environ.get("HF_TOKEN"):
        print("ERROR: Set HF_TOKEN environment variable")
        sys.exit(1)

    model_path = "/tmp/models/Phi-4-mini-instruct-Q4_K_M.gguf"
    baseline = Phi4Baseline(model_path, n_threads=8)
    baseline.warmup(3)

    results = []

    # Toxic-chat: subsample 500
    print("Loading toxic-chat...", flush=True)
    tc_samples = load_dataset_by_name("toxic-chat")
    tc_sub = stratified_subsample(tc_samples, 500)
    mal = sum(1 for s in tc_sub if s.label == 1)
    print(f"  Subsampled: {len(tc_sub)} ({mal} mal, {len(tc_sub) - mal} ben)")

    metrics = SystemMetrics(system="phi4-mini-instruct", dataset="toxic-chat", total=len(tc_sub))
    category_stats: dict = {}
    for i, sample in enumerate(tc_sub):
        result = baseline.classify(sample.text)
        update_counts(metrics, sample, result.predicted_positive, 0.0, [], category_stats)
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(tc_sub)}...", flush=True)
    metrics = compute_metrics(metrics, category_stats)
    print(f"  -> Recall={metrics.recall:.1%} Prec={metrics.precision:.1%} F1={metrics.f1:.1%} FPR={metrics.fpr:.1%}")
    results.append(asdict(metrics))

    # Safeguard: subsample 500
    print("Loading safeguard...", flush=True)
    sg_samples = load_dataset_by_name("safeguard")
    sg_sub = stratified_subsample(sg_samples, 500)
    mal = sum(1 for s in sg_sub if s.label == 1)
    print(f"  Subsampled: {len(sg_sub)} ({mal} mal, {len(sg_sub) - mal} ben)")

    metrics = SystemMetrics(system="phi4-mini-instruct", dataset="safeguard", total=len(sg_sub))
    category_stats = {}
    for i, sample in enumerate(sg_sub):
        result = baseline.classify(sample.text)
        update_counts(metrics, sample, result.predicted_positive, 0.0, [], category_stats)
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(sg_sub)}...", flush=True)
    metrics = compute_metrics(metrics, category_stats)
    print(f"  -> Recall={metrics.recall:.1%} Prec={metrics.precision:.1%} F1={metrics.f1:.1%} FPR={metrics.fpr:.1%}")
    results.append(asdict(metrics))

    # Save
    out = Path("results/phi4_sampled_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults: {out}")


if __name__ == "__main__":
    main()
