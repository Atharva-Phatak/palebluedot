def data_processing_pipeline_config_path():
    return "pipeline_configs/data_processing/config.json"



def ocr_engine_config_path():
    return "pipeline_configs/ocr_engine/config.json"


def ocr_post_process_config_path():
    return "pipeline_configs/ocr_post_process/config.json"


def raw_data_path(filename: str):
    return f"raw_data/{filename}.pdf"


def minio_zip_path(filename: str):
    return f"extracted_data/{filename}.zip"


def ocr_results_path(filename: str):
    return f"ocr_results/{filename}.parquet"


def formatted_results_path(filename: str):
    return f"formatted_results/{filename}.parquet"

def pdf_markdown_path(filename: str):
    return f"markdowns/{filename}.md"
