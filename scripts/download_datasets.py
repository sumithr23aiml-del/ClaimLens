#!/usr/bin/env python
"""Stage ClaimLens document-understanding datasets."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
DOCS = RAW / 'documents'

PUBLIC = {
    'funsd.zip': 'https://guillaumejaume.github.io/FUNSD/dataset.zip',
}

REGISTERED = [
    ('RVL-CDIP', 'https://adamharley.com/rvl-cdip/',
     'extract images/ and labels/ under data/raw/rvl-cdip/'),
    ('DocVQA', 'https://www.docvqa.org/datasets',
     'register, then extract under data/raw/docvqa/'),
]

def fetch(name: str, url: str) -> None:
    target = RAW / name
    if target.exists():
        print(f'[skip] {name}')
        return
    print(f'[get ] {name}')
    urlretrieve(url, target)
    if target.suffix == '.zip':
        with zipfile.ZipFile(target) as zf:
            zf.extractall(RAW / target.stem)

def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / '.gitkeep').touch()
    for name, url in PUBLIC.items():
        try:
            fetch(name, url)
        except Exception as exc:
            print(f'[warn] {name} failed: {exc}')
    
    print()
    print('Datasets requiring registration:')
    for name, url, hint in REGISTERED:
        print(f' - {name}: {url}')
        print(f'   {hint}')
    
    print()
    print('Real claim documents contain personal and financial data.')
    print('data/raw/documents/ is git-ignored — never commit a claim packet.')
    print('Next: dvc add data/raw && dvc push')
    return 0

if __name__ == '__main__':
    sys.exit(main())
