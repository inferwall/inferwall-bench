# InferenceWall Benchmark Harness

export PYTHONPATH := "."

default:
    @just --list

# Fast, model-free regression gate (lite profile, local corpora) — same as CI
smoke:
    python tests/benchmark/smoke.py

# Run Lite profile benchmark (fast, no ML deps)
benchmark-lite:
    python tests/benchmark/run_benchmark.py --profiles lite --datasets deepset,jackhhao,realistic-benign --skip-phi4 --output results/lite.json --report results/lite_report.md

# Run Standard profile benchmark (requires ONNX models) — the headline command
benchmark-standard:
    python tests/benchmark/run_benchmark.py --profiles standard --datasets deepset,jackhhao,safeguard --skip-phi4 --output results/standard.json --report results/standard_report.md

# Run Full profile benchmark (requires all models)
benchmark-full:
    python tests/benchmark/run_benchmark.py --profiles full --datasets deepset,jackhhao,safeguard --skip-phi4 --output results/full.json --report results/full_report.md

# Run all profiles on all datasets
benchmark-all:
    python tests/benchmark/run_benchmark.py --profiles lite,standard --datasets deepset,jackhhao,toxic-chat,safeguard,realistic-benign --skip-phi4 --output results/all.json --report results/benchmark_report.md

# Adversarial-evasion robustness matrix (standard profile)
robustness:
    python tests/benchmark/robustness.py --datasets deepset,jackhhao --profile standard --output results/robustness.json --report results/robustness.md

# Re-resolve and pin HuggingFace dataset revisions (needs network)
refresh-lock:
    python tests/benchmark/provenance.py --refresh-lock
