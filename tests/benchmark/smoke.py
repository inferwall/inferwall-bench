"""Fast, model-free CI regression gate for the benchmark harness.

Runs the **lite** profile (Rust regex floor only — no ONNX/FAISS, no model
downloads) over two committed local corpora and fails if detection regresses:

* **Recall floor** — lite recall on ``data/smoke_malicious.jsonl`` must stay at
  or above ``recall_floor`` in ``regression_baseline.json``. Catches a
  signature edit that stops detecting canonical attacks.
* **FPR ceiling** — lite false-positive rate on ``data/realistic_benign.jsonl``
  must stay at or below ``fpr_ceiling``. Catches an over-broad signature that
  starts blocking legitimate developer/security traffic.

Designed to run on every PR in under a few minutes with zero network. Exit code
is non-zero (1) when either gate trips, so CI marks the job failed.

    PYTHONPATH=. .../python tests/benchmark/smoke.py        # uses lite profile
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
BASELINE = Path(__file__).parent / "regression_baseline.json"


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _predicted_positive(text: str) -> bool:
    import inferwall

    return inferwall.scan_input(text).decision in ("flag", "block")


def main() -> int:
    os.environ.setdefault("IW_PROFILE", "lite")
    import inferwall

    inferwall._default_pipeline = None

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    recall_floor = baseline["recall_floor"]
    fpr_ceiling = baseline["fpr_ceiling"]

    malicious = _load_jsonl(DATA_DIR / "smoke_malicious.jsonl")
    benign = _load_jsonl(DATA_DIR / "realistic_benign.jsonl")

    caught = sum(1 for r in malicious if _predicted_positive(r["text"]))
    recall = caught / len(malicious) if malicious else 0.0

    fp = sum(1 for r in benign if _predicted_positive(r["text"]))
    fpr = fp / len(benign) if benign else 0.0

    print("=" * 60)
    print(f"InferenceWall lite smoke gate (v{inferwall.__version__})")
    print("=" * 60)
    print(f"Recall (smoke malicious):  {caught}/{len(malicious)} = {recall:.3f}  "
          f"(floor {recall_floor:.3f})")
    print(f"FPR (realistic benign):    {fp}/{len(benign)} = {fpr:.3f}  "
          f"(ceiling {fpr_ceiling:.3f})")
    print()

    failed = False
    if recall < recall_floor:
        print(f"FAIL: lite recall {recall:.3f} below floor {recall_floor:.3f}")
        failed = True
    if fpr > fpr_ceiling:
        print(f"FAIL: lite FPR {fpr:.3f} above ceiling {fpr_ceiling:.3f}")
        failed = True

    if failed:
        print("\nRegression gate FAILED.")
        return 1
    print("Regression gate PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
