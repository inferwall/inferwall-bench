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
python tests/benchmark/run_benchmark.py --profiles lite --datasets deepset,custom,owasp
```

## Datasets

| Dataset | Source | Samples | Description |
|---------|--------|---------|-------------|
| deepset | [HuggingFace](https://huggingface.co/datasets/deepset/prompt-injections) | ~662 | Most widely used benchmark |
| jasper | [HuggingFace](https://huggingface.co/datasets/JasperLS/prompt-injections) | varies | Diverse attack types |
| custom | Local | 100 | Hand-curated (50 malicious + 50 benign edge cases) |
| owasp | Local | 50 | OWASP LLM Top 10 2025 coverage |

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
