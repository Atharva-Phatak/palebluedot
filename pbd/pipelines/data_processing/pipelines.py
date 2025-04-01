from zenml import pipeline
from pbd.pipelines.data_processing.steps.data_process import download_youtube_audio
from pbd.pipelines.data_processing.setting import docker_settings, k8s_operator_settings


@pipeline(
    name="collect_audio_data",
    settings={
        "docker": docker_settings,
        "orchestrator": k8s_operator_settings,
    },
)
def collect_audio_data(url: str):
    download_youtube_audio(url=url)


if __name__ == "__main__":
    collect_audio_data(url="https://www.youtube.com/watch?v=wupToqz1e2g")
