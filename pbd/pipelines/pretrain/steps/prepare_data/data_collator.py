from dataclasses import dataclass
from typing import Any
from transformers.data.data_collator import DataCollatorMixin
import torch
import numpy as np


def pad(
    tensors: list[torch.Tensor],
    padding_value: int = 0,
    padding_side: str = "right",
    pad_to_multiple_of: int | None = None,
) -> torch.Tensor:
    """
    Pads a list of tensors to the same shape along the first dimension.

    Args:
        tensors (`list[torch.Tensor]`):
            List of input tensors to pad.
        padding_value (`int`):
            Value to use for padding. Default is 0.
        padding_side (`str`):
            Side on which to add padding. Must be 'left' or 'right'. Default is 'right'.
        pad_to_multiple_of (`int`, *optional*):
            If set will pad the sequence to a multiple of the provided value.

    Returns:
        `torch.Tensor`:
            A single tensor containing the padded tensors.

    Examples:
    ```python
    >>> import torch

    >>> pad([torch.tensor([1, 2, 3]), torch.tensor([4, 5])])
    tensor([[1, 2, 3],
            [4, 5, 0]])

    >>> pad([torch.tensor([[1, 2], [3, 4]]), torch.tensor([[5, 6]])])
    tensor([[[1, 2],
            [3, 4]],
            [[5, 6],
            [0, 0]]])
    ```
    """
    # Determine the maximum shape for each dimension
    output_shape = np.max([t.shape for t in tensors], 0).tolist()

    # Apply pad_to_multiple_of to the first (sequence) dimension
    if pad_to_multiple_of is not None:
        remainder = output_shape[0] % pad_to_multiple_of
        if remainder != 0:
            output_shape[0] += pad_to_multiple_of - remainder

    # Create an output tensor filled with the padding value
    output = torch.full(
        (len(tensors), *output_shape),
        padding_value,
        dtype=tensors[0].dtype,
        device=tensors[0].device,
    )

    for i, t in enumerate(tensors):
        if padding_side == "left":
            seq_start = output_shape[0] - t.shape[0]
        elif padding_side == "right":
            seq_start = 0
        else:
            raise ValueError("padding_side must be 'left' or 'right'")

        # Define the slices
        seq_slice = slice(seq_start, seq_start + t.shape[0])
        slices = (seq_slice,) + tuple(slice(0, s) for s in t.shape[1:])
        output[i][slices] = t

    return output


