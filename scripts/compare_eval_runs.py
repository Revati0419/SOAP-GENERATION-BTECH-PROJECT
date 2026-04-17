"""
Compare two SOAP evaluation outputs.

Typical use (Marathi):
  python scripts/compare_eval_runs.py \
    --baseline outputs/eval_gemma_marathi.json \
    --candidate outputs/eval_qlora_marathi.json \
    --label-baseline Gemma \
    --label-candidate QLoRA
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


CORE_METRICS = [
    "precision",
    "recall",
    "f1",
    "rouge1_f1",
    "rouge2_f1",
    "rougeL_f1",
    "exact_match",
    "section_presence_acc",
]

SECTIONS = ["subjective", "objective", "assessment", "plan"]


def load_json(path: Path) -> Dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to read {path}: {exc}")


def val(d: Dict, *keys, default=0.0):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def fmt_delta(delta: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.4f}"


def print_block(title: str):
    print("\n" + title)
    print("-" * len(title))


def print_metric_row(name: str, b: float, c: float):
    d = c - b
    print(f"{name:20s} | baseline={b:.4f} | candidate={c:.4f} | delta={fmt_delta(d)}")


def compare(baseline: Dict, candidate: Dict, label_b: str, label_c: str):
    print("=" * 92)
    print(f"SOAP EVAL COMPARISON: {label_b} (baseline) vs {label_c} (candidate)")
    print("=" * 92)

    print_block("Dataset coverage")
    for k in ["matched_sessions", "pred_sessions", "ref_sessions", "unmatched_pred_sessions", "unmatched_ref_sessions"]:
        vb = val(baseline, k, default=0)
        vc = val(candidate, k, default=0)
        print(f"{k:24s} | baseline={vb} | candidate={vc}")

    print_block("Overall macro metrics")
    for m in CORE_METRICS:
        vb = float(val(baseline, "overall_macro", m, default=0.0))
        vc = float(val(candidate, "overall_macro", m, default=0.0))
        print_metric_row(m, vb, vc)

    print_block("Section-wise metrics")
    for sec in SECTIONS:
        print(f"\n[{sec.upper()}]")
        for m in CORE_METRICS:
            vb = float(val(baseline, "section_metrics", sec, m, default=0.0))
            vc = float(val(candidate, "section_metrics", sec, m, default=0.0))
            print_metric_row(m, vb, vc)



def main():
    parser = argparse.ArgumentParser(description="Compare two SOAP evaluation JSON outputs.")
    parser.add_argument("--baseline", required=True, help="Path to baseline eval JSON (e.g., Gemma)")
    parser.add_argument("--candidate", required=True, help="Path to candidate eval JSON (e.g., QLoRA)")
    parser.add_argument("--label-baseline", default="Baseline", help="Display label for baseline model")
    parser.add_argument("--label-candidate", default="Candidate", help="Display label for candidate model")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    candidate_path = Path(args.candidate)

    if not baseline_path.exists():
        raise SystemExit(f"Baseline file not found: {baseline_path}")
    if not candidate_path.exists():
        raise SystemExit(f"Candidate file not found: {candidate_path}")

    baseline = load_json(baseline_path)
    candidate = load_json(candidate_path)
    compare(baseline, candidate, args.label_baseline, args.label_candidate)


if __name__ == "__main__":
    main()
