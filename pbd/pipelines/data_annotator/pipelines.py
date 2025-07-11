from metaflow import step, FlowSpec, kubernetes, trigger_on_finish
import os
import argilla as rg

IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-data_annotator:latest"


@trigger_on_finish()
class TextToTextRatingFlow(FlowSpec):

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=1,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def start(self):
        print(f"Loaded {len(self.data)} samples.")
        self.next(self.push_to_argilla)

    @step
    def push_to_argilla(self):
        # Login to Argilla
        rg.init(
            api_url="http://argilla.palebluedot.io",
            api_key=os.environ.get("argilla_apiKey"),
        )  # adjust for your server
        records = []
        for sample in self.data:
            record = rg.Text2TextRecord(
                id=sample["id"],
                text=sample["problem"],
                prediction=sample["solution"],  # Optional: initial guess
                metadata={
                    "source": "ocr-post-process",
                },
                # You can leave annotation blank for manual UI annotation
            )
            records.append(record)

        dataset_name = "postproc_text2text_rating"
        rg.log(records, name=dataset_name, workspace="admin")  # set your workspace
        print(f"Pushed {len(records)} records to Argilla: {dataset_name}")
        self.dataset_name = dataset_name
        self.next(self.end)

    @step
    def end(self):
        print("Annotation ready in Argilla UI.")
        print(f"👉 Visit http://localhost:6900 and open dataset: {self.dataset_name}")


if __name__ == "__main__":
    TextToTextRatingFlow()