@dataclass
class DataCollatorForLanguageModeling(DataCollatorMixin):
    """
    Data collator used for language modeling data. Inputs are dynamically padded to the maximum length of a batch.

    This collator expects each example in the input list to be a dictionary containing at least the `"input_ids"` key.
    If the input contains a `"completion_mask"`, it is used to set the labels to `-100` for tokens that are not in the
    completion. If `"assistant_masks"` are present, they are used to set the labels to `-100` for tokens that are not
    in the assistant part of the sequence. The collator returns a dictionary containing the following keys:
    - `"input_ids"`: Tensor of input IDs, padded to the maximum length of the batch.
    - `"labels"`: Tensor of labels, padded to the maximum length of the batch. If `completion_only_loss` is set to
    `True`, tokens that are not in the completion are set to -100. If `assistant_masks` are present, tokens that are
    not in the assistant part of the sequence are set to -100. If `padding_free` is set to `False`, the following key
    is also returned:
    - `"attention_mask"`: Tensor of attention masks, padded to the maximum length of the batch.
    If `padding_free` is set to `True`, the following key is also returned:
    - `"position_ids"`: Tensor of position IDs, padded to the maximum length of the batch.

    Args:
        pad_token_id (`int`):
            Token ID to use for padding.
        completion_only_loss (`bool`, *optional*, defaults to `True`):
            When the input contains a completion mask (`completion_mask`), the labels are set to -100 for the tokens
            that are no in the completion.
        padding_free (`bool`, *optional*, defaults to `False`):
            If set to `True`, the sequences will be flattened into a single sequence, and the position IDs will be
            generated accordingly and returned instead of the attention mask.
        pad_to_multiple_of (`int`, *optional*):
            If set, the sequences will be padded to a multiple of this value.
        return_tensors (`str`, *optional*, defaults to `"pt"`):
            Type of Tensor to return. Only `"pt"` is currently supported.

    Examples:
    ```python
    >>> from trl.trainer.sft_trainer import DataCollatorForLanguageModeling

    >>> collator = DataCollatorForLanguageModeling(pad_token_id=0)
    >>> examples = [{"input_ids": [1, 2, 3]}, {"input_ids": [4, 5]}]
    >>> collator(examples)
    {'input_ids': tensor([[  1,  2,  3],
                          [  4,  5,  0]]),
     'attention_mask': tensor([[  1,  1,  1],
                               [  1,  1,  0]]),
     'labels': tensor([[   1,    2,    3],
                       [   4,    5, -100]])}

    >>> # With completion mask
    >>> examples = [
    ...     {"input_ids": [1, 2, 3], "completion_mask": [0, 1, 1]},
    ...     {"input_ids": [4, 5], "completion_mask": [0, 1]},
    ... ]
    >>> collator(examples)
    {'input_ids': tensor([[  1,  2,  3],
                          [  4,  5,  0]]),
     'attention_mask': tensor([[  1,  1,  1],
                               [  1,  1,  0]]),
     'labels': tensor([[-100,    2,    3],
                       [-100,    5, -100]])}

    >>> # With padding_free
    >>> collator = DataCollatorForLanguageModeling(pad_token_id=0, padding_free=True)
    >>> collator(examples)
    {'input_ids': tensor([[ 1, 2, 3, 4, 5]]),
     'position_ids': tensor([[0, 1, 2, 0, 1]]),
     'labels': tensor([[1, 2, 3, 4, 5]])}
    ```
    """

    pad_token_id: int
    completion_only_loss: bool = True
    padding_free: bool = False
    pad_to_multiple_of: int | None = None
    return_tensors: str = "pt"

    def torch_call(self, examples: list[dict[str, Any]]) -> dict[str, Any]:
        # Convert to tensor
        input_ids = [torch.tensor(example["input_ids"]) for example in examples]
        if "labels" in examples[0]:
            labels = [torch.tensor(example["labels"]) for example in examples]
        else:
            labels = [torch.tensor(example["input_ids"]) for example in examples]

        # For padding-free, we should NOT create attention_mask as it causes FlashAttention to ignore position_ids and
        # compute wrong cu_seq_lens from the all-1s mask
        if self.padding_free:
            if "seq_lengths" in examples[0]:
                position_ids = self.get_position_ids_from_packed_seq_lengths(
                    [example["seq_lengths"] for example in examples]
                )
            else:
                position_ids = [torch.arange(len(ids)) for ids in input_ids]
        else:
            attention_mask = [torch.ones_like(ids) for ids in input_ids]
        if self.completion_only_loss and "completion_mask" in examples[0]:
            completion_mask = [
                torch.tensor(example["completion_mask"]) for example in examples
            ]
        if "assistant_masks" in examples[0]:
            assistant_masks = [
                torch.tensor(example["assistant_masks"]) for example in examples
            ]

        # If padding_free, flatten everything into a single sequence
        output = {}
        if self.padding_free:
            input_ids = [torch.cat(input_ids, dim=0)]
            labels = [torch.cat(labels, dim=0)]
            position_ids = [torch.cat(position_ids, dim=0)]
            if self.completion_only_loss and "completion_mask" in examples[0]:
                completion_mask = [torch.cat(completion_mask, dim=0)]
            if "assistant_masks" in examples[0]:
                assistant_masks = [torch.cat(assistant_masks, dim=0)]

        # Pad
        output["input_ids"] = pad(
            input_ids,
            padding_value=self.pad_token_id,
            padding_side="right",
            pad_to_multiple_of=self.pad_to_multiple_of,
        )
        output["labels"] = pad(
            labels,
            padding_value=-100,
            padding_side="right",
            pad_to_multiple_of=self.pad_to_multiple_of,
        )
        if self.padding_free:
            output["position_ids"] = pad(
                position_ids,
                padding_value=0,
                padding_side="right",
                pad_to_multiple_of=self.pad_to_multiple_of,
            )
            output["labels"][output["position_ids"] == 0] = -100
        else:
            output["attention_mask"] = pad(
                attention_mask,
                padding_value=0,
                padding_side="right",
                pad_to_multiple_of=self.pad_to_multiple_of,
            )
        if self.completion_only_loss and "completion_mask" in examples[0]:
            completion_mask = pad(
                completion_mask,
                padding_value=0,
                padding_side="right",
                pad_to_multiple_of=self.pad_to_multiple_of,
            )
            output["labels"][
                completion_mask == 0
            ] = -100  # mask everything that is not in the completion
        if "assistant_masks" in examples[0]:
            assistant_masks = pad(
                assistant_masks,
                padding_value=0,
                padding_side="right",
                pad_to_multiple_of=self.pad_to_multiple_of,
            )
            output["labels"][assistant_masks == 0] = -100
        return output

    @staticmethod
    def get_position_ids_from_packed_seq_lengths(
        batch_seq_lengths: list[list[int]],
    ) -> list[torch.Tensor]:
        """
        Get position IDs for packed sequences.

        Args:
            batch_seq_lengths (`list[list[int]]`):
                A list of lists containing the lengths of each individual document in the packed batch.

        Return:
            `list[torch.Tensor]`:
                A list of tensors containing the position IDs for each packed sequence.
        """
        # Get lengths per row
        example_lengths = [sum(seq_lengths) for seq_lengths in batch_seq_lengths]
        # Flat list of lengths
        batch_seq_lengths = torch.tensor(
            [
                seq_length
                for seq_lengths in batch_seq_lengths
                for seq_length in seq_lengths
            ]
        )
        position_ids = torch.ones(sum(example_lengths), dtype=batch_seq_lengths.dtype)
        position_ids[0] = 0
        # Reset position ids to 0 at the start of each sequence
        position_ids[batch_seq_lengths[:-1].cumsum(0)] = -(batch_seq_lengths[:-1] - 1)
        position_ids = position_ids.cumsum(0)
        # Split back into one tensor per example
        return list(position_ids.split(example_lengths))
