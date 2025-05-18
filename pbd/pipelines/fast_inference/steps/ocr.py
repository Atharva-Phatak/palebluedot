from mistralrs import Runner, Which, ChatCompletionRequest
from zenml import step
def load_runner(model_config:dict):
    """
    Load the MistralRS runner with the specified model configuration.
    """
    return  Runner(
    which=Which.GGUF(
        **model_config
    ))

def run_ocr(image_path:str,
            runner: Runner,
            prompt:str,
            generation_config:dict,):
    res = runner.send_chat_completion_request(
    ChatCompletionRequest(
        model="idefics3",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_path
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            },
        ],
        **generation_config
    ))
    return res.choices[0].message.content



@step
def ocr_images(
    image_paths: list[str],
    model_config: dict,
    generation_config: dict,
    prompt: str
) -> list[str]:
    runner = load_runner(model_config)
    return [run_ocr(img, runner, prompt, generation_config) for img in image_paths]
