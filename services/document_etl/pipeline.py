from pathlib import Path
import json

from .ocr import extract_text


INPUT_DIR = Path("data/raw/document_stubs")
OUTPUT_DIR = Path("data/processed/document_etl")


def process_document(file_path: str) -> dict:
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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for file in INPUT_DIR.glob("*"):
        result = process_document(str(file))

        output = OUTPUT_DIR / f"{file.stem}.json"
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()