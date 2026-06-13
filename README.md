# inferwall-bench

Benchmark harness for [InferenceWall](https://github.com/inferwall/inferwall) — measures detection accuracy (recall, precision, F1, FPR) with statistical confidence intervals, an adversarial-evasion robustness suite, and reproducibility pinning across deployment profiles.

## Quick Start

```bash
pip install inferwall datasets
git clone https://github.com/inferwall/inferwall-bench.git
cd inferwall-bench

# Fast, model-free smoke (Lite profile, local corpora) — the same gate CI runs
PYTHONPATH=. python tests/benchmark/smoke.py

# Standard headline benchmark (downloads the standard ML profile)
inferwall models install --profile standard
PYTHONPATH=. python tests/benchmark/run_benchmark.py \
    --profiles standard --datasets deepset,jackhhao,safeguard --skip-phi4
```

## HuggingFace Token

Some datasets may require authentication. Set your HuggingFace token as an environment variable:

```bash
export HF_TOKEN=hf_your_token_here
```

You can generate a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). The token is passed automatically to all dataset loaders.

## Datasets

Dataset revisions are pinned in [`tests/benchmark/DATASETS.lock`](tests/benchmark/DATASETS.lock) and passed to `load_dataset(..., revision=<sha>)` so an upstream edit cannot silently move the headline. Regenerate with `python tests/benchmark/provenance.py --refresh-lock`.

### HuggingFace Datasets

| Name | HuggingFace ID | Test Samples | Description |
|------|----------------|--------------|-------------|
| deepset | deepset/prompt-injections | 116 | Foundational prompt injection benchmark |
| jackhhao | jackhhao/jailbreak-classification | 262 | Balanced jailbreak detection |
| toxic-chat | lmsys/toxic-chat (toxicchat0124) | 5,083 | Real user-AI traffic with jailbreak labels |
| safeguard | xTRam1/safe-guard-prompt-injection | 2,060 | Broad prompt injection coverage |

### Local Corpora

| Name | Samples | Description |
|------|---------|-------------|
| realistic-benign | 150 | Attack-adjacent but benign developer/security/RAG traffic — measures precision under realistic load (FPR only) |
| smoke_malicious | 10 | Canonical attacks the lite regex floor must keep catching (CI gate, not a loader) |

## Metrics

For each profile × dataset combination the harness reports:

- **Recall / Precision / F1 / FPR** as **point ± 95% bootstrap CI** (2,000 resamples, seeded). CI half-width is rounded to a precision justified by sample size (whole percent for n<300).
- **ROC-AUC and PR-AUC** — threshold-independent ranking quality.
- **Threshold sweep** — recall/precision/FPR across a score-threshold grid, so the operating point's precision-recall trade-off is visible.
- **Per-attack-class split** — recall broken out by injection vs jailbreak; benign reports FPR.

> Accuracy-only: latency is intentionally not measured (the reference environment is a VM, not representative of production).

## Adversarial robustness suite

`tests/benchmark/robustness.py` measures how much detection recall survives an evasion attempt. It takes the attacks the **standard** profile currently catches, applies each deterministic mutator from `tests/benchmark/mutators.py` (base64/hex/rot13/url wrapping, leetspeak, zero-width insertion, homoglyph substitution, NFKC fullwidth, whitespace, sentence shuffle), re-scans, and reports **recall retained** per transform as a robustness matrix. Any transform below the floor (default 70%) is flagged as a signature/engine follow-up.

```bash
PYTHONPATH=. python tests/benchmark/robustness.py \
    --datasets deepset,jackhhao --profile standard \
    --output results/robustness.json --report results/robustness.md
```

## Profiles

| Profile | Engines |
|---------|---------|
| Lite | Heuristic (Rust regex floor) |
| Standard | + ONNX classifier + FAISS semantic |
| Full | + LLM-judge |

## CI regression gate

`.github/workflows/benchmark-smoke.yml` runs `tests/benchmark/smoke.py` on every PR: the **lite** profile only (no model downloads, runs in well under three minutes). It fails if lite recall on `data/smoke_malicious.jsonl` drops below the floor, or the false-positive rate on `data/realistic_benign.jsonl` rises above the ceiling. Both thresholds live in `tests/benchmark/regression_baseline.json` and should only be changed deliberately after reviewing the new numbers.

## Reproducibility

Every results JSON embeds a provenance block: pinned dataset revisions, the active policy and thresholds, best-effort model-file SHA256s, the bench git commit, and the global seed. A `--seed` flag (default 42) threads through all sampling, shuffling, and bootstrap resampling.

## Report

After running, find the report at the `--report` path. It includes:
- Executive summary + statistical summary (CIs, AUC)
- Per-attack-class breakdown
- Threshold sweep (precision-recall)
- Head-to-head comparison (when multiple systems run)
- False positive / false negative analysis
- Reproducibility provenance + methodology

## License

Apache-2.0
