from pathlib import Path

from .ocr import extract_text


def process_document(file_path: str) -> dict:
    """Run a document through the M1 ETL scaffold."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    text = extract_text(str(path))

    return {
        "file_name": path.name,
        "mime_type": "application/pdf",
        "text": text,
        "text_length": len(text),
    }