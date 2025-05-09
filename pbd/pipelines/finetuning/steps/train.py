from unsloth import FastLanguageModel, FastModel
from trl import Gr

def load_model(model_config:dict) -> FastLanguageModel:
    """
    Load a language model from the specified model name.

    Args:
        model_name (str): The name of the model to load.

    Returns:
        FastLanguageModel: The loaded language model.
    """
    model, tokenizer =  FastLanguageModel.from_pretrained(**model_config)
    peft_model = FastModel.get_peft_model(
        model,
        finetune_vision_layers     = False, # Turn off for just text!
        finetune_language_layers   = True,  # Should leave on!
        finetune_attention_modules = True,  # Attention good for GRPO
        finetune_mlp_modules       = True,  # SHould leave on always!

        r = 8,           # Larger = higher accuracy, but might overfit
        lora_alpha = 8,  # Recommended alpha == r at least
        lora_dropout = 0,
        bias = "none",
        random_state = 3407,
    )
    return peft_model, tokenizer



