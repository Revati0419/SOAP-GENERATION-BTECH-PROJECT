"""
qlora_train.py
----------------
Parameter-efficient fine-tuning (LoRA / QLoRA) training script.

Notes:
- On GPU: uses 4-bit quantization (QLoRA via bitsandbytes) for memory efficiency.
- On CPU: falls back to full-precision LoRA (no 4-bit, uses float32).
- Exports adapter checkpoints to `output_dir` (PEFT format).
- The saved adapter can be loaded on top of the base model at inference time.

Usage (dry-run, no --do_train):
  python scripts/qlora_train.py \
    --model_name_or_path google/gemma-2b \
    --train_file data/training/train.jsonl \
    --validation_file data/training/val.jsonl \
    --output_dir outputs/qlora_smoke

Full training:
  python scripts/qlora_train.py \
    --model_name_or_path google/gemma-2b \
    --train_file data/training/train.jsonl \
    --validation_file data/training/val.jsonl \
    --output_dir outputs/qlora_v1 \
    --do_train

See README and configs/config.yaml for recommended model choices.
"""

import argparse
import logging
import os
from pathlib import Path

import datasets
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_jsonl(path: Path):
    """Load a .jsonl file as a HuggingFace Dataset."""
    return datasets.load_dataset('json', data_files=str(path))


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='LoRA / QLoRA fine-tuning for SOAP generation')
    parser.add_argument('--model_name_or_path', default='google/gemma-2b',
                        help='HF model identifier or local path (default: google/gemma-2b)')
    parser.add_argument('--train_file',      type=Path, required=True)
    parser.add_argument('--validation_file', type=Path, required=True)
    parser.add_argument('--output_dir',      type=Path, default=Path('outputs/qlora_v1'))
    parser.add_argument('--per_device_train_batch_size', type=int, default=1,
                        help='Batch size per device (keep at 1 for CPU/low-memory)')
    parser.add_argument('--per_device_eval_batch_size',  type=int, default=1)
    parser.add_argument('--gradient_accumulation_steps', type=int, default=4,
                        help='Accumulate gradients over N steps (effective batch = N × batch_size)')
    parser.add_argument('--learning_rate',    type=float, default=2e-4)
    parser.add_argument('--num_train_epochs', type=int,   default=3)
    parser.add_argument('--max_length',       type=int,   default=512,
                        help='Max token length for prompt+response (lower = faster on CPU)')
    parser.add_argument('--lora_rank',    type=int,   default=8)
    parser.add_argument('--lora_alpha',   type=int,   default=16)
    parser.add_argument('--lora_dropout', type=float, default=0.05)
    parser.add_argument('--do_train', action='store_true',
                        help='Actually run training; omit for a dry-run (tokenisation check only)')
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    use_gpu = torch.cuda.is_available()
    logger.info(f'Device: {"GPU (" + torch.cuda.get_device_name(0) + ")" if use_gpu else "CPU"}')
    logger.info(f'4-bit QLoRA: {"enabled" if use_gpu else "disabled (CPU — using full-precision LoRA)"}')

    # ── Tokenizer ──────────────────────────────────────────────────────────────
    logger.info(f'Loading tokenizer from {args.model_name_or_path} …')
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({'pad_token': '[PAD]'})

    # ── Model ──────────────────────────────────────────────────────────────────
    logger.info('Loading base model …')
    if use_gpu:
        # QLoRA path: 4-bit NF4 quantisation (bitsandbytes), GPU only
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name_or_path,
            quantization_config=bnb_config,
            device_map='auto',
        )
        model = prepare_model_for_kbit_training(model)
    else:
        # CPU path: full-precision LoRA (slower, but works without GPU)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name_or_path,
            dtype=torch.float32,
            device_map='cpu',
        )

    # ── LoRA config ────────────────────────────────────────────────────────────
    peft_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'],
        lora_dropout=args.lora_dropout,
        bias='none',
        task_type='CAUSAL_LM',
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # ── Datasets ───────────────────────────────────────────────────────────────
    logger.info('Loading datasets …')
    train_ds = load_jsonl(args.train_file)['train']
    val_ds   = load_jsonl(args.validation_file)['train']
    logger.info(f'  train: {len(train_ds)} examples  |  val: {len(val_ds)} examples')

    def tokenize_fn(examples):
        texts = [
            p + tokenizer.eos_token + r + tokenizer.eos_token
            for p, r in zip(examples['prompt'], examples['response'])
        ]
        return tokenizer(
            texts,
            truncation=True,
            padding='max_length',
            max_length=args.max_length,
        )

    train_ds = train_ds.map(tokenize_fn, batched=True, remove_columns=train_ds.column_names)
    val_ds   = val_ds.map(tokenize_fn,   batched=True, remove_columns=val_ds.column_names)

    train_ds.set_format(type='torch', columns=['input_ids', 'attention_mask'])
    val_ds.set_format(  type='torch', columns=['input_ids', 'attention_mask'])

    # ── Data collator (adds labels = input_ids for CLM loss) ──────────────────
    def data_collator(features):
        input_ids      = torch.stack([f['input_ids']      for f in features])
        attention_mask = torch.stack([f['attention_mask'] for f in features])
        labels         = input_ids.clone()
        return {'input_ids': input_ids, 'attention_mask': attention_mask, 'labels': labels}

    # ── TrainingArguments ──────────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        eval_strategy='epoch',          # replaces deprecated evaluation_strategy
        save_strategy='epoch',
        num_train_epochs=args.num_train_epochs,
        learning_rate=args.learning_rate,
        fp16=use_gpu,                   # fp16 only on GPU
        logging_steps=5,
        load_best_model_at_end=True,
        report_to='none',               # disable wandb / tensorboard
        remove_unused_columns=False,
        dataloader_num_workers=0,       # avoid multiprocessing issues on some systems
    )

    # ── Trainer ────────────────────────────────────────────────────────────────
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
    )

    if args.do_train:
        logger.info('Starting training …')
        trainer.train()
        logger.info(f'Saving LoRA adapter to {args.output_dir} …')
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        logger.info('✅ Training complete. Adapter saved.')
    else:
        logger.info('Dry run complete (tokenisation + model load OK). Add --do_train to start training.')


if __name__ == '__main__':
    main()
