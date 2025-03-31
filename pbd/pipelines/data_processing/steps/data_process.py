from pbd.pipelines.data_processing.setting import pod_settings, docker_settings
from pytubefix import YouTube
from pytubefix.cli import on_progress

from zenml import step
import logging
import os
from minio import Minio
@step(
    settings = {
        "orchestrator" : pod_settings,
    },
)
def download_youtube_audio(url:str):
    yt = YouTube(url, on_progress_callback=on_progress)
    logging.info(f"Downloading {yt.title}")
    ys = yt.streams.get_audio_only()
    ys.download()



