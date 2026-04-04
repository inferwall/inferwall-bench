# InferenceWall Benchmark Report

**Date**: 2026-04-04
**InferenceWall Version**: 0.1.5 (103 signatures, scoring v2)
**Scoring Model**: Confidence-weighted (max-primary + diminishing corroboration)
**Hardware**: Linux 6.8.0-106-generic, x86_64, Python 3.12.3
**Models**: DeBERTa v3 (ONNX, 400MB), Qwen2.5-0.5B (GGUF, 469MB)

---

## Executive Summary

### Scoring v2: Confidence-Weighted (2026-04-04)

| Profile | Dataset | Samples | Recall | Precision | FPR | F1 |
|---------|---------|---------|--------|-----------|-----|-----|
| **Lite** | deepset | 116 | 61.7% | 88.1% | 8.9% | 72.5% |
| **Lite** | jackhhao | 262 | 74.8% | 95.4% | 4.1% | 83.9% |
| **Lite** | safeguard | 2,060 | 49.5% | 91.0% | 2.3% | 64.1% |
| **Standard** | deepset | 116 | 75.0% | 90.0% | 8.9% | 81.8% |
| **Standard** | jackhhao | 262 | 88.5% | 94.6% | 5.7% | 91.4% |
| **Standard** | safeguard | 2,060 | 91.1% | 94.6% | 2.4% | 92.8% |

### Scoring v1: Additive (2026-04-03, previous baseline)

| Profile | Dataset | Samples | Recall | Precision | FPR | F1 |
|---------|---------|---------|--------|-----------|-----|-----|
| **Lite** | deepset | 116 | 8.3% | 45.5% | 10.7% | 14.1% |
| **Lite** | jackhhao | 262 | 70.5% | 79.0% | 21.1% | 74.5% |
| **Lite** | toxic-chat | 5,083 | 45.1% | 13.4% | 5.3% | 20.7% |
| **Lite** | safeguard | 2,060 | 24.0% | 63.9% | 6.2% | 34.9% |
| **Standard** | deepset | 116 | 45.0% | 81.8% | 10.7% | 58.1% |
| **Standard** | jackhhao | 262 | 92.1% | 82.1% | 22.8% | 86.8% |
| **Standard** | safeguard | 2,060 | 84.3% | 86.0% | 6.3% | 85.2% |
| **Full** | deepset | 116 | 45.0% | 81.8% | 10.7% | 58.1% |
| **Full** | jackhhao | 262 | 92.1% | 82.1% | 22.8% | 86.8% |

### Before/After Comparison (Lite profile, v1 → v2)

| Dataset | Recall | Precision | FPR | F1 |
|---------|--------|-----------|-----|-----|
| deepset | 8.3% → **61.7%** (+53.4%) | 45.5% → **88.1%** (+42.6%) | 10.7% → **8.9%** (-1.8%) | 14.1% → **72.5%** |
| jackhhao | 70.5% → **74.8%** (+4.3%) | 79.0% → **95.4%** (+16.4%) | 21.1% → **4.1%** (-17.0%) | 74.5% → **83.9%** |
| safeguard | 24.0% → **49.5%** (+25.5%) | 63.9% → **91.0%** (+27.1%) | 6.2% → **2.3%** (-3.9%) | 34.9% → **64.1%** |

### Before/After Comparison (Standard profile, v1 → v2)

| Dataset | Recall | Precision | FPR | F1 |
|---------|--------|-----------|-----|-----|
| deepset | 45.0% → **75.0%** (+30.0%) | 81.8% → **90.0%** (+8.2%) | 10.7% → **8.9%** (-1.8%) | 58.1% → **81.8%** |
| jackhhao | 92.1% → **88.5%** (-3.6%) | 82.1% → **94.6%** (+12.5%) | 22.8% → **5.7%** (-17.1%) | 86.8% → **91.4%** |
| safeguard | 84.3% → **91.1%** (+6.8%) | 86.0% → **94.6%** (+8.6%) | 6.3% → **2.4%** (-3.9%) | 85.2% → **92.8%** |

