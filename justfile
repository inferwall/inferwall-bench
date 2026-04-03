# InferenceWall Benchmark Harness

default:
    @just --list

# Run Lite profile benchmark (fast, no ML deps)
benchmark-lite:
    python tests/benchmark/run_benchmark.py --profiles lite --datasets custom,owasp --output results/lite.json --report results/lite_report.md

# Run Standard profile benchmark (requires ONNX models)
benchmark-standard:
    python tests/benchmark/run_benchmark.py --profiles standard --datasets custom,owasp --output results/standard.json --report results/standard_report.md

# Run Full profile benchmark (requires all models)
benchmark-full:
    python tests/benchmark/run_benchmark.py --profiles full --datasets custom,owasp --output results/full.json --report results/full_report.md

# Run all profiles on all datasets
benchmark-all:
    python tests/benchmark/run_benchmark.py --profiles lite,standard,full --datasets deepset,jackhhao,toxic-chat,safeguard,custom,owasp --output results/all.json --report results/benchmark_report.md

# Run Lite benchmark on local datasets only (no HuggingFace download)
benchmark-quick:
    python tests/benchmark/run_benchmark.py --profiles lite --datasets custom,owasp --output results/quick.json --report results/quick_report.md
