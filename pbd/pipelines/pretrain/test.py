"""
Quick test script for PretrainTrainer with small GPT-2 model.
Install requirements: pip install torch transformers accelerate datasets
"""

import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from datasets import load_dataset
from pathlib import Path

# Simple linear warmup + cosine decay

# Import your trainer (adjust path as needed)
from pbd.pipelines.pretrain.steps.callbacks.tracking import WandbCallback
from pbd.pipelines.pretrain.steps.trainer import PretrainTrainer
from pbd.pipelines.pretrain.steps.trainer.scheduler import (
    get_cosine_schedule_with_warmup,
)
import os

os.environ["WANDB_API"] = ""


class SimpleGPT2Trainer(PretrainTrainer):
    """Concrete implementation of PretrainTrainer for GPT-2."""

    def _load_optimizer_and_scheduler(self):
        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.trainer_state.optimizer.lr
        )
        scheduler = get_cosine_schedule_with_warmup(
            optimizer,
            num_warmup_steps=self.trainer_state.scheduler.warmup_steps,
            num_training_steps=self.trainer_state.max_steps,
        )
        return optimizer, scheduler

    def _load_train_dataloader(self):
        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token
        return create_dataloader(
            tokenizer, batch_size=self.trainer_state.batch_size, max_length=512
        )


def create_dataloader(tokenizer, batch_size, max_length=512, num_samples=100000):
    """Create a simple dataloader with WikiText data."""
    # Load a small dataset
    dataset = load_dataset("wikitext", "wikitext-2-raw-v1", split="train")

    # Subsample for faster testing
    if num_samples and num_samples < len(dataset):
        dataset = dataset.select(range(num_samples))
        print(f"Subsampled dataset to {num_samples} examples")

    def tokenize_function(examples):
        # Tokenize and create fixed-length sequences
        tokens = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": tokens["input_ids"],
            "attention_mask": tokens["attention_mask"],
        }

    # Process dataset
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names,
    )

    tokenized_dataset.set_format("torch")

    # Create dataloader
    dataloader = DataLoader(
        tokenized_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
    )

    return dataloader


def main():
    # Configuration
    CHECKPOINT_DIR = Path("./checkpoints")

    print("=" * 80)
    print("Setting up GPT-2 training test")
    print("=" * 80)

    # Create trainer
    print("\n4. Initializing trainer...")
    callbacks = [WandbCallback()]
    trainer = SimpleGPT2Trainer(
        config_path="configs/pretrain/gpt2.yaml",
        callbacks=callbacks,
    )

    # Start training
    print("\n5. Starting training...")
    print("=" * 80)
    trainer.fit()

    # Save final checkpoint
    # print("\n6. Saving final checkpoint...")
    # CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    # trainer.save_checkpoint(str(CHECKPOINT_DIR / "final_checkpoint.pt"))

    print("\n✓ Training complete!")
    print(f"Checkpoints saved to: {CHECKPOINT_DIR}")


if __name__ == "__main__":
    main()
