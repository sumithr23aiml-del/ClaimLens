#!/usr/bin/env python
"""M1 acceptance checks for ClaimLens."""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.request

import psycopg

DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'claimlens')} user={os.getenv('DB_USER', 'claimlens')} "
    f"password={os.getenv('DB_PASS', 'claimlens')}"
)
TIKA = os.getenv('TIKA_URL', 'http://localhost:9998')

EXPECTED_TABLES = {
    'policy_products', 'customers', 'policies', 'policy_versions', 'coverages', 'claims',
    'policy_snapshots', 'claim_documents', 'extracted_fields', 'claim_line_items',
    'fraud_indicators', 'fraud_assessments', 'claim_decisions', 'settlement_lines',
}

failures: list[str] = []

def check(label: str, ok: bool, detail: str = '') -> None:
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)

def main() -> int:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema='public'")
            found = {r[0] for r in cur.fetchall()}
            missing = EXPECTED_TABLES - found
            check('schema: all 14 tables present', not missing,
                  f'missing {sorted(missing)}' if missing else '14/14')

            cur.execute('SELECT count(*) FROM policies')
            check('seed: policies issued', cur.fetchone()[0] >= 120)

            cur.execute('SELECT count(*) FROM fraud_indicators')
            check('seed: fraud indicator catalogue', cur.fetchone()[0] >= 8)

            cur.execute('SELECT count(*) FROM claims c '
                        'LEFT JOIN policy_snapshots s USING (claim_id) '
                        'WHERE s.claim_id IS NULL')
            check('integrity: every claim has a policy snapshot', cur.fetchone()[0] == 0)

            cur.execute('SELECT count(*) FROM claims c JOIN claim_documents d USING (claim_id)')
            check('seed: claim documents registered', cur.fetchone()[0] > 0)

        # the duplicate-document guard must actually fire
        with conn.cursor() as cur:
            cur.execute('SELECT claim_id, checksum_sha256 FROM claim_documents LIMIT 1')
            row = cur.fetchone()
            if not row:
                check('constraint: duplicate document blocked', False, 'no documents found')
            else:
                claim_id, digest = row
                try:
                    with conn.cursor() as cur2:
                        cur2.execute(
                            'INSERT INTO claim_documents (claim_id, document_type, file_name, '
                            'storage_uri, checksum_sha256) '
                            "VALUES (%s,'fnol_form','dup.pdf','s3://x/dup.pdf',%s)",
                            (claim_id, digest))
                    conn.rollback()
                    check('constraint: duplicate document blocked', False, 'insert succeeded')
                except psycopg.errors.UniqueViolation:
                    conn.rollback()
                    check('constraint: duplicate document blocked', True)

    try:
        with urllib.request.urlopen(f'{TIKA}/tika', timeout=8) as r:
            check('tika: reachable', r.status == 200)
    except Exception as exc:
        check('tika: reachable', False, str(exc))

    rc = subprocess.run([sys.executable, '-m', 'pytest', '-q'], capture_output=True, text=True)
    check('domain: unit tests', rc.returncode == 0)

    print()
    if failures:
        print(f'M1 NOT COMPLETE — {len(failures)} check(s) failed')
        return 1
    
    print('M1 COMPLETE — safe to tag v0.1.0-M1')
    return 0

if __name__ == '__main__':
    sys.exit(main())