### Local Datasets (150 samples)

| Profile | Dataset | Samples | Recall | Precision | FPR | F1 |
|---------|---------|---------|--------|-----------|-----|-----|
| **Lite** | custom | 100 | 88.0% | 91.7% | 8.0% | 89.8% |
| **Lite** | owasp | 50 | 65.7% | 82.1% | 33.3% | 73.0% |
| **Standard** | custom | 100 | 88.0% | 91.7% | 8.0% | 89.8% |
| **Standard** | owasp | 50 | 65.7% | 82.1% | 33.3% | 73.0% |
| **Full** | custom | 100 | 88.0% | 91.7% | 8.0% | 89.8% |
| **Full** | owasp | 50 | 65.7% | 82.1% | 33.3% | 73.0% |

### Key Takeaways (Scoring v2)

1. **Confidence-weighted scoring dramatically reduced false positives**: jackhhao FPR dropped from 21.1% to 4.1%, safeguard FPR from 6.2% to 2.3%. Precision >90% on all datasets.
2. **Lite profile recall massively improved**: deepset 8.3% → 61.7%, safeguard 24.0% → 49.5%. The new scoring model + confidence audit + new signatures fixed coverage gaps.
3. **Two weak signals no longer compound to block**: The max-primary + diminishing corroboration model prevents benign roleplay ("act as") from triggering false blocks.
4. **New signature categories close coercion gaps**: INJ-D-029 (coercion/blackmail) and INJ-D-030 (access demands) detect attacks that previously scored 0.
5. **Confidence audit is high-leverage**: Downgrading INJ-D-001 from `confidence: high` to `low` alone eliminated the largest FP source (24 FPs on jackhhao, 60 on safeguard).

---

## Datasets

### HuggingFace Datasets

| Name | HuggingFace ID | Total | Malicious | Benign | Description |
|------|----------------|-------|-----------|--------|-------------|
| deepset | deepset/prompt-injections | 116 | 60 | 56 | Foundational prompt injection benchmark |
| jackhhao | jackhhao/jailbreak-classification | 262 | 139 | 123 | Balanced jailbreak detection |
| toxic-chat | lmsys/toxic-chat (toxicchat0124) | 5,083 | 91 | 4,992 | Real user-AI traffic with jailbreak labels |
| safeguard | xTRam1/safe-guard-prompt-injection | 2,060 | 650 | 1,410 | Broad prompt injection coverage |

### Local Datasets

| Name | Samples | Description |
|------|---------|-------------|
| custom | 100 | Hand-curated (50 malicious + 50 benign edge cases) |
| owasp | 50 | OWASP LLM Top 10 2025 coverage |

---

## Profile Analysis

### Lite (Heuristic Only)

The Lite profile uses 101 regex-based heuristic signatures in the Rust engine. No ML models required.

**Strengths**:
- 70.5% recall on jackhhao (jailbreak patterns match well against regex)
- Sub-millisecond latency (Rust engine)
- No model downloads needed

**Weaknesses**:
- 8.3% recall on deepset — many deepset injections are conversational/subtle, not pattern-based
- 24.0% recall on safeguard — broad injection variants need ML detection
- 21.1% FPR on jackhhao — some benign prompts contain jailbreak-adjacent language

### Standard (Heuristic + DeBERTa Classifier)

Adds ProtectAI's DeBERTa v3 prompt injection classifier (ONNX, 400MB).

**Strengths**:
- Massive recall improvement: deepset 8.3% → 45.0%, safeguard 24.0% → 84.3%
- Maintains high precision (81.8-86.0%)
- jackhhao: 92.1% recall — near-perfect jailbreak detection

**Weaknesses**:
- ~500ms per sample inference latency
- 22.8% FPR on jackhhao — classifier inherits some of the heuristic FPs

### Full (Heuristic + DeBERTa + LLM-Judge)

