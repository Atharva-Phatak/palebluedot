from metaflow import step, FlowSpec, kubernetes, trigger_on_finish, current
import os
import argilla as rg
from pbd.helper.s3_paths import formatted_results_path
from pbd.helper.file_download import download_from_minio
from datasets import load_dataset
from pbd.helper.slack import send_slack_message

IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-data_annotator:latest"


@trigger_on_finish(flow="OCRPostProcessFlow")
class TextToTextRatingFlow(FlowSpec):

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
        self.slack_token = os.environ.get("SLACK_TOKEN")
        self.data = self._load_data()
        print(f"Loaded {len(self.data)} samples.")
        self.next(self.push_to_argilla)

    def _load_data(self):
        self.filename = current.trigger.run.data.config.filename
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

        workspace = client.workspaces("pbd")
        if workspace is None:
            print("Creating workspace 'pbd' in Argilla...")
            workspace_to_create = rg.Workspace(name="pbd")
            _ = workspace_to_create.create()

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

        # Create dataset (always create new one to avoid workspace issues)
        dataset = rg.Dataset(
            name=dataset_name,
            settings=settings,
            client=client,
            workspace="pbd"
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

        print("Annotation ready in Argilla UI.")
        send_slack_message(
            token=self.slack_token,
            message=f"✅ Annotation ready in Argilla for {self.dataset_name}!",
            channel="#zenml-pipelines",
        )


if __name__ == "__main__":
    TextToTextRatingFlow()
