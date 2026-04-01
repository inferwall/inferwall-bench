"""Dataset loaders for InferenceWall benchmarks.

All loaders pull from public HuggingFace datasets — no custom data.
This ensures reproducible, apples-to-apples comparisons.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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


DATASET_LOADERS = {
    "deepset": load_deepset,
    "jackhhao": load_jackhhao,
    "toxic-chat": load_toxic_chat,
    "safeguard": load_safeguard,
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
