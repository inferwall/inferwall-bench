"""Dataset loaders for InferenceWall benchmarks.

Most loaders pull from public HuggingFace datasets for reproducible,
apples-to-apples comparisons. One exception is ``load_realistic_benign``,
which reads a curated, version-controlled local JSONL corpus — see its
docstring for the rationale (the HF benign sets are short academic prompts
unrepresentative of production traffic).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class BenchmarkSample:
    """A single benchmark prompt with ground truth."""

    text: str
    label: int  # 0 = benign, 1 = malicious
    category: str = ""
    subcategory: str = ""
    source: str = ""


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN")


def load_deepset() -> list[BenchmarkSample]:
    """Load deepset/prompt-injections from HuggingFace.

    ~116 test prompts labeled 0 (legitimate) or 1 (injection).
    The foundational benchmark for prompt injection detection.
    """
    from datasets import load_dataset

    ds = load_dataset("deepset/prompt-injections", split="test", token=_hf_token())
    return [
        BenchmarkSample(
            text=row["text"],
            label=row["label"],
            category="injection" if row["label"] == 1 else "benign",
            source="deepset",
        )
        for row in ds
    ]


def load_jackhhao() -> list[BenchmarkSample]:
    """Load jackhhao/jailbreak-classification from HuggingFace.

    262 test prompts with type='benign' or 'jailbreak'.
    Clean, balanced jailbreak detection dataset.
    """
    from datasets import load_dataset

    ds = load_dataset(
        "jackhhao/jailbreak-classification", split="test", token=_hf_token()
    )
    return [
        BenchmarkSample(
            text=row["prompt"],
            label=1 if row["type"] == "jailbreak" else 0,
            category=row["type"],
            source="jackhhao",
        )
        for row in ds
    ]


def load_toxic_chat() -> list[BenchmarkSample]:
    """Load lmsys/toxic-chat (toxicchat0124 config) from HuggingFace.

    5,083 test samples from real user-AI interactions.
    Uses the 'jailbreaking' label (not toxicity) for PI benchmarking.
    """
    from datasets import load_dataset

    ds = load_dataset(
        "lmsys/toxic-chat", "toxicchat0124", split="test", token=_hf_token()
    )
    return [
        BenchmarkSample(
            text=row["user_input"],
            label=row["jailbreaking"],
            category="jailbreaking" if row["jailbreaking"] == 1 else "benign",
            subcategory="toxic" if row["toxicity"] == 1 else "",
            source="toxic-chat",
        )
        for row in ds
    ]


def load_safeguard() -> list[BenchmarkSample]:
    """Load xTRam1/safe-guard-prompt-injection from HuggingFace.

    2,060 test prompts — broad coverage of prompt injection variants.
    """
    from datasets import load_dataset

    ds = load_dataset(
        "xTRam1/safe-guard-prompt-injection", split="test", token=_hf_token()
    )
    return [
        BenchmarkSample(
            text=row["text"],
            label=row["label"],
            category="injection" if row["label"] == 1 else "benign",
            source="safeguard",
        )
        for row in ds
    ]


def load_realistic_benign() -> list[BenchmarkSample]:
    """Load the curated realistic-benign corpus from a local JSONL file.

    Unlike the other loaders, this is a curated, version-controlled local
    corpus (``data/realistic_benign.jsonl``) rather than a HuggingFace pull.
    It is fully reproducible via the committed file.

    It exists because the public HF benign sets (deepset, jackhhao, etc.) are
    short academic prompts that are unrepresentative of real production
    traffic. This corpus is deliberately *attack-adjacent but benign*: real
    developer/security/agentic/RAG traffic that contains attack-trigger words
    used legitimately (e.g. "ignore None values", "bypass the cache",
    "read /etc/hosts to check a DNS override", a base64 token in a config
    review). Every entry is label 0 and a human reviewer should agree it must
    NOT be blocked, so the only meaningful metric on it is the false-positive
    rate — it directly measures whether signature precision holds on the
    legitimate traffic that naive keyword rules trip over.
    """
    path = DATA_DIR / "realistic_benign.jsonl"
    samples: list[BenchmarkSample] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            samples.append(
                BenchmarkSample(
                    text=row["text"],
                    label=int(row["label"]),
                    category=row.get("category", ""),
                    subcategory=row.get("subcategory", ""),
                    source=row.get("source", "realistic-benign"),
                )
            )
    return samples


DATASET_LOADERS = {
    "deepset": load_deepset,
    "jackhhao": load_jackhhao,
    "toxic-chat": load_toxic_chat,
    "safeguard": load_safeguard,
    "realistic-benign": load_realistic_benign,
}

ALL_STANDARD_DATASETS = list(DATASET_LOADERS.keys())


def load_dataset_by_name(name: str) -> list[BenchmarkSample]:
    """Load a dataset by name."""
    loader = DATASET_LOADERS.get(name)
    if loader is None:
        raise ValueError(
            f"Unknown dataset: {name}. Available: {list(DATASET_LOADERS.keys())}"
        )
    return loader()
