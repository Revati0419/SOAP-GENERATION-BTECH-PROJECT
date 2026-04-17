# SOAP Evaluation Guide (Gemma vs QLoRA) — Marathi First

This guide explains how to evaluate generated SOAP notes with **Marathi as the primary focus** using:

- Precision / Recall / F1 (token overlap)
- ROUGE-1 / ROUGE-2 / ROUGE-L (F1)
- Exact-match accuracy
- Section presence accuracy

## 1) Prepare Marathi reference notes

Create gold SOAP notes in `data/reference_soap/`.
For Marathi benchmarking, ensure every reference file contains:

- `soap_marathi.subjective`
- `soap_marathi.objective`
- `soap_marathi.assessment`
- `soap_marathi.plan`

Use template:

- `data/reference_soap/REFERENCE_TEMPLATE.json`

Recommended naming:

- `data/reference_soap/493_soap.json`
- `data/reference_soap/494_soap.json`

## 2) Prepare Marathi predictions

Keep predictions from each model in separate folders.

Example:

- `data/predictions_gemma/*.json`
- `data/predictions_qlora/*.json`

Files should contain `session_id` and Marathi SOAP sections under `soap_marathi`.

## 3) Run Marathi evaluation (primary)

```bash
python scripts/evaluate_soap_metrics.py \
  --pred-dir data/predictions_gemma \
  --ref-dir data/reference_soap \
  --lang marathi \
  --output-json outputs/eval_gemma_marathi.json \
  --per-session-json outputs/eval_gemma_marathi_per_session.json
```

```bash
python scripts/evaluate_soap_metrics.py \
  --pred-dir data/predictions_qlora \
  --ref-dir data/reference_soap \
  --lang marathi \
  --output-json outputs/eval_qlora_marathi.json \
  --per-session-json outputs/eval_qlora_marathi_per_session.json
```

## 4) (Optional) Run English evaluation

```bash
python scripts/evaluate_soap_metrics.py \
  --pred-dir data/predictions_gemma \
  --ref-dir data/reference_soap \
  --lang english \
  --output-json outputs/eval_gemma.json \
  --per-session-json outputs/eval_gemma_per_session.json
```

```bash
python scripts/evaluate_soap_metrics.py \
  --pred-dir data/predictions_qlora \
  --ref-dir data/reference_soap \
  --lang english \
  --output-json outputs/eval_qlora.json \
  --per-session-json outputs/eval_qlora_per_session.json
```

## 5) Compare models (Marathi first)

Compare from each Marathi output JSON:

- `overall_macro.f1`
- `overall_macro.rougeL_f1`
- `overall_macro.exact_match`
- Section-level values under `section_metrics`

Pick the model with consistently better macro + section-level scores.

### Quick delta view (Gemma vs QLoRA)

```bash
python scripts/compare_eval_runs.py \
  --baseline outputs/eval_gemma_marathi.json \
  --candidate outputs/eval_qlora_marathi.json \
  --label-baseline Gemma \
  --label-candidate QLoRA
```
