"""
qlora_train.py
----------------
Parameter-efficient fine-tuning (QLoRA) training script template.

Notes:
- Requires a HuggingFace-compatible base model (weights accessible via `model_name_or_path`).
- This script does a small dry-run by default; set --do_train to run a longer job.
- Exports adapter checkpoints to `output_dir` (PEFT format).

Usage (dry-run):
  python scripts/qlora_train.py --model_name_or_path <HF_MODEL> --train_file data/training/train.jsonl --validation_file data/training/val.jsonl --output_dir outputs/qlora_smoke

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
)

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_jsonl(path):
    return datasets.load_dataset('json', data_files=str(path))


def preprocess(dataset, tokenizer, max_length=1024):
    def concat_examples(example):
        # Expect each example to have 'prompt' and 'response' fields
        prompt = example.get('prompt', '')
        response = example.get('response', '')
        text = prompt + tokenizer.eos_token + response + tokenizer.eos_token
        return {'input_ids': tokenizer(text, truncation=True, max_length=max_length).input_ids}

    return dataset.map(lambda ex: tokenizer(ex['prompt'] + tokenizer.eos_token + ex['response'], truncation=True, max_length=max_length), batched=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name_or_path', required=True, help='HF model identifier or local path (must be compatible)')
    parser.add_argument('--train_file', type=Path, required=True)
    parser.add_argument('--validation_file', type=Path, required=True)
    parser.add_argument('--output_dir', type=Path, default=Path('outputs/qlora'))
    parser.add_argument('--per_device_train_batch_size', type=int, default=4)
    parser.add_argument('--per_device_eval_batch_size', type=int, default=4)
    parser.add_argument('--learning_rate', type=float, default=2e-4)
    parser.add_argument('--num_train_epochs', type=int, default=1)
    parser.add_argument('--max_length', type=int, default=512)
    parser.add_argument('--lora_rank', type=int, default=8)
    parser.add_argument('--lora_alpha', type=int, default=16)
    parser.add_argument('--lora_dropout', type=float, default=0.05)
    parser.add_argument('--do_train', action='store_true')
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info('Loading tokenizer...')
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({'pad_token': '[PAD]'})

    logger.info('Loading model (k-bit quantization will be enabled if supported)...')
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name_or_path,
        load_in_4bit=True,
        device_map='auto',
        torch_dtype=torch.float16,
    )

    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)

    # PEFT config (LoRA)
    peft_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj'],
        lora_dropout=args.lora_dropout,
        bias='none',
        task_type='CAUSAL_LM'
    )

    model = get_peft_model(model, peft_config)

    # Load datasets
    logger.info('Loading datasets...')
    train_ds = load_jsonl(args.train_file)['train']
    val_ds = load_jsonl(args.validation_file)['train']

    # Tokenize (simple approach: concat prompt + response)
    def tokenize_fn(examples):
        texts = [p + tokenizer.eos_token + r + tokenizer.eos_token for p, r in zip(examples['prompt'], examples['response'])]
        return tokenizer(texts, truncation=True, padding='max_length', max_length=args.max_length)

    train_ds = train_ds.map(tokenize_fn, batched=True, remove_columns=train_ds.column_names)
    val_ds = val_ds.map(tokenize_fn, batched=True, remove_columns=val_ds.column_names)

    # Convert to torch format
    train_ds.set_format(type='torch', columns=['input_ids', 'attention_mask'])
    val_ds.set_format(type='torch', columns=['input_ids', 'attention_mask'])

    # Training args
    training_args = TrainingArguments(
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        evaluation_strategy='epoch',
        num_train_epochs=args.num_train_epochs,
        learning_rate=args.learning_rate,
        output_dir=str(args.output_dir),
        logging_steps=10,
        save_strategy='epoch',
        fp16=True,
        remove_unused_columns=False,
    )

    def data_collator(features):
        input_ids = [f['input_ids'] for f in features]
        attention_mask = [f['attention_mask'] for f in features]
        input_ids = torch.stack(input_ids)
        attention_mask = torch.stack(attention_mask)
        labels = input_ids.clone()
        return {'input_ids': input_ids, 'attention_mask': attention_mask, 'labels': labels}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
    )

    if args.do_train:
        logger.info('Starting training...')
        trainer.train()
        logger.info('Saving adapter checkpoint...')
        model.save_pretrained(args.output_dir)
    else:
        logger.info('Dry run complete. To run training add --do_train')


if __name__ == '__main__':
    main()