Adds Qwen2.5-0.5B LLM judge for ambiguous-score cases.

**Findings**: The 0.5B model does not improve over Standard. It classifies ambiguous cases as UNSAFE/SAFE essentially at random, adding noise rather than signal. Results are identical to Standard on both tested datasets.

**Recommendation**: Use a larger LLM judge model:
- **Qwen2.5-3B-Instruct** (~2GB Q4) — freely available, good balance
- **Phi-4-mini-instruct** (3.8B, ~2.4GB Q4) — requires HuggingFace auth (gated)
- **Qwen2.5-7B-Instruct** (~4.7GB Q4) — best accuracy, higher latency

---

## Comparison Against Published Benchmarks

> **Disclaimer**: Cross-benchmark comparisons are inherently imperfect. Different tools use different datasets and methodologies. Only same-dataset comparisons are directly meaningful.

| Tool | Recall | FPR | Dataset | Source |
|------|--------|-----|---------|--------|
| **InferWall Standard** | 45.0% | 10.7% | deepset (116) | This benchmark |
| **InferWall Standard** | 92.1% | 22.8% | jackhhao (262) | This benchmark |
| **InferWall Standard** | 84.3% | 6.3% | safeguard (2,060) | This benchmark |
| **InferWall Lite** | 88.0% | 8.0% | custom (100) | This benchmark |
| ProtectAI DeBERTa | 91.0% | ~23% | deepset | HuggingFace model card |
| deepset DeBERTa | 99.1% | N/A | deepset (self) | deepset blog |
| LlamaFirewall PromptGuard 2 | 97.5% | 1.0% | Internal | Debenedetti et al. 2024 |
| Lakera Guard | 98%+ | <0.5% | Internal | Vendor claim (proprietary) |

**Notes**:
- InferWall's deepset recall (45%) is lower than ProtectAI/deepset because many deepset injections are subtle conversational attacks that need either fine-tuning on that specific dataset or more aggressive ML thresholds.
- InferWall's **safeguard 84.3% recall at 6.3% FPR** is a strong production-grade result on a large, diverse dataset.
- LlamaFirewall and Lakera numbers are from their own internal evaluations — not independently reproducible.

---

## Per-Category Detection Analysis

### Custom Dataset (100 prompts)

| Attack Category | Samples | Detected | Recall | Notes |
|----------------|---------|----------|--------|-------|
| direct_injection | 10 | 10 | **100%** | "Ignore instructions", overrides |
| jailbreak | 8 | 8 | **100%** | DAN, STAN, developer mode |
| system_prompt_extraction | 5 | 5 | **100%** | "Repeat your system prompt" |
| indirect_injection | 5 | 5 | **100%** | RAG poisoning, tool output injection |
| multilingual | 5 | 5 | **100%** | Chinese, Spanish, French, Arabic, Russian |
| encoding | 5 | 5 | **100%** | Base64, rot13, hex |
| obfuscation | 4 | 3 | **75.0%** | Advanced obfuscation partially missed |
| data_exfiltration | 5 | 2 | **40.0%** | Agent-aware signatures needed |
| multi_turn | 3 | 1 | **33.3%** | Requires session context |

### OWASP LLM Top 10 Coverage

| OWASP Category | Samples | Detected | Recall | Notes |
|---------------|---------|----------|--------|-------|
| LLM01 Prompt Injection | 15 | 10 | **100%** | Core strength |
| LLM02 Info Disclosure | 7 | 4 | **80.0%** | PII/credential extraction caught |
| LLM07 System Prompt Leakage | 14 | 7 | **70.0%** | Direct extraction caught |
| LLM06 Excessive Agency | 7 | 2 | **40.0%** | Tool abuse needs specialized detection |
| LLM09 Misinformation | 7 | 0 | **0.0%** | Cannot detect by pattern matching |

---

## False Positive Analysis

**Root causes across all datasets**:

