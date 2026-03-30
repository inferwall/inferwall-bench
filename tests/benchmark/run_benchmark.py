#!/usr/bin/env python3
"""InferenceWall benchmark runner.

Usage:
    python tests/benchmark/run_benchmark.py \
        --profiles lite,standard,full \
        --datasets deepset,custom,owasp \
        --output results/benchmark_results.json \
        --report results/benchmark_report.md
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.benchmark.datasets import BenchmarkSample, load_dataset_by_name


@dataclass
class PromptResult:
    """Result of scanning a single prompt."""

    text_preview: str
    true_label: int
    predicted_positive: bool
    decision: str
    score: float
    matched_signatures: list[str]
    latency_ms: float
    category: str = ""


@dataclass
class DatasetMetrics:
    """Aggregated metrics for one dataset × profile combination."""

    profile: str
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
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_mean_ms: float = 0.0
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
    metrics: list[dict] = field(default_factory=list)


def scan_prompt(text: str) -> tuple[str, float, list[str], float]:
    """Scan a prompt and return (decision, score, signatures, latency_ms)."""
    import inferwall

    start = time.perf_counter()
    result = inferwall.scan_input(text)
    elapsed_ms = (time.perf_counter() - start) * 1000

    sigs = [m["signature_id"] for m in result.matches]
    return result.decision, result.score, sigs, elapsed_ms


def run_dataset(
    profile: str,
    dataset_name: str,
    samples: list[BenchmarkSample],
    warmup: int = 3,
) -> DatasetMetrics:
    """Run benchmark on a single dataset for a single profile."""
    import inferwall

    # Warm-up calls (exclude from measurement)
    for _ in range(warmup):
        inferwall.scan_input("warm up call")

    metrics = DatasetMetrics(profile=profile, dataset=dataset_name, total=len(samples))
    latencies: list[float] = []
    category_stats: dict[str, dict[str, int]] = {}

    for sample in samples:
        decision, score, sigs, latency_ms = scan_prompt(sample.text)

        # Map decision to binary: flag or block = positive
        predicted_positive = decision in ("flag", "block")

        latencies.append(latency_ms)

        # Confusion matrix
        if sample.label == 1 and predicted_positive:
            metrics.tp += 1
        elif sample.label == 0 and predicted_positive:
            metrics.fp += 1
            metrics.false_positives.append(
                {"text": sample.text[:100], "score": score, "sigs": sigs}
            )
        elif sample.label == 0 and not predicted_positive:
            metrics.tn += 1
        elif sample.label == 1 and not predicted_positive:
            metrics.fn += 1
            metrics.false_negatives.append(
                {
                    "text": sample.text[:100],
                    "score": score,
                    "category": sample.category,
                }
            )

        # Per-category tracking
        cat = sample.category or "unknown"
        if cat not in category_stats:
            category_stats[cat] = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0}
        category_stats[cat]["total"] += 1
        if sample.label == 1 and predicted_positive:
            category_stats[cat]["tp"] += 1
        elif sample.label == 0 and predicted_positive:
            category_stats[cat]["fp"] += 1
        elif sample.label == 0 and not predicted_positive:
            category_stats[cat]["tn"] += 1
        elif sample.label == 1 and not predicted_positive:
            category_stats[cat]["fn"] += 1

    # Calculate metrics
    if metrics.tp + metrics.fn > 0:
        metrics.recall = metrics.tp / (metrics.tp + metrics.fn)
    if metrics.tp + metrics.fp > 0:
        metrics.precision = metrics.tp / (metrics.tp + metrics.fp)
    if metrics.precision + metrics.recall > 0:
        metrics.f1 = 2 * metrics.precision * metrics.recall / (metrics.precision + metrics.recall)
    if metrics.fp + metrics.tn > 0:
        metrics.fpr = metrics.fp / (metrics.fp + metrics.tn)
    if metrics.total > 0:
        metrics.accuracy = (metrics.tp + metrics.tn) / metrics.total

    # Latency percentiles
    if latencies:
        sorted_lat = sorted(latencies)
        metrics.latency_mean_ms = statistics.mean(latencies)
        metrics.latency_p50_ms = sorted_lat[len(sorted_lat) // 2]
        metrics.latency_p95_ms = sorted_lat[int(len(sorted_lat) * 0.95)]
        metrics.latency_p99_ms = sorted_lat[int(len(sorted_lat) * 0.99)]

    # Per-category metrics
    for cat, stats in category_stats.items():
        cat_recall = 0.0
        if stats["tp"] + stats["fn"] > 0:
            cat_recall = stats["tp"] / (stats["tp"] + stats["fn"])
        metrics.per_category[cat] = {
            **stats,
            "recall": round(cat_recall, 4),
        }

    return metrics


def get_hardware_info() -> str:
    """Get system hardware description."""
    cpu = platform.processor() or platform.machine()
    return f"{platform.system()} {platform.release()}, {cpu}, Python {platform.python_version()}"


def main() -> None:
    parser = argparse.ArgumentParser(description="InferenceWall Benchmark Runner")
    parser.add_argument(
        "--profiles",
        default="lite",
        help="Comma-separated profiles to test (lite,standard,full)",
    )
    parser.add_argument(
        "--datasets",
        default="custom,owasp",
        help="Comma-separated datasets (deepset,jasper,custom,owasp)",
    )
    parser.add_argument(
        "--output",
        default="results/benchmark_results.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--report",
        default="results/benchmark_report.md",
        help="Output markdown report path",
    )
    args = parser.parse_args()

    profiles = [p.strip() for p in args.profiles.split(",")]
    dataset_names = [d.strip() for d in args.datasets.split(",")]

    import inferwall

    print(f"InferenceWall Benchmark v0.1.0")
    print(f"InferenceWall version: {inferwall.__version__}")
    print(f"Hardware: {get_hardware_info()}")
    print(f"Profiles: {profiles}")
    print(f"Datasets: {dataset_names}")
    print()

    # Load datasets
    datasets: dict[str, list[BenchmarkSample]] = {}
    for name in dataset_names:
        print(f"Loading dataset: {name}...")
        samples = load_dataset_by_name(name)
        if samples:
            datasets[name] = samples
            malicious = sum(1 for s in samples if s.label == 1)
            print(f"  Loaded {len(samples)} samples ({malicious} malicious, {len(samples) - malicious} benign)")
        else:
            print(f"  Skipped (no data)")
    print()

    # Run benchmarks
    all_metrics: list[DatasetMetrics] = []
    for profile in profiles:
        print(f"=== Profile: {profile} ===")
        os.environ["IW_PROFILE"] = profile
        # Reset pipeline singleton
        inferwall._default_pipeline = None

        for ds_name, samples in datasets.items():
            print(f"  Running {ds_name} ({len(samples)} samples)...", end=" ", flush=True)
            metrics = run_dataset(profile, ds_name, samples)
            all_metrics.append(metrics)
            print(
                f"Recall={metrics.recall:.1%} FPR={metrics.fpr:.1%} "
                f"F1={metrics.f1:.1%} p99={metrics.latency_p99_ms:.2f}ms"
            )
        print()

    # Save results
    results = BenchmarkResults(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        hardware=get_hardware_info(),
        python_version=platform.python_version(),
        inferwall_version=inferwall.__version__,
        metrics=[asdict(m) for m in all_metrics],
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(results), indent=2))
    print(f"Results saved to {output_path}")

    # Generate report
    from tests.benchmark.generate_report import generate_report

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results, report_path)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
