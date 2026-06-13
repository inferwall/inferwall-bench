"""Adversarial-evasion robustness suite.

Measures how much detection recall InferenceWall retains when known attacks are
wrapped or obfuscated by the mutators in ``mutators.py``.

Method:

1. Load malicious samples from one or more datasets (default deepset+jackhhao).
2. Establish a *baseline*: scan each attack through the real STANDARD-profile
   Pipeline and keep only the ones currently caught (decision in flag/block).
   These are the attacks the firewall already detects — the only ones where a
   mutator can cause a *regression* to measure.
3. For each mutator, transform every baseline-caught attack, re-scan, and
   compute **recall retained** = (mutated attacks still caught) / (baseline
   caught). 100% means the transform did not evade anything.
4. Emit a markdown "robustness matrix" (rows = transforms).

The headline this proves: the recent preprocessing de-obfuscation work
(base64/hex decode + Unicode confusable folding) keeps recall high under
``base64_wrap``, ``hex_wrap`` and ``homoglyph_sub``. Any transform that drops
recall below ``--floor`` (default 70%) is flagged as a signature/engine
follow-up.

Run:
    PYTHONPATH=. .../python tests/benchmark/robustness.py \
        --datasets deepset,jackhhao --profile standard \
        --output results/robustness.json --report results/robustness.md
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

from tests.benchmark.loaders import load_dataset_by_name
from tests.benchmark.mutators import MUTATORS, SEED, apply_mutator

FLOOR_DEFAULT = 0.70


def _scan(text: str):
    import inferwall

    return inferwall.scan_input(text)


def _is_caught(text: str) -> bool:
    return _scan(text).decision in ("flag", "block")


def collect_baseline(dataset_names: list[str], limit: int | None) -> list[str]:
    """Return malicious samples the STANDARD pipeline currently catches."""
    attacks: list[str] = []
    for name in dataset_names:
        for s in load_dataset_by_name(name):
            if s.label == 1 and s.text.strip():
                attacks.append(s.text)
    if limit:
        attacks = attacks[:limit]

    caught: list[str] = []
    for i, text in enumerate(attacks):
        if _is_caught(text):
            caught.append(text)
        if (i + 1) % 100 == 0:
            print(f"    baseline {i + 1}/{len(attacks)} (caught {len(caught)})", flush=True)
    return caught


def run_robustness(
    dataset_names: list[str], limit: int | None
) -> dict:
    """Build the robustness matrix. Returns a JSON-serializable dict."""
    print(f"Establishing baseline on {dataset_names}...", flush=True)
    baseline = collect_baseline(dataset_names, limit)
    n = len(baseline)
    print(f"Baseline: {n} attacks currently caught by STANDARD profile.\n")
    if n == 0:
        raise SystemExit("No baseline attacks caught — cannot measure robustness.")

    rows: list[dict] = []
    for name in MUTATORS:
        retained = 0
        examples_evaded: list[str] = []
        for text in baseline:
            mutated = apply_mutator(name, text)
            if _is_caught(mutated):
                retained += 1
            elif len(examples_evaded) < 3:
                examples_evaded.append(text[:100])
        recall_retained = retained / n
        rows.append(
            {
                "transform": name,
                "baseline": n,
                "retained": retained,
                "recall_retained": round(recall_retained, 4),
                "evaded_examples": examples_evaded,
            }
        )
        flag = "" if recall_retained >= FLOOR_DEFAULT else "  <-- BELOW FLOOR"
        print(f"  {name:24s} retained {retained}/{n} = {recall_retained:6.1%}{flag}", flush=True)

    import inferwall

    return {
        "kind": "robustness",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seed": SEED,
        "profile": os.environ.get("IW_PROFILE", "standard"),
        "inferwall_version": inferwall.__version__,
        "python_version": platform.python_version(),
        "datasets": dataset_names,
        "baseline_caught": n,
        "floor": FLOOR_DEFAULT,
        "matrix": rows,
    }


def render_markdown(result: dict, floor: float) -> str:
    lines: list[str] = []
    lines.append("# InferenceWall Robustness Matrix (adversarial evasion)")
    lines.append("")
    lines.append(f"**Profile**: {result['profile']}  ")
    lines.append(f"**InferenceWall**: v{result['inferwall_version']}  ")
    lines.append(f"**Datasets**: {', '.join(result['datasets'])}  ")
    lines.append(f"**Seed**: {result['seed']}  ")
    lines.append(f"**Baseline attacks caught**: {result['baseline_caught']}  ")
    lines.append(f"**Floor**: {floor:.0%} recall retained")
    lines.append("")
    lines.append(
        "Each row applies one mutator to every baseline-caught attack and "
        "re-scans. *Recall retained* is the fraction still detected — 100% "
        "means the evasion failed."
    )
    lines.append("")
    lines.append("| Transform | Retained | Recall retained | Status |")
    lines.append("|-----------|----------|-----------------|--------|")
    for row in result["matrix"]:
        rr = row["recall_retained"]
        status = "ok" if rr >= floor else "**FOLLOW-UP**"
        lines.append(
            f"| `{row['transform']}` | {row['retained']}/{row['baseline']} "
            f"| {rr:.1%} | {status} |"
        )
    lines.append("")

    below = [r for r in result["matrix"] if r["recall_retained"] < floor]
    if below:
        lines.append("## Follow-ups (transforms below floor)")
        lines.append("")
        for r in below:
            lines.append(
                f"- **`{r['transform']}`** retained only {r['recall_retained']:.1%}. "
                "Sample attacks that evaded:"
            )
            for ex in r["evaded_examples"]:
                lines.append(f"    - `{ex}`")
        lines.append("")
    else:
        lines.append("All transforms retained recall at or above the floor. "
                     "No signature/engine follow-up required.")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Robustness / adversarial-evasion suite")
    parser.add_argument("--datasets", default="deepset,jackhhao")
    parser.add_argument("--profile", default="standard")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap baseline attacks (for a faster run)")
    parser.add_argument("--floor", type=float, default=FLOOR_DEFAULT)
    parser.add_argument("--output", default="results/robustness.json")
    parser.add_argument("--report", default="results/robustness.md")
    args = parser.parse_args()

    os.environ["IW_PROFILE"] = args.profile
    import inferwall

    inferwall._default_pipeline = None
    # Warm-up so model load time is not attributed to the first scan.
    for _ in range(3):
        inferwall.scan_input("warm up call")

    dataset_names = [d.strip() for d in args.datasets.split(",")]
    result = run_robustness(dataset_names, args.limit)
    result["floor"] = args.floor

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(f"\nResults: {out}")

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_markdown(result, args.floor))
    print(f"Report:  {report}")


if __name__ == "__main__":
    main()
