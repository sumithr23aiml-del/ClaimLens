import os

import requests


TIKA_URL = os.getenv(
    "TIKA_URL",
    "http://localhost:9998",
)


def extract_text(file_path: str) -> str:
    """Extract text from a document using Apache Tika."""

    with open(file_path, "rb") as file:
        response = requests.put(
            f"{TIKA_URL}/tika",
            data=file,
            headers={
                "Accept": "text/plain",
            },
            timeout=60,
        )

    response.raise_for_status()

    return response.text