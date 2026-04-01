#!/usr/bin/env python3
"""InferenceWall benchmark runner — head-to-head vs Phi-4-mini-instruct.

Accuracy-only benchmark (no latency metrics — VM environment).

Usage:
    python tests/benchmark/run_benchmark.py \
        --datasets deepset,jackhhao,toxic-chat,safeguard \
        --phi4-model /tmp/models/Phi-4-mini-instruct-Q4_K_M.gguf \
        --output results/benchmark.json \
        --report results/benchmark_report.md
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.benchmark.loaders import (
    ALL_STANDARD_DATASETS,
    BenchmarkSample,
    load_dataset_by_name,
)


@dataclass
class SystemMetrics:
    """Metrics for one system x dataset combination."""

    system: str
    dataset: str
    total: int = 0
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    recall: float = 0.0
    precision: float = 0.0
    f1: float = 0.0
    fpr: float = 0.0
    accuracy: float = 0.0
    false_positives: list[dict] = field(default_factory=list)
    false_negatives: list[dict] = field(default_factory=list)
    per_category: dict[str, dict] = field(default_factory=dict)


@dataclass
class BenchmarkResults:
    """Full benchmark results."""

    timestamp: str = ""
    hardware: str = ""
    python_version: str = ""
    inferwall_version: str = ""
    phi4_model: str = ""
    metrics: list[dict] = field(default_factory=list)


def compute_metrics(
    metrics: SystemMetrics, category_stats: dict
) -> SystemMetrics:
    """Compute derived metrics from raw counts."""
    if metrics.tp + metrics.fn > 0:
        metrics.recall = metrics.tp / (metrics.tp + metrics.fn)
    if metrics.tp + metrics.fp > 0:
        metrics.precision = metrics.tp / (metrics.tp + metrics.fp)
    if metrics.precision + metrics.recall > 0:
        metrics.f1 = (
            2 * metrics.precision * metrics.recall / (metrics.precision + metrics.recall)
        )
    if metrics.fp + metrics.tn > 0:
        metrics.fpr = metrics.fp / (metrics.fp + metrics.tn)
    if metrics.total > 0:
        metrics.accuracy = (metrics.tp + metrics.tn) / metrics.total

    for cat, stats in category_stats.items():
        cat_recall = 0.0
        cat_precision = 0.0
        if stats["tp"] + stats["fn"] > 0:
            cat_recall = stats["tp"] / (stats["tp"] + stats["fn"])
        if stats["tp"] + stats["fp"] > 0:
            cat_precision = stats["tp"] / (stats["tp"] + stats["fp"])
        metrics.per_category[cat] = {
            **stats,
            "recall": round(cat_recall, 4),
            "precision": round(cat_precision, 4),
        }

    return metrics


def update_counts(
    metrics: SystemMetrics,
    sample: BenchmarkSample,
    predicted_positive: bool,
    score: float,
    sigs: list[str],
    category_stats: dict,
) -> None:
    """Update confusion matrix counts."""
    cat = sample.category or "unknown"
    if cat not in category_stats:
        category_stats[cat] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0}
    category_stats[cat]["total"] += 1

    if sample.label == 1 and predicted_positive:
        metrics.tp += 1
        category_stats[cat]["tp"] += 1
    elif sample.label == 0 and predicted_positive:
        metrics.fp += 1
        category_stats[cat]["fp"] += 1
        metrics.false_positives.append(
            {"text": sample.text[:120], "score": score, "sigs": sigs}
        )
    elif sample.label == 0 and not predicted_positive:
        metrics.tn += 1
        category_stats[cat]["tn"] += 1
    elif sample.label == 1 and not predicted_positive:
        metrics.fn += 1
        category_stats[cat]["fn"] += 1
        metrics.false_negatives.append(
            {"text": sample.text[:120], "score": score, "category": sample.category}
        )


def run_inferwall(
    profile: str, dataset_name: str, samples: list[BenchmarkSample]
) -> SystemMetrics:
    """Run InferenceWall on a dataset."""
    import inferwall

    os.environ["IW_PROFILE"] = profile
    inferwall._default_pipeline = None

    # Warm-up
    for _ in range(3):
        inferwall.scan_input("warm up call")

    system_name = f"inferwall-{profile}"
    metrics = SystemMetrics(system=system_name, dataset=dataset_name, total=len(samples))
    category_stats: dict[str, dict] = {}

    for i, sample in enumerate(samples):
        result = inferwall.scan_input(sample.text)
        predicted_positive = result.decision in ("flag", "block")
        sigs = [m["signature_id"] for m in result.matches]

        update_counts(metrics, sample, predicted_positive, result.score, sigs, category_stats)

        if (i + 1) % 500 == 0:
            print(f"    {i + 1}/{len(samples)}...", flush=True)

    return compute_metrics(metrics, category_stats)


def run_phi4(
    model_path: str, dataset_name: str, samples: list[BenchmarkSample]
) -> SystemMetrics:
    """Run Phi-4-mini-instruct baseline on a dataset."""
    from tests.benchmark.phi4_baseline import Phi4Baseline

    baseline = Phi4Baseline(model_path)
    baseline.warmup(3)

    metrics = SystemMetrics(
        system="phi4-mini-instruct", dataset=dataset_name, total=len(samples)
    )
    category_stats: dict[str, dict] = {}

    for i, sample in enumerate(samples):
        result = baseline.classify(sample.text)

        update_counts(metrics, sample, result.predicted_positive, 0.0, [], category_stats)

        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(samples)}...", flush=True)

    return compute_metrics(metrics, category_stats)


def get_hardware_info() -> str:
    cpu = platform.processor() or platform.machine()
    return f"{platform.system()} {platform.release()}, {cpu}, Python {platform.python_version()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="InferenceWall Benchmark Runner")
    parser.add_argument(
        "--datasets",
        default=",".join(ALL_STANDARD_DATASETS),
        help="Comma-separated datasets",
    )
    parser.add_argument(
        "--profiles",
        default="lite,standard",
        help="InferenceWall profiles to test",
    )
    parser.add_argument(
        "--phi4-model",
        default="/tmp/models/Phi-4-mini-instruct-Q4_K_M.gguf",
        help="Path to Phi-4-mini-instruct GGUF model",
    )
    parser.add_argument("--skip-phi4", action="store_true")
    parser.add_argument("--skip-inferwall", action="store_true")
    parser.add_argument("--output", default="results/benchmark.json")
    parser.add_argument("--report", default="results/benchmark_report.md")
    args = parser.parse_args()

    dataset_names = [d.strip() for d in args.datasets.split(",")]
    profiles = [p.strip() for p in args.profiles.split(",")]

    import inferwall

    print("=" * 60)
    print("InferenceWall Benchmark v2.0 (accuracy-only)")
    print("=" * 60)
    print(f"InferenceWall: v{inferwall.__version__}")
    print(f"Hardware: {get_hardware_info()}")
    print(f"Datasets: {dataset_names}")
    print(f"Profiles: {profiles}")
    print(f"Phi-4: {args.phi4_model if not args.skip_phi4 else 'SKIPPED'}")
    print()

    # Load datasets
    datasets: dict[str, list[BenchmarkSample]] = {}
    for name in dataset_names:
        print(f"Loading {name}...", end=" ", flush=True)
        samples = load_dataset_by_name(name)
        if samples:
            datasets[name] = samples
            malicious = sum(1 for s in samples if s.label == 1)
            print(f"{len(samples)} samples ({malicious} mal, {len(samples) - malicious} ben)")
        else:
            print("SKIPPED")
    print()

    all_metrics: list[SystemMetrics] = []

    # Run InferenceWall
    if not args.skip_inferwall:
        for profile in profiles:
            print(f"=== InferenceWall ({profile}) ===")
            for ds_name, samples in datasets.items():
                print(f"  {ds_name} ({len(samples)} samples)...", flush=True)
                m = run_inferwall(profile, ds_name, samples)
                all_metrics.append(m)
                print(
                    f"    -> Recall={m.recall:.1%} Prec={m.precision:.1%} "
                    f"F1={m.f1:.1%} FPR={m.fpr:.1%} Acc={m.accuracy:.1%}"
                )
            print()

    # Run Phi-4 baseline
    if not args.skip_phi4 and Path(args.phi4_model).exists():
        print("=== Phi-4-mini-instruct (zero-shot) ===")
        for ds_name, samples in datasets.items():
            print(f"  {ds_name} ({len(samples)} samples)...", flush=True)
            m = run_phi4(args.phi4_model, ds_name, samples)
            all_metrics.append(m)
            print(
                f"    -> Recall={m.recall:.1%} Prec={m.precision:.1%} "
                f"F1={m.f1:.1%} FPR={m.fpr:.1%} Acc={m.accuracy:.1%}"
            )
        print()
    elif not args.skip_phi4:
        print(f"WARNING: Phi-4 model not found at {args.phi4_model}, skipping")
        print()

    # Save results
    results = BenchmarkResults(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        hardware=get_hardware_info(),
        python_version=platform.python_version(),
        inferwall_version=inferwall.__version__,
        phi4_model=args.phi4_model if not args.skip_phi4 else "",
        metrics=[asdict(m) for m in all_metrics],
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(results), indent=2))
    print(f"Results: {output_path}")

    # Generate report
    from tests.benchmark.generate_report import generate_report

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results, report_path)
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
