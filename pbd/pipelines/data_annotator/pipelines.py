from metaflow import step, FlowSpec, kubernetes, Parameter, schedule
import os
import argilla as rg
from pbd.helper.s3_paths import formatted_results_path
from pbd.helper.file_download import download_from_minio
from datasets import load_dataset
from pbd.helper.slack import send_slack_message

IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-data_annotator:latest"


@schedule()
class TextToTextRatingFlow(FlowSpec):

    filename = Parameter("filename", help="Name of the input file (without extension)")
    # minio_endpoint = Parameter("minio_endpoint", help="MinIO endpoint URL")
    # bucket = Parameter("bucket", default="data-bucket", help="MinIO bucket name")

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=1,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def start(self):
        self.minio_endpoint = "minio-palebluedot.io"
        self.bucket = "data-bucket"
        self.data = self._load_data()
        print(f"Loaded {len(self.data)} samples.")
        self.next(self.push_to_argilla)

    def _load_data(self):
        formatted_results = formatted_results_path(filename=self.filename)
        local_path = download_from_minio(
            endpoint=self.minio_endpoint,
            bucket=self.bucket,
            object_key=formatted_results,
            local_path=f"/tmp/{self.filename}.parquet",
        )
        ds = load_dataset("parquet", data_files=[local_path])
        return ds["train"].to_list()

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=1,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def push_to_argilla(self):
        rg.init(
            api_url="http://argilla.palebluedot.io",
            api_key=os.environ.get("argilla_apiKey"),
        )
        records = []
        for sample in self.data:
            record = rg.Text2TextRecord(
                text=sample["content"],
                prediction=sample["generated"],
                metadata={"source": self.filename},
            )
            records.append(record)

        dataset_name = f"{self.filename}_ocr_post_process"
        rg.log(records, name=dataset_name, workspace="admin")
        print(f"Pushed {len(records)} records to Argilla: {dataset_name}")
        self.dataset_name = dataset_name
        self.next(self.end)

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=1,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def end(self):
        token = os.environ.get("SLACK_TOKEN")
        message = f"Annotation ready in Argilla UI: http://argilla.palebluedot.io/datasets/{self.dataset_name}"
        send_slack_message(token=token, message=message)
        print("Annotation ready in Argilla UI.")


if __name__ == "__main__":
    TextToTextRatingFlow()
