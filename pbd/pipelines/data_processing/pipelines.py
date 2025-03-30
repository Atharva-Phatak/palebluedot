from zenml import pipeline
from pbd.pipelines.data_processing.steps.data_process import download_youtube_audio

@pipeline(name = "collect_audio_data")
def collect_audio_data(url:str):
    download_youtube_audio(url = url)