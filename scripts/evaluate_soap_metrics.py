"""
SOAP Evaluation Metrics
=======================

Evaluates generated SOAP notes against reference (gold) SOAP notes.

Metrics:
  - Precision / Recall / F1 (token overlap; multiset)
  - ROUGE-1 / ROUGE-2 / ROUGE-L (F1)
  - Exact Match Accuracy (normalized text equality)
  - Section Presence Accuracy (empty/non-empty alignment)

Usage example:
  python scripts/evaluate_soap_metrics.py \
      --pred-dir data/soap_notes \
      --ref-dir data/reference_soap \
      --lang english
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


SECTIONS = ["subjective", "objective", "assessment", "plan"]


def safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def normalize_text(text: str) -> str:
    """Normalize text for overlap/accuracy metrics (supports Devanagari + Latin)."""
    text = (text or "").lower().strip()
    # Keep letters/numbers (Latin + Devanagari), whitespace
    text = re.sub(r"[^0-9a-z\u0900-\u097f\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    text = normalize_text(text)
    return text.split() if text else []


def multiset_overlap_count(a: List[str], b: List[str]) -> int:
    ca = Counter(a)
    cb = Counter(b)
    return sum((ca & cb).values())


def precision_recall_f1(pred_tokens: List[str], ref_tokens: List[str]) -> Tuple[float, float, float]:
    overlap = multiset_overlap_count(pred_tokens, ref_tokens)
    precision = safe_div(overlap, len(pred_tokens))
    recall = safe_div(overlap, len(ref_tokens))
    f1 = safe_div(2 * precision * recall, precision + recall)
    return precision, recall, f1


def ngram_counter(tokens: List[str], n: int) -> Counter:
    if len(tokens) < n or n <= 0:
        return Counter()
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def rouge_n_f1(pred_tokens: List[str], ref_tokens: List[str], n: int) -> float:
    pred_ng = ngram_counter(pred_tokens, n)
    ref_ng = ngram_counter(ref_tokens, n)
    overlap = sum((pred_ng & ref_ng).values())
    precision = safe_div(overlap, sum(pred_ng.values()))
    recall = safe_div(overlap, sum(ref_ng.values()))
    return safe_div(2 * precision * recall, precision + recall)


def lcs_length(a: List[str], b: List[str]) -> int:
    if not a or not b:
        return 0
    # DP with rolling rows to control memory
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        curr = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[-1]


def rouge_l_f1(pred_tokens: List[str], ref_tokens: List[str]) -> float:
    lcs = lcs_length(pred_tokens, ref_tokens)
    precision = safe_div(lcs, len(pred_tokens))
    recall = safe_div(lcs, len(ref_tokens))
    return safe_div(2 * precision * recall, precision + recall)


def extract_session_id(path: Path, payload: Dict) -> str:
    sid = payload.get("session_id")
    if sid is not None:
        return str(sid)
    m = re.search(r"(\d+)", path.stem)
    return m.group(1) if m else path.stem


def extract_soap_sections(payload: Dict, lang: str) -> Dict[str, str]:
    """Extract SOAP sections from flexible schema variants."""
    lang = (lang or "english").lower().strip()

    soap_key_candidates = []
    if lang == "english":
        soap_key_candidates.extend(["soap_english", "soap_en"])
    elif lang == "marathi":
        soap_key_candidates.extend(["soap_marathi", "soap_mr"])
    elif lang == "hindi":
        soap_key_candidates.extend(["soap_hindi", "soap_hi"])
    else:
        soap_key_candidates.append(f"soap_{lang}")

    soap = None
    for key in soap_key_candidates:
        if isinstance(payload.get(key), dict):
            soap = payload[key]
            break

    if soap is None:
        # fallback: top-level sections
        soap = payload

    result = {}
    for sec in SECTIONS:
        value = soap.get(sec, "") if isinstance(soap, dict) else ""
        result[sec] = value if isinstance(value, str) else str(value)
    return result


def load_soap_dir(dir_path: Path, lang: str) -> Dict[str, Dict[str, str]]:
    dataset = {}
    for file_path in sorted(dir_path.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"⚠️ Skipping invalid JSON: {file_path.name} ({exc})")
            continue
        sid = extract_session_id(file_path, payload)
        dataset[sid] = extract_soap_sections(payload, lang)
    return dataset


@dataclass
class MetricRow:
    precision: float
    recall: float
    f1: float
    rouge1_f1: float
    rouge2_f1: float
    rougeL_f1: float
    exact_match: float
    section_presence_acc: float


def score_section(pred_text: str, ref_text: str) -> MetricRow:
    pred_norm = normalize_text(pred_text)
    ref_norm = normalize_text(ref_text)

    pred_tokens = pred_norm.split() if pred_norm else []
    ref_tokens = ref_norm.split() if ref_norm else []

    p, r, f1 = precision_recall_f1(pred_tokens, ref_tokens)
    r1 = rouge_n_f1(pred_tokens, ref_tokens, n=1)
    r2 = rouge_n_f1(pred_tokens, ref_tokens, n=2)
    rl = rouge_l_f1(pred_tokens, ref_tokens)

    exact = 1.0 if pred_norm == ref_norm and ref_norm != "" else 0.0
    section_presence_acc = 1.0 if bool(pred_norm) == bool(ref_norm) else 0.0

    return MetricRow(
        precision=p,
        recall=r,
        f1=f1,
        rouge1_f1=r1,
        rouge2_f1=r2,
        rougeL_f1=rl,
        exact_match=exact,
        section_presence_acc=section_presence_acc,
    )


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate(pred: Dict[str, Dict[str, str]], ref: Dict[str, Dict[str, str]]) -> Dict:
    common_ids = sorted(set(pred.keys()) & set(ref.keys()), key=lambda x: int(x) if x.isdigit() else x)

    if not common_ids:
        pred_ids = sorted(pred.keys(), key=lambda x: int(x) if x.isdigit() else x)
        ref_ids = sorted(ref.keys(), key=lambda x: int(x) if x.isdigit() else x)

        if not pred_ids:
            raise ValueError(
                "No prediction JSON files/session_ids found in --pred-dir. "
                "Add prediction files like <session_id>_soap.json containing soap_marathi/soap_english."
            )
        if not ref_ids:
            raise ValueError(
                "No reference JSON files/session_ids found in --ref-dir. "
                "Add reference files in data/reference_soap/ using REFERENCE_TEMPLATE.json."
            )

        raise ValueError(
            "No overlapping session_ids between prediction and reference folders. "
            f"pred_count={len(pred_ids)}, ref_count={len(ref_ids)}, "
            f"sample_pred_ids={pred_ids[:10]}, sample_ref_ids={ref_ids[:10]}"
        )

    by_section = {sec: defaultdict(list) for sec in SECTIONS}
    per_session = []

    for sid in common_ids:
        session_metrics = {"session_id": sid, "sections": {}}
        for sec in SECTIONS:
            row = score_section(pred[sid].get(sec, ""), ref[sid].get(sec, ""))
            row_dict = row.__dict__
            session_metrics["sections"][sec] = row_dict
            for k, v in row_dict.items():
                by_section[sec][k].append(v)
        per_session.append(session_metrics)

    section_summary = {}
    macro_pool = defaultdict(list)

    for sec in SECTIONS:
        section_summary[sec] = {}
        for metric_name, vals in by_section[sec].items():
            section_summary[sec][metric_name] = mean(vals)
            macro_pool[metric_name].append(section_summary[sec][metric_name])

    overall_macro = {metric_name: mean(vals) for metric_name, vals in macro_pool.items()}

    return {
        "matched_sessions": len(common_ids),
        "pred_sessions": len(pred),
        "ref_sessions": len(ref),
        "unmatched_pred_sessions": len(set(pred.keys()) - set(ref.keys())),
        "unmatched_ref_sessions": len(set(ref.keys()) - set(pred.keys())),
        "section_metrics": section_summary,
        "overall_macro": overall_macro,
        "per_session": per_session,
    }


def print_report(results: Dict):
    print("=" * 90)
    print("SOAP EVALUATION REPORT")
    print("=" * 90)
    print(f"Matched sessions      : {results['matched_sessions']}")
    print(f"Prediction sessions   : {results['pred_sessions']}")
    print(f"Reference sessions    : {results['ref_sessions']}")
    print(f"Unmatched predictions : {results['unmatched_pred_sessions']}")
    print(f"Unmatched references  : {results['unmatched_ref_sessions']}")

    metric_cols = [
        "precision",
        "recall",
        "f1",
        "rouge1_f1",
        "rouge2_f1",
        "rougeL_f1",
        "exact_match",
        "section_presence_acc",
    ]

    print("\nPer-section mean metrics:")
    print("-" * 90)
    for sec, vals in results["section_metrics"].items():
        formatted = " | ".join(f"{m}={vals[m]:.4f}" for m in metric_cols)
        print(f"{sec:11s} -> {formatted}")

    print("\nOverall macro (average across S/O/A/P):")
    print("-" * 90)
    ov = results["overall_macro"]
    print(" | ".join(f"{m}={ov[m]:.4f}" for m in metric_cols))


def main():
    parser = argparse.ArgumentParser(description="Evaluate generated SOAP notes against reference SOAP notes.")
    parser.add_argument("--pred-dir", required=True, help="Directory containing generated SOAP JSON files")
    parser.add_argument("--ref-dir", required=True, help="Directory containing reference/gold SOAP JSON files")
    parser.add_argument(
        "--lang",
        default="marathi",
        help="Language to evaluate (default: marathi). Options: marathi/english/hindi/...",
    )
    parser.add_argument("--output-json", default="", help="Optional path to write full metrics JSON")
    parser.add_argument("--per-session-json", default="", help="Optional path to write per-session metrics JSON")
    args = parser.parse_args()

    pred_dir = Path(args.pred_dir)
    ref_dir = Path(args.ref_dir)

    if not pred_dir.exists() or not pred_dir.is_dir():
        raise SystemExit(f"Prediction directory not found: {pred_dir}")
    if not ref_dir.exists() or not ref_dir.is_dir():
        raise SystemExit(f"Reference directory not found: {ref_dir}")

    pred = load_soap_dir(pred_dir, args.lang)
    ref = load_soap_dir(ref_dir, args.lang)

    results = evaluate(pred, ref)
    print_report(results)

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n💾 Saved full metrics JSON: {out}")

    if args.per_session_json:
        out = Path(args.per_session_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results["per_session"], indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"💾 Saved per-session metrics JSON: {out}")


if __name__ == "__main__":
    main()
