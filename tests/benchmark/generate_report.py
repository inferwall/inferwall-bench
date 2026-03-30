"""Generate markdown benchmark report from JSON results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def generate_report(results: Any, output_path: Path) -> None:
    """Generate a markdown benchmark report."""
    lines: list[str] = []

    lines.append("# InferenceWall Benchmark Results")
    lines.append("")
    lines.append(f"**Generated**: {results.timestamp}")
    lines.append(f"**Hardware**: {results.hardware}")
    lines.append(f"**InferenceWall**: v{results.inferwall_version}")
    lines.append(f"**Python**: {results.python_version}")
    lines.append("")

    metrics = results.metrics

    # --- Executive Summary ---
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Profile | Dataset | Recall | FPR | Precision | F1 | p50 | p99 |")
    lines.append("|---------|---------|--------|-----|-----------|-----|-----|-----|")
    for m in metrics:
        lines.append(
            f"| {m['profile']} | {m['dataset']} | "
            f"{m['recall']:.1%} | {m['fpr']:.1%} | "
            f"{m['precision']:.1%} | {m['f1']:.1%} | "
            f"{m['latency_p50_ms']:.2f}ms | {m['latency_p99_ms']:.2f}ms |"
        )
    lines.append("")

    # --- Comparison Against Published Benchmarks ---
    lines.append("## Comparison Against Published Benchmarks")
    lines.append("")
    lines.append("> **Note**: Cross-benchmark comparisons are imperfect because datasets")
    lines.append("> and evaluation methodologies differ. Only comparisons on the same")
    lines.append("> dataset (e.g., deepset) are directly comparable.")
    lines.append("")
    lines.append("| Tool | Recall | FPR | Source |")
    lines.append("|------|--------|-----|--------|")

    for m in metrics:
        lines.append(
            f"| InferWall {m['profile'].title()} ({m['dataset']}) | "
            f"{m['recall']:.1%} | {m['fpr']:.1%} | This benchmark |"
        )

    lines.append("| LlamaFirewall PromptGuard 2 | 97.5% | 1.0% | Debenedetti et al. 2024 |")
    lines.append("| ProtectAI DeBERTa | 91.0% | ~23% | HuggingFace model card |")
    lines.append("| deepset DeBERTa | 99.1% | N/A | deepset blog |")
    lines.append("| Lakera Guard | 98%+ | <0.5% | Vendor claim (proprietary) |")
    lines.append("")

    # --- Confusion Matrix ---
    lines.append("## Detailed Results")
    lines.append("")
    for m in metrics:
        lines.append(f"### {m['profile'].title()} — {m['dataset']}")
        lines.append("")
        lines.append(f"- **Total samples**: {m['total']}")
        lines.append(f"- **TP**: {m['tp']} | **FP**: {m['fp']} | **TN**: {m['tn']} | **FN**: {m['fn']}")
        lines.append(f"- **Recall**: {m['recall']:.1%}")
        lines.append(f"- **False Positive Rate**: {m['fpr']:.1%}")
        lines.append(f"- **Precision**: {m['precision']:.1%}")
        lines.append(f"- **F1 Score**: {m['f1']:.1%}")
        lines.append(f"- **Accuracy**: {m['accuracy']:.1%}")
        lines.append(f"- **Latency**: p50={m['latency_p50_ms']:.2f}ms, "
                      f"p95={m['latency_p95_ms']:.2f}ms, "
                      f"p99={m['latency_p99_ms']:.2f}ms, "
                      f"mean={m['latency_mean_ms']:.2f}ms")
        lines.append("")

        # Per-category breakdown
        if m.get("per_category"):
            lines.append("**Per-category breakdown:**")
            lines.append("")
            lines.append("| Category | Total | TP | FN | Recall |")
            lines.append("|----------|-------|----|----|--------|")
            for cat, stats in sorted(m["per_category"].items()):
                lines.append(
                    f"| {cat} | {stats['total']} | {stats['tp']} | "
                    f"{stats['fn']} | {stats['recall']:.1%} |"
                )
            lines.append("")

    # --- False Positive Analysis ---
    lines.append("## False Positive Analysis")
    lines.append("")
    lines.append("Benign prompts incorrectly flagged as threats:")
    lines.append("")
    any_fps = False
    for m in metrics:
        if m.get("false_positives"):
            any_fps = True
            lines.append(f"### {m['profile'].title()} — {m['dataset']}")
            lines.append("")
            for fp in m["false_positives"][:20]:
                lines.append(f"- **score={fp['score']}** sigs={fp['sigs']}: `{fp['text']}`")
            lines.append("")
    if not any_fps:
        lines.append("No false positives detected across all profiles and datasets.")
        lines.append("")

    # --- False Negative Analysis ---
    lines.append("## False Negative Analysis")
    lines.append("")
    lines.append("Attack prompts that were not detected:")
    lines.append("")
    any_fns = False
    for m in metrics:
        if m.get("false_negatives"):
            any_fns = True
            lines.append(f"### {m['profile'].title()} — {m['dataset']}")
            lines.append("")
            for fn in m["false_negatives"][:20]:
                lines.append(f"- **[{fn.get('category', '?')}]** score={fn['score']}: `{fn['text']}`")
            lines.append("")
    if not any_fns:
        lines.append("All attack prompts were detected across all profiles and datasets.")
        lines.append("")

    # --- Methodology ---
    lines.append("## Methodology")
    lines.append("")
    lines.append("### Decision Mapping")
    lines.append("- `block` or `flag` → **positive** (detected as threat)")
    lines.append("- `allow` → **negative** (not detected)")
    lines.append("")
    lines.append("### Measurement")
    lines.append("- Latency measured per-prompt using `time.perf_counter()`")
    lines.append("- First 3 calls excluded as warm-up (model/signature loading)")
    lines.append("- All measurements are single-threaded, steady-state")
    lines.append("")
    lines.append("### Datasets")
    lines.append("- **deepset**: deepset/prompt-injections (HuggingFace) — most widely used benchmark")
    lines.append("- **jasper**: JasperLS/prompt-injections (HuggingFace) — diverse attack types")
    lines.append("- **custom**: Hand-curated 100 prompts (50 malicious, 50 benign edge cases)")
    lines.append("- **owasp**: OWASP LLM Top 10 2025 coverage test (50 prompts)")
    lines.append("")
    lines.append("### Reproducibility")
    lines.append("```bash")
    lines.append("pip install inferwall-bench")
    lines.append("python tests/benchmark/run_benchmark.py --profiles lite --datasets custom,owasp")
    lines.append("```")
    lines.append("")

    output_path.write_text("\n".join(lines))
