# inferwall-bench

Benchmark harness for [InferenceWall](https://github.com/inferwall/inferwall) — measures detection performance, false positive rates, and latency across deployment profiles.

## Quick Start

```bash
pip install inferwall
git clone https://github.com/inferwall/inferwall-bench.git
cd inferwall-bench

# Run quick benchmark (Lite profile, local datasets)
python tests/benchmark/run_benchmark.py --profiles lite --datasets custom,owasp

# Run full benchmark with HuggingFace datasets
pip install datasets
python tests/benchmark/run_benchmark.py --profiles lite --datasets deepset,jackhhao,toxic-chat,safeguard,custom,owasp
```

## HuggingFace Token

Some datasets may require authentication. Set your HuggingFace token as an environment variable:

```bash
export HF_TOKEN=hf_your_token_here
```

You can generate a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). The token is passed automatically to all dataset loaders.

## Datasets

### HuggingFace Datasets

| Name | HuggingFace ID | Total Samples | Malicious | Benign | Description |
|------|----------------|---------------|-----------|--------|-------------|
| deepset | deepset/prompt-injections | 116 | 60 | 56 | Foundational prompt injection benchmark |
| jackhhao | jackhhao/jailbreak-classification | 262 | 139 | 123 | Balanced jailbreak detection |
| toxic-chat | lmsys/toxic-chat (toxicchat0124) | 5,083 | 91 | 4,992 | Real user-AI traffic with jailbreak labels |
| safeguard | xTRam1/safe-guard-prompt-injection | 2,060 | 650 | 1,410 | Broad prompt injection coverage |

### Local Datasets

| Name | Samples | Description |
|------|---------|-------------|
| custom | 100 | Hand-curated (50 malicious + 50 benign edge cases) |
| owasp | 50 | OWASP LLM Top 10 2025 coverage |

## Metrics

For each profile × dataset combination:

- **Recall** (True Positive Rate): % of attacks caught
- **FPR** (False Positive Rate): % of benign prompts incorrectly flagged
- **Precision**: of all flagged prompts, % that were actual attacks
- **F1 Score**: harmonic mean of precision and recall
- **Latency**: p50, p95, p99 in milliseconds

## Profiles

| Profile | Engines | Expected Latency |
|---------|---------|-----------------|
| Lite | Heuristic (Rust) | <0.3ms p99 |
| Standard | + ONNX classifier + FAISS semantic | <80ms p99 |
| Full | + LLM-judge | <2s p99 |

## Usage

```bash
# All options
python tests/benchmark/run_benchmark.py \
    --profiles lite,standard,full \
    --datasets deepset,jasper,custom,owasp \
    --output results/all.json \
    --report results/benchmark_report.md

# Or use justfile
just benchmark-lite
just benchmark-quick
just benchmark-all
```

## Report

After running, find the report at `results/benchmark_report.md`. It includes:
- Executive summary table
- Comparison against published benchmarks (LlamaFirewall, ProtectAI, deepset)
- Per-category breakdown
- False positive analysis
- False negative analysis
- Methodology section

## License

Apache-2.0
