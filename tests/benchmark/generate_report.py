"""Generate markdown benchmark report with head-to-head comparison.

Accuracy-only — no latency metrics (VM environment).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _ci_pct(ci: list[float] | None, n: int) -> str:
    """Render a [point, lo, hi] CI triple as 'P% ±H' rounded by sample size."""
    if not ci:
        return "—"
    point, lo, hi = ci
    dp = 0 if n < 300 else 1
    half = (hi - lo) / 2 * 100
    return f"{point * 100:.{dp}f}% ±{half:.{dp}f}"


def generate_report(results: Any, output_path: Path) -> None:
    """Generate a markdown benchmark report."""
    lines: list[str] = []
    metrics = results.metrics if hasattr(results, "metrics") else results["metrics"]
    timestamp = results.timestamp if hasattr(results, "timestamp") else results["timestamp"]
    hardware = results.hardware if hasattr(results, "hardware") else results["hardware"]
    iw_ver = results.inferwall_version if hasattr(results, "inferwall_version") else results["inferwall_version"]
    py_ver = results.python_version if hasattr(results, "python_version") else results["python_version"]

    seed = getattr(results, "seed", None) if hasattr(results, "seed") else results.get("seed")
    provenance = getattr(results, "provenance", None) if hasattr(results, "provenance") else results.get("provenance")

    lines.append("# InferenceWall Benchmark Report")
    lines.append("")
    lines.append(f"**Date**: {timestamp}")
    lines.append(f"**Hardware**: {hardware}")
    lines.append(f"**InferenceWall**: v{iw_ver}")
    lines.append(f"**Python**: {py_ver}")
    if seed is not None:
        lines.append(f"**Seed**: {seed}")
    lines.append("")

    # --- Dataset Summary ---
    lines.append("## Datasets")
    lines.append("")
    lines.append("All datasets are public HuggingFace datasets used as-is with no modifications.")
    lines.append("")
    lines.append("| Dataset | HuggingFace Source | Test Samples | Description |")
    lines.append("|---------|-------------------|-------------|-------------|")
    lines.append("| deepset | deepset/prompt-injections | 116 | Foundational PI benchmark |")
    lines.append("| jackhhao | jackhhao/jailbreak-classification | 262 | Balanced jailbreak detection |")
    lines.append("| toxic-chat | lmsys/toxic-chat (toxicchat0124) | 5,083 | Real user-AI traffic, jailbreak labels |")
    lines.append("| safeguard | xTRam1/safe-guard-prompt-injection | 2,060 | Broad PI coverage |")
    lines.append("")

    # --- Executive Summary ---
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| System | Dataset | Samples | Recall | Precision | F1 | FPR | Accuracy |")
    lines.append("|--------|---------|---------|--------|-----------|-----|-----|----------|")
    for m in metrics:
        lines.append(
            f"| {m['system']} | {m['dataset']} | {m['total']} | "
            f"{m['recall']:.1%} | {m['precision']:.1%} | "
            f"{m['f1']:.1%} | {m['fpr']:.1%} | {m['accuracy']:.1%} |"
        )
    lines.append("")

    # --- Statistical Summary (bootstrap 95% CIs + AUC) ---
    has_ci = any(m.get("ci") for m in metrics)
    if has_ci:
        lines.append("## Statistical Summary (95% bootstrap CIs)")
        lines.append("")
        lines.append(
            "Metrics shown as **point ± 95% CI** (2,000-resample percentile "
            "bootstrap, seeded). CI half-width rounds to whole percent for "
            "n<300 sets. ROC-AUC / PR-AUC are threshold-independent."
        )
        lines.append("")
        lines.append("| System | Dataset | n | Recall | Precision | F1 | FPR | ROC-AUC | PR-AUC |")
        lines.append("|--------|---------|---|--------|-----------|-----|-----|---------|--------|")
        for m in metrics:
            ci = m.get("ci") or {}
            auc = m.get("auc") or {}
            n = m["total"]
            lines.append(
                f"| {m['system']} | {m['dataset']} | {n} | "
                f"{_ci_pct(ci.get('recall'), n)} | {_ci_pct(ci.get('precision'), n)} | "
                f"{_ci_pct(ci.get('f1'), n)} | {_ci_pct(ci.get('fpr'), n)} | "
                f"{auc.get('roc_auc', '—')} | {auc.get('pr_auc', '—')} |"
            )
        lines.append("")

    # --- Per-attack-class split ---
    has_split = any(m.get("by_attack_class") for m in metrics)
    if has_split:
        lines.append("## Per-Attack-Class Breakdown")
        lines.append("")
        lines.append(
            "Recall split by attack class (injection / jailbreak); benign rows "
            "report FPR since recall is undefined for the negative class."
        )
        lines.append("")
        lines.append("| System | Dataset | Class | n | Recall | FPR |")
        lines.append("|--------|---------|-------|---|--------|-----|")
        for m in metrics:
            for cls, stats in sorted((m.get("by_attack_class") or {}).items()):
                rec = f"{stats['recall']:.1%}" if "recall" in stats else "—"
                fp = f"{stats['fpr']:.1%}" if "fpr" in stats else "—"
                lines.append(
                    f"| {m['system']} | {m['dataset']} | {cls} | "
                    f"{stats['n']} | {rec} | {fp} |"
                )
        lines.append("")

    # --- Threshold sweep (precision-recall table) ---
    has_sweep = any(m.get("pr_curve") for m in metrics)
    if has_sweep:
        lines.append("## Threshold Sweep (precision-recall)")
        lines.append("")
        lines.append(
            "Recall / precision / FPR across the score-threshold grid. The "
            "production inbound flag threshold is 4.0; rows bracket the "
            "operating point so the precision-recall trade-off is visible."
        )
        lines.append("")
        for m in metrics:
            sweep = m.get("pr_curve")
            if not sweep:
                continue
            lines.append(f"### {m['system']} — {m['dataset']}")
            lines.append("")
            lines.append("| Threshold | Recall | Precision | FPR |")
            lines.append("|-----------|--------|-----------|-----|")
            # Sample ~10 rows evenly so the table stays readable.
            step = max(1, len(sweep) // 10)
            for row in sweep[::step]:
                lines.append(
                    f"| {row['threshold']:.2f} | {row['recall']:.1%} | "
                    f"{row['precision']:.1%} | {row['fpr']:.1%} |"
                )
            lines.append("")

    # --- Head-to-Head Comparison ---
    datasets_seen = sorted(set(m["dataset"] for m in metrics))
    systems_seen = sorted(set(m["system"] for m in metrics))

    if len(systems_seen) > 1:
        lines.append("## Head-to-Head Comparison")
        lines.append("")

        for ds in datasets_seen:
            lines.append(f"### {ds}")
            lines.append("")
            lines.append("| Metric | " + " | ".join(systems_seen) + " |")
            lines.append("|--------|" + "|".join(["--------"] * len(systems_seen)) + "|")

            ds_metrics = {m["system"]: m for m in metrics if m["dataset"] == ds}

            for metric_name, key in [
                ("Recall", "recall"),
                ("Precision", "precision"),
                ("F1 Score", "f1"),
                ("False Positive Rate", "fpr"),
                ("Accuracy", "accuracy"),
                ("True Positives", "tp"),
                ("False Positives", "fp"),
                ("True Negatives", "tn"),
                ("False Negatives", "fn"),
            ]:
                vals = []
                for sys_name in systems_seen:
                    if sys_name in ds_metrics:
                        v = ds_metrics[sys_name][key]
                        if isinstance(v, float) and v <= 1.0 and key not in ("tp", "fp", "tn", "fn"):
                            vals.append(f"{v:.1%}")
                        else:
                            vals.append(str(v))
                    else:
                        vals.append("—")
                lines.append(f"| {metric_name} | " + " | ".join(vals) + " |")

            lines.append("")

    # --- Aggregate across datasets ---
    lines.append("## Aggregate Results (All Datasets Combined)")
    lines.append("")
    lines.append("| System | Total | TP | FP | TN | FN | Recall | Precision | F1 | FPR | Accuracy |")
    lines.append("|--------|-------|----|----|----|----|--------|-----------|-----|-----|----------|")

    for sys_name in systems_seen:
        sys_metrics = [m for m in metrics if m["system"] == sys_name]
        total = sum(m["total"] for m in sys_metrics)
        tp = sum(m["tp"] for m in sys_metrics)
        fp = sum(m["fp"] for m in sys_metrics)
        tn = sum(m["tn"] for m in sys_metrics)
        fn = sum(m["fn"] for m in sys_metrics)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        accuracy = (tp + tn) / total if total > 0 else 0
        lines.append(
            f"| {sys_name} | {total} | {tp} | {fp} | {tn} | {fn} | "
            f"{recall:.1%} | {precision:.1%} | {f1:.1%} | {fpr:.1%} | {accuracy:.1%} |"
        )
    lines.append("")

    # --- Detailed Results ---
    lines.append("## Detailed Results")
    lines.append("")
    for m in metrics:
        lines.append(f"### {m['system']} — {m['dataset']}")
        lines.append("")
        lines.append(f"- **Total**: {m['total']} (TP={m['tp']} FP={m['fp']} TN={m['tn']} FN={m['fn']})")
        lines.append(f"- **Recall**: {m['recall']:.1%}")
        lines.append(f"- **Precision**: {m['precision']:.1%}")
        lines.append(f"- **F1**: {m['f1']:.1%}")
        lines.append(f"- **FPR**: {m['fpr']:.1%}")
        lines.append(f"- **Accuracy**: {m['accuracy']:.1%}")
        lines.append("")

        if m.get("per_category"):
            lines.append("**Per-category:**")
            lines.append("")
            lines.append("| Category | Total | TP | FP | TN | FN | Recall | Precision |")
            lines.append("|----------|-------|----|----|----|-----|--------|-----------|")
            for cat, stats in sorted(m["per_category"].items()):
                lines.append(
                    f"| {cat} | {stats['total']} | {stats['tp']} | "
                    f"{stats['fp']} | {stats['tn']} | {stats['fn']} | "
                    f"{stats['recall']:.1%} | {stats['precision']:.1%} |"
                )
            lines.append("")

    # --- False Positive Analysis ---
    lines.append("## False Positive Analysis")
    lines.append("")
    any_fps = False
    for m in metrics:
        if m.get("false_positives"):
            any_fps = True
            lines.append(f"### {m['system']} — {m['dataset']} ({len(m['false_positives'])} FPs)")
            lines.append("")
            for fp in m["false_positives"][:15]:
                sigs = fp.get("sigs", [])
                sig_str = ", ".join(sigs) if sigs else "—"
                lines.append(f"- score={fp['score']} [{sig_str}]: `{fp['text']}`")
            if len(m["false_positives"]) > 15:
                lines.append(f"- ... and {len(m['false_positives']) - 15} more")
            lines.append("")
    if not any_fps:
        lines.append("No false positives across all systems and datasets.")
        lines.append("")

    # --- False Negative Analysis ---
    lines.append("## False Negative Analysis")
    lines.append("")
    any_fns = False
    for m in metrics:
        if m.get("false_negatives"):
            any_fns = True
            lines.append(f"### {m['system']} — {m['dataset']} ({len(m['false_negatives'])} FNs)")
            lines.append("")
            for fn in m["false_negatives"][:15]:
                lines.append(f"- [{fn.get('category', '?')}] score={fn['score']}: `{fn['text']}`")
            if len(m["false_negatives"]) > 15:
                lines.append(f"- ... and {len(m['false_negatives']) - 15} more")
            lines.append("")
    if not any_fns:
        lines.append("All attacks detected across all systems and datasets.")
        lines.append("")

    # --- Provenance ---
    if provenance:
        lines.append("## Reproducibility Provenance")
        lines.append("")
        lines.append(f"- **Bench commit**: `{provenance.get('bench_git_commit', 'unknown')}`")
        lines.append(f"- **Seed**: {provenance.get('seed', '—')}")
        pol = provenance.get("policy", {})
        if pol.get("thresholds"):
            t = pol["thresholds"]
            lines.append(
                f"- **Policy** `{pol.get('policy_name', '?')}` "
                f"({pol.get('signature_count', '?')} signatures): "
                f"inbound flag={t['inbound_flag']} block={t['inbound_block']}"
            )
        revs = provenance.get("dataset_revisions", {})
        if revs:
            lines.append("- **Dataset revisions** (pinned):")
            for name, meta in revs.items():
                lines.append(
                    f"    - `{name}` ({meta.get('hf_id', '?')}) "
                    f"@ `{meta.get('revision', 'unpinned')}`"
                )
        models = provenance.get("model_sha256", {})
        if models:
            lines.append("- **Model SHA256** (best-effort):")
            for path, digest in models.items():
                lines.append(f"    - `{path}`: `{digest[:16]}…`")
        lines.append("")

    # --- Methodology ---
    lines.append("## Methodology")
    lines.append("")
    lines.append("### Systems Under Test")
    lines.append("- **InferenceWall** (Lite/Standard): Multi-layered detection — heuristic rules, ML classifiers, semantic similarity")
    lines.append("- **Phi-4-mini-instruct**: Microsoft 3.8B parameter LLM (Q4_K_M GGUF), zero-shot classification")
    lines.append("")
    lines.append("### Decision Mapping")
    lines.append("- InferenceWall: `block` or `flag` → positive (threat detected); `allow` → negative")
    lines.append("- Phi-4-mini-instruct: response containing `UNSAFE` → positive; `SAFE` → negative")
    lines.append("")
    lines.append("### Datasets")
    lines.append("- All public HuggingFace datasets, used as-is with no modifications")
    lines.append("- No custom or hand-curated data — fully reproducible")
    lines.append("- Note: Latency measurements excluded (VM environment, not representative of production)")
    lines.append("")
    lines.append("### Reproducibility")
    lines.append("Dataset revisions are pinned in `tests/benchmark/DATASETS.lock`; "
                 "the global seed and full provenance are recorded above.")
    lines.append("```bash")
    lines.append("pip install inferwall datasets")
    lines.append("inferwall models install --profile standard")
    lines.append("PYTHONPATH=. python tests/benchmark/run_benchmark.py \\")
    lines.append("    --profiles standard --datasets deepset,jackhhao,safeguard \\")
    lines.append("    --skip-phi4 --seed 42")
    lines.append("```")
    lines.append("")

    output_path.write_text("\n".join(lines))
