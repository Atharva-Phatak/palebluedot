from metaflow import step, FlowSpec, kubernetes, Parameter
import os
import argilla as rg
from pbd.helper.s3_paths import formatted_results_path
from pbd.helper.file_download import download_from_minio
from datasets import load_dataset
from pbd.helper.slack import send_slack_message

IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-data_annotator:latest"


class TextToTextRatingFlow(FlowSpec):
    filename = Parameter("filename", help="Name of the input file (without extension)")

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
        # Initialize Argilla client
        client = rg.Argilla(
            api_url="http://argilla.palebluedot.io",
            api_key=os.environ.get("argilla_apiKey"),
        )

        # Create dataset name
        dataset_name = f"{self.filename}_ocr_post_process"

        # Create dataset settings for text-to-text annotation
        settings = rg.Settings(
            fields=[
                rg.TextField(
                    name="original_text",
                    title="Original Text",
                    use_markdown=True,  # Enable markdown for basic formatting
                ),
                rg.TextField(
                    name="generated_text",
                    title="Generated Text",
                    use_markdown=True,  # Enable markdown for basic formatting
                ),
            ],
            questions=[
                rg.TextQuestion(
                    name="corrected_text",
                    title="Corrected Text",
                    description="Please modify/correct the generated text as needed (LaTeX math: $...$, bold: **text**, italic: *text*)",
                    required=True,
                    use_markdown=True,  # Enable markdown in the text input as well
                )
            ],
            metadata=[rg.TermsMetadataProperty(name="source", title="Source File")],
        )

        # Create or get dataset
        try:
            dataset = client.datasets(name=dataset_name, workspace="admin")
            print(f"Dataset '{dataset_name}' already exists, adding records to it.")
        except Exception:
            dataset = rg.Dataset(
                name=dataset_name,
                workspace="admin",
                settings=settings,
            )
            dataset = dataset.create()
            print(f"Created new dataset: {dataset_name}")

        # Prepare records
        records = []
        for sample in self.data:
            record = rg.Record(
                fields={
                    "original_text": sample["content"],
                    "generated_text": sample["generated"],
                },
                metadata={"source": self.filename},
                # Pre-populate the correction field with the generated text
                suggestions=[
                    rg.Suggestion(
                        question_name="corrected_text", value=sample["generated"]
                    )
                ],
            )
            records.append(record)

        # Log records to dataset
        dataset.records.log(records)
        print(f"Pushed {len(records)} records to Argilla dataset: {dataset_name}")

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
