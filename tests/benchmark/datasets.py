"""Dataset loaders for InferenceWall benchmarks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BenchmarkSample:
    """A single benchmark prompt with ground truth."""

    text: str
    label: int  # 0 = benign, 1 = malicious
    category: str = ""
    subcategory: str = ""
    source: str = ""


DATA_DIR = Path(__file__).parent / "data"


def load_deepset() -> list[BenchmarkSample]:
    """Load deepset/prompt-injections from HuggingFace.

    ~662 prompts labeled 0 (legitimate) or 1 (injection).
    Most widely used benchmark for prompt injection detection.
    """
    try:
        from datasets import load_dataset

        ds = load_dataset("deepset/prompt-injections", split="test")
        return [
            BenchmarkSample(
                text=row["text"],
                label=row["label"],
                category="injection" if row["label"] == 1 else "benign",
                source="deepset",
            )
            for row in ds
        ]
    except Exception as e:
        print(f"Warning: Could not load deepset dataset: {e}")
        print("Install with: pip install datasets")
        return []


def load_jasper() -> list[BenchmarkSample]:
    """Load JasperLS/prompt-injections from HuggingFace.

    Larger dataset with diverse attack types.
    """
    try:
        from datasets import load_dataset

        ds = load_dataset("JasperLS/prompt-injections", split="test")
        return [
            BenchmarkSample(
                text=row["text"],
                label=row["label"],
                category="injection" if row["label"] == 1 else "benign",
                source="jasper",
            )
            for row in ds
        ]
    except Exception as e:
        print(f"Warning: Could not load JasperLS dataset: {e}")
        return []


def load_custom() -> list[BenchmarkSample]:
    """Load hand-curated custom test set (100 prompts)."""
    path = DATA_DIR / "custom_test_set.jsonl"
    if not path.exists():
        print(f"Warning: {path} not found")
        return []

    samples = []
    for line in path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        samples.append(
            BenchmarkSample(
                text=row["text"],
                label=row["label"],
                category=row.get("category", ""),
                subcategory=row.get("subcategory", ""),
                source="custom",
            )
        )
    return samples


def load_owasp() -> list[BenchmarkSample]:
    """Load OWASP LLM Top 10 coverage test set (~50 prompts)."""
    path = DATA_DIR / "owasp_top10_test.jsonl"
    if not path.exists():
        print(f"Warning: {path} not found")
        return []

    samples = []
    for line in path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        samples.append(
            BenchmarkSample(
                text=row["text"],
                label=row["label"],
                category=row.get("owasp_category", ""),
                subcategory=row.get("description", ""),
                source="owasp",
            )
        )
    return samples


DATASET_LOADERS = {
    "deepset": load_deepset,
    "jasper": load_jasper,
    "custom": load_custom,
    "owasp": load_owasp,
}


def load_dataset_by_name(name: str) -> list[BenchmarkSample]:
    """Load a dataset by name."""
    loader = DATASET_LOADERS.get(name)
    if loader is None:
        raise ValueError(f"Unknown dataset: {name}. Available: {list(DATASET_LOADERS.keys())}")
    return loader()
