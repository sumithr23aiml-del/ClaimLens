from pathlib import Path

import pytest

from services.document_etl.pipeline import process_document


def test_missing_document():
    with pytest.raises(FileNotFoundError):
        process_document("does_not_exist.pdf")