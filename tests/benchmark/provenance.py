"""Reproducibility provenance capture for benchmark runs.

Records everything needed to reproduce a headline number:

* **Dataset revisions** — the pinned HF SHAs from ``DATASETS.lock``.
* **Profile / policy + thresholds** — which engines ran and the decision
  thresholds, read live from the loaded pipeline.
* **Model file SHA256s** — best-effort hashing of the ONNX model files in the
  inferwall cache, so a model swap is detectable.
* **Bench git commit** — the commit of this harness.
* **Global seed** — the seed threaded through sampling and bootstrap CIs.

Run ``python tests/benchmark/provenance.py --refresh-lock`` to re-resolve the HF
dataset SHAs and rewrite ``DATASETS.lock`` (requires network + huggingface_hub).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

LOCK_PATH = Path(__file__).parent / "DATASETS.lock"
MODEL_CACHE = Path.home() / ".cache" / "inferwall" / "models"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _dataset_revisions(dataset_names: list[str]) -> dict:
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8")).get("datasets", {})
    except FileNotFoundError:
        lock = {}
    return {
        name: {
            "hf_id": lock.get(name, {}).get("hf_id", lock.get(name, {}).get("local", "?")),
            "revision": lock.get(name, {}).get("revision", "unpinned"),
        }
        for name in dataset_names
    }


def _sha256(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _model_hashes() -> dict:
    """Best-effort SHA256 of cached ONNX model files. Empty if cache absent."""
    out: dict[str, str] = {}
    if not MODEL_CACHE.exists():
        return out
    for onnx in sorted(MODEL_CACHE.rglob("*.onnx")):
        try:
            rel = str(onnx.relative_to(MODEL_CACHE))
            out[rel] = _sha256(onnx)
        except Exception:
            continue
    return out


def _policy_snapshot(profiles: list[str]) -> dict:
    """Capture the live policy thresholds and signature count, best-effort."""
    snap: dict = {"profiles": profiles}
    try:
        import inferwall

        pipe = inferwall._get_pipeline()
        pol = pipe.policy
        snap["policy_name"] = pol.name
        snap["thresholds"] = {
            "inbound_flag": pol.inbound_flag_threshold,
            "inbound_block": pol.inbound_block_threshold,
            "outbound_flag": pol.outbound_flag_threshold,
            "outbound_block": pol.outbound_block_threshold,
        }
        snap["signature_count"] = pipe.signature_count
    except Exception as exc:  # pragma: no cover - environment dependent
        snap["policy_error"] = str(exc)[:120]
    return snap


def collect_provenance(dataset_names: list[str], profiles: list[str], seed: int) -> dict:
    """Assemble the full provenance block for the results JSON."""
    return {
        "bench_git_commit": _git_commit(),
        "seed": seed,
        "dataset_revisions": _dataset_revisions(dataset_names),
        "policy": _policy_snapshot(profiles),
        "model_sha256": _model_hashes(),
    }


def refresh_lock() -> None:
    """Re-resolve HF dataset SHAs and rewrite DATASETS.lock (needs network)."""
    import os
    import time

    from huggingface_hub import HfApi

    api = HfApi()
    token = os.environ.get("HF_TOKEN")
    data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    for name, meta in data["datasets"].items():
        hf_id = meta.get("hf_id")
        if not hf_id:
            continue
        try:
            info = api.dataset_info(hf_id, token=token)
            meta["revision"] = info.sha
            print(f"{name:18s} {hf_id} -> {info.sha}")
        except Exception as exc:
            print(f"{name:18s} {hf_id} ERR {exc}")
    data["resolved_at"] = time.strftime("%Y-%m-%d")
    LOCK_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {LOCK_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark provenance utility")
    parser.add_argument("--refresh-lock", action="store_true",
                        help="Re-resolve HF dataset SHAs and rewrite DATASETS.lock")
    args = parser.parse_args()
    if args.refresh_lock:
        refresh_lock()
    else:
        prov = collect_provenance(["deepset", "jackhhao"], ["lite"], 42)
        print(json.dumps(prov, indent=2))