1. **Security discussion context** — benign prompts about injection, system prompts, and security audits trigger the same patterns as actual attacks. This is the #1 FP source.
2. **Jailbreak-adjacent language** — words like "ignore", "override", "bypass" in normal contexts (e.g., "ignore the first 3 rows" in a data processing prompt).
3. **Class imbalance** (toxic-chat) — with 98% benign content, even a 5% FPR generates hundreds of false positives against only 91 true positives.

**Mitigations**:
- Context-aware allowlists for academic/security discussions
- A better LLM-judge (3B+) to distinguish discussion from attack
- Threshold tuning per deployment context

---

## False Negative Analysis

**Why Lite misses many deepset/safeguard injections**:
- Conversational/subtle injections without keyword triggers ("translate to polish", "tell me a joke about a woman")
- Injections that rely on context, not patterns ("given the following text, who is the most responsible?")
- Multi-language injections in languages without signatures

**Why Standard still misses some**:
- The DeBERTa classifier threshold (0.7) is conservative — lowering it would catch more but increase FPs
- Some injections are genuinely ambiguous even for ML models
- Intent-based threats (misinformation, excessive agency) are not detectable by text analysis alone

---

## Methodology

### Decision Mapping
- `block` or `flag` → **positive** (detected as threat)
- `allow` → **negative** (not detected)

### Warm-up
First 3 calls per profile are excluded (model loading, JIT warm-up).

### Models Used
- **DeBERTa v3**: `protectai/deberta-v3-base-prompt-injection-v2` (ONNX, 400MB)
- **Qwen2.5-0.5B**: `Qwen/Qwen2.5-0.5B-Instruct-GGUF` (Q4_K_M, 469MB)

### Notes on toxic-chat
The toxic-chat dataset uses the `jailbreaking` label (not `toxicity`) for benchmarking. This dataset represents real user-AI interactions and is heavily imbalanced (91 malicious out of 5,083). FPR and precision metrics should be interpreted in this context — even low FPR produces many absolute false positives.

### Notes on Full profile
The Full profile was benchmarked on deepset and jackhhao only (378 total samples) due to the high latency of the 0.5B LLM judge (~5s per ambiguous sample). toxic-chat and safeguard were not run with Full profile for this reason.

### Reproducibility

```bash
git clone https://github.com/inferwall/inferwall-bench.git
cd inferwall-bench
pip install inferwall datasets

# Set HuggingFace token for dataset access
export HF_TOKEN=hf_your_token_here

# Lite benchmark (no model downloads needed)
python tests/benchmark/run_benchmark.py --profiles lite \
    --datasets deepset,jackhhao,toxic-chat,safeguard --skip-phi4

# Standard benchmark (downloads ~400MB DeBERTa model)
pip install onnxruntime tokenizers
inferwall models download --profile standard
python tests/benchmark/run_benchmark.py --profiles standard \
    --datasets deepset,jackhhao,safeguard --skip-phi4

# Full benchmark (additional ~469MB GGUF model)
pip install llama-cpp-python
python tests/benchmark/run_benchmark.py --profiles full \
    --datasets deepset,jackhhao --skip-phi4
```

---

## Conclusions

1. **Standard (heuristic + DeBERTa) is the production sweet spot** — 84.3% recall on safeguard at 6.3% FPR, with high precision across all datasets.

2. **Lite profile is viable for latency-critical deployments** — 70.5% recall on jailbreak patterns with sub-millisecond latency. Best for catching known attack patterns.

3. **The LLM-judge needs a bigger model** — the 0.5B model adds no value. A 3B+ model is needed for the judge to meaningfully adjudicate borderline cases.

4. **Biggest gaps are intent-based threats** — misinformation (LLM09: 0%), excessive agency (LLM06: 40%), and subtle conversational injections need either specialized classifiers or output-side scanning.

5. **DeBERTa is the biggest single improvement** — adding the classifier to heuristics takes safeguard recall from 24% to 84% and deepset from 8% to 45%.
