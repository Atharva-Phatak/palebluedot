from transformers import PreTrainedTokenizer
from datasets import Dataset, DatasetDict
import pyarrow
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.types

from typing import Any, TypeVar

DatasetType = TypeVar("DatasetType", Dataset, DatasetDict)


def truncate_dataset(
    dataset: DatasetType, max_length: int, map_kwargs: dict[str, Any] | None = None
) -> DatasetType:
    r"""
    Truncate sequences in a dataset to a specified `max_length`.

    Args:
        dataset ([`~datasets.Dataset`] or [`~datasets.DatasetDict`]):
            Dataset to truncate.
        max_length (`int`):
            Maximum sequence length to truncate to.
        map_kwargs (`dict`, *optional*):
            Additional keyword arguments to pass to the dataset's map method when truncating examples.

    Returns:
        [`~datasets.Dataset`] or [`~datasets.DatasetDict`]: The dataset with truncated sequences.

    Example:
    ```python
    >>> from datasets import Dataset

    >>> examples = {
    ...     "input_ids": [[1, 2, 3], [4, 5, 6, 7], [8]],
    ...     "attention_mask": [[0, 1, 1], [0, 0, 1, 1], [1]],
    ... }
    >>> dataset = Dataset.from_dict(examples)
    >>> truncated_dataset = truncate_dataset(dataset, max_length=2)
    >>> truncated_dataset[:]
    {'input_ids': [[1, 2], [4, 5], [8]],
     'attention_mask': [[0, 1], [0, 0], [1]]}
    ```
    """
    if map_kwargs is None:
        map_kwargs = {}
    if isinstance(dataset, Dataset):
        # Fast truncation with pyarrow
        def truncate(examples):
            truncated_columns = []
            for column in examples.columns:
                if pyarrow.types.is_list(column.type) or pyarrow.types.is_large_list(
                    column.type
                ):
                    column = pc.list_slice(column, 0, max_length)
                truncated_columns.append(column)
            return pa.Table.from_arrays(truncated_columns, names=examples.column_names)

        dataset = dataset.with_format("arrow")
        dataset = dataset.map(truncate, batched=True, **map_kwargs)
        dataset = dataset.with_format(None)
    else:

        def truncate(examples):
            truncated_examples = {}
            for key, column in examples.items():
                if column and isinstance(column[0], list):
                    column = [val[:max_length] for val in column]
                truncated_examples[key] = column
            return truncated_examples

        dataset = dataset.map(
            truncate,
            batched=True,
            **map_kwargs,
        )
    return dataset


def prepare_data_simple(
    processing_class: PreTrainedTokenizer,
    dataset: Dataset,
    max_length: int = None,
    text_field="text",
    batched: bool = False,
):
    """
    Simplest form of data preparation for padding-free.

    Key: max_length is applied HERE during tokenization, BEFORE any flattening.
    The flattening happens later in the data collator at batch time.

    Args:
        max_length:
            - If set: Truncates each individual sample to this length
            - If None: No truncation (keep all tokens)
        batched:
            - False (recommended): Process one sample at a time
            - True: Process in batches (faster but uses more memory)
    """

    def tokenize(example):
        # When batched=False, example is a single dict
        # When batched=True, example contains lists
        text = example[text_field]
        text = text + processing_class.eos_token

        return processing_class(text)

    ds = dataset.map(
        tokenize,
        batched=batched,  # Default False for simplicity
        remove_columns=dataset.column_names,
    )
    if max_length is not None:
        ds = truncate_dataset(dataset=ds, max_length=max_length)
    return ds
