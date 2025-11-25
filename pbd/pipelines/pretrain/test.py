"""
Quick test script for PretrainTrainer with small GPT-2 model.
Install requirements: pip install torch transformers accelerate datasets
"""

import torch
from torch.utils.data import DataLoader
from transformers import GPT2LMHeadModel, GPT2Config, AutoTokenizer
from datasets import load_dataset
from pathlib import Path

# Simple linear warmup + cosine decay
from torch.optim.lr_scheduler import CosineAnnealingLR

# Import your trainer (adjust path as needed)
from pbd.pipelines.pretrain.steps.trainer import PretrainTrainer


class SimpleGPT2Trainer(PretrainTrainer):
    """Concrete implementation of PretrainTrainer for GPT-2."""

    def forward(self, batch):
        """Forward pass that returns loss and token count."""
        outputs = self.model(**batch, labels=batch["input_ids"])
        loss = outputs.loss
        tokens_processed = batch["input_ids"].numel()
        return loss, tokens_processed


def create_tiny_gpt2():
    """Create a tiny GPT-2 model for quick testing."""
    config = GPT2Config(
        vocab_size=50257,
        n_positions=128,  # Short context
        n_embd=256,  # Small embedding
        n_layer=4,  # Few layers
        n_head=4,  # Few heads
    )
    model = GPT2LMHeadModel(config)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    return model


def create_dataloader(tokenizer, batch_size=8, max_length=128, num_samples=1000):
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
    BATCH_SIZE = 8
    MAX_STEPS = 500
    LEARNING_RATE = 5e-4
    GRADIENT_ACCUMULATION = 2
    LOG_EVERY = 10
    CHECKPOINT_DIR = Path("./checkpoints")
    NUM_SAMPLES = 1000  # Subsample dataset for quick testing

    print("=" * 80)
    print("Setting up GPT-2 training test")
    print("=" * 80)

    # Create model and tokenizer
    print("\n1. Creating tiny GPT-2 model...")
    model = create_tiny_gpt2()
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

    # Create dataloader
    print("\n2. Loading WikiText-2 dataset...")
    train_loader = create_dataloader(
        tokenizer,
        batch_size=BATCH_SIZE,
        num_samples=NUM_SAMPLES,
    )
    print(f"Dataset size: {len(train_loader.dataset):,} examples")

    # Create optimizer and scheduler
    print("\n3. Setting up optimizer and scheduler...")
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    scheduler = CosineAnnealingLR(optimizer, T_max=MAX_STEPS)

    # Create trainer
    print("\n4. Initializing trainer...")
    trainer = SimpleGPT2Trainer(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        train_loader=train_loader,
        max_steps=MAX_STEPS,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        log_every=LOG_EVERY,
        gradient_clip_norm=1.0,
        mixed_precision="fp16",  # Use "bf16" if available, or None for fp32
        seed=42,
    )

    # Start training
    print("\n5. Starting training...")
    print("=" * 80)
    trainer.fit()

    # Save final checkpoint
    print("\n6. Saving final checkpoint...")
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_checkpoint(str(CHECKPOINT_DIR / "final_checkpoint.pt"))

    print("\n✓ Training complete!")
    print(f"Checkpoints saved to: {CHECKPOINT_DIR}")


if __name__ == "__main__":
    main()
