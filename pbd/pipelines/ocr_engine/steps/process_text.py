from zenml import step
import torch
from vllm import SamplingParams


@step
def format_extracted_content(data, sampling_parameters: dict):
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    sampling_parameters = SamplingParams(**sampling_parameters)
    # model = LLM(
    #    sampling_params=sampling_parameters,
    # )
    # Run inference and add logic to process the data
    return []
