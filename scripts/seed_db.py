#!/usr/bin/env python
"""Seed ClaimLens products, policies, fraud indicators and demo claims."""
from __future__ import annotations
import hashlib
import json
import os
import random
from datetime import date, datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row

DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'claimlens')} user={os.getenv('DB_USER', 'claimlens')} "
    f"password={os.getenv('DB_PASS', 'claimlens_dev_2026')}"
)
BUCKET = os.getenv('MINIO_BUCKET_DOCS', 'claim-documents')

PRODUCTS = [
    ('MOT-COMP-01', 'Motor Comprehensive', 'motor', 2000, 0,
     '{"metal": 0.0, "plastic": 0.5, "rubber": 0.5, "glass": 0.0}'),
    ('MOT-TP-01', 'Motor Third Party', 'motor', 0, 0, '{}'),
    ('HLT-IND-01', 'Health Individual', 'health', 0, 30, '{}'),
    ('HLT-FAM-01', 'Health Family Floater','health', 0, 30, '{}'),
    ('PRP-HOME-01', 'Home Contents', 'property', 5000, 15, '{}'),
    ('TRV-INT-01', 'Travel International', 'travel', 1500, 0, '{}'),
]

INDICATORS = [
    ('FR001_LATE_REPORTING', 1, 'Loss reported well after the incident date', 15,
     '{"days_threshold": 30}'),
    ('FR002_POLICY_INCEPTION', 1, 'Loss occurred soon after policy inception', 25,
     '{"days_after_inception": 30}'),
    ('FR003_REPEAT_CLAIMANT', 1, 'Multiple claims by the same customer in 12 months', 20,
     '{"claims_in_12m": 3}'),
    ('FR004_ROUND_AMOUNT', 1, 'Claimed amount is an implausibly round figure', 10, '{}'),
    ('FR005_VENDOR_CONCENTRATION', 1, 'Same vendor across an unusual share of claims', 20,
     '{"vendor_share_threshold": 0.6}'),
    ('FR006_PRE_EXISTING_DAMAGE', 1, 'Damage inconsistent with the reported incident', 30, '{}'),
    ('FR007_DOCUMENT_ALTERED', 1, 'Document shows signs of alteration', 35, '{}'),
    ('FR008_NIGHT_LOSS_NO_REPORT', 1, 'Night-time loss with no police report', 15, '{}'),
]

PERILS = {
    'motor': ['own_damage', 'theft', 'third_party'],
    'health': ['hospitalisation', 'day_care'],
    'property': ['fire', 'burglary', 'water_damage'],
    'travel': ['medical_emergency', 'baggage_loss', 'trip_cancellation'],
}

def seed_reference(cur) -> None:
    cur.executemany(
        'INSERT INTO policy_products (product_id, product_name, line_of_business, '
        'base_deductible, waiting_period_days, depreciation_schedule) '
        'VALUES (%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING', PRODUCTS)
    cur.executemany(
        'INSERT INTO fraud_indicators (indicator_code, version, description, weight, params) '
        'VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING', INDICATORS)

def seed_policies(cur, n: int = 120) -> list[dict]:
    issued = []
    for i in range(n):
        cur.execute(
            'INSERT INTO customers (external_ref, full_name, date_of_birth, email, phone, city) '
            'VALUES (%s,%s,%s,%s,%s,%s) RETURNING customer_id',
            (f'CUST{i:05d}', f'Demo Policyholder {i:03d}', date(1980 + i % 25, 3, 14),
             f'demo{i:03d}@example.invalid', f'+91900000{i:04d}',
             random.choice(['Chennai', 'Coimbatore', 'Madurai', 'Salem'])),
        )
        customer_id = cur.fetchone()['customer_id']
        product = random.choice(PRODUCTS)
        inception = date(2025, 1, 1) + timedelta(days=random.randint(0, 330))
        expiry = inception + timedelta(days=365)
        cur.execute(
            'INSERT INTO policies (policy_number, product_id, customer_id, inception_date, '
            'expiry_date) VALUES (%s,%s,%s,%s,%s) RETURNING policy_id',
            (f'POL{i:07d}', product[0], customer_id, inception, expiry),
        )
        policy_id = cur.fetchone()['policy_id']
        cur.execute(
            'INSERT INTO policy_versions (policy_id, version_no, effective_from, '
            'endorsement_reason) VALUES (%s,1,%s,%s) RETURNING version_id',
            (policy_id, inception, 'original issuance'),
        )
        version_id = cur.fetchone()['version_id']
        lob = product[2]
        for peril in PERILS.get(lob, ['general']):
            cur.execute(
                'INSERT INTO coverages (version_id, peril, sum_insured, sub_limit, deductible, '
                'coinsurance_pct) VALUES (%s,%s,%s,%s,%s,%s)',
                (version_id, peril, round(random.choice([200000, 500000, 1000000]), 2),
                 None, product[3], random.choice([0, 0, 0, 10])),
            )
        issued.append({'policy_id': policy_id, 'product': product,
                       'inception': inception, 'expiry': expiry, 'lob': lob,
                       'version_no': 1})
    return issued

def seed_claims(cur, policies: list[dict], n: int = 40) -> None:
    now = datetime.now(timezone.utc)
    for i in range(n):
        p = random.choice(policies)
        peril = random.choice(PERILS.get(p['lob'], ['general']))
        span = (p['expiry'] - p['inception']).days
        loss_date = p['inception'] + timedelta(days=random.randint(1, max(1, span - 1)))
        claimed = round(random.choice([
            random.uniform(4_000, 45_000),
            random.uniform(45_000, 180_000),
            float(random.choice([50_000, 100_000])), 
        ]), 2)
        cur.execute(
            'INSERT INTO claims (claim_number, policy_id, peril, loss_date, loss_location, '
            'reported_at, claimed_amount, description, status) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING claim_id',
            (f'CLM{i:07d}', p['policy_id'], peril, loss_date,
             random.choice(['Chennai', 'Coimbatore', 'Madurai', 'Salem']),
             now - timedelta(days=random.randint(0, 60)), claimed,
             'Demo claim generated for milestone 1 verification.', 'registered'),
        )
        claim_id = cur.fetchone()['claim_id']
        
        cur.execute('SELECT policy_number FROM policies WHERE policy_id = %s', (p['policy_id'],))
        policy_number = cur.fetchone()['policy_number']
        terms = {'peril': peril, 'deductible': p['product'][3],
                 'waiting_period_days': p['product'][4],
                 'depreciation_schedule': json.loads(p['product'][5] or '{}')}
        cur.execute(
            'INSERT INTO policy_snapshots (claim_id, policy_number, product_id, version_no, '
            'inception_date, expiry_date, terms) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)',
            (claim_id, policy_number, p['product'][0], p['version_no'],
             p['inception'], p['expiry'], json.dumps(terms)),
        )
        for d, doc_type in enumerate(['fnol_form', 'policy_schedule', 'repair_invoice'], start=1):
            digest = hashlib.sha256(f'{claim_id}-{doc_type}'.encode()).hexdigest()
            cur.execute(
                'INSERT INTO claim_documents (claim_id, document_type, file_name, storage_uri, '
                'mime_type, page_count, checksum_sha256, ocr_status) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (claim_id, doc_type, f'{doc_type}_{i:04d}.pdf',
                 f's3://{BUCKET}/demo/CLM{i:07d}/{doc_type}.pdf',
                 'application/pdf', random.randint(1, 4), digest, 'pending'),
            )
        for line_no in range(1, random.randint(2, 5)):
            cur.execute(
                'INSERT INTO claim_line_items (claim_id, line_no, description, part_category, '
                'claimed_amount, quantity) VALUES (%s,%s,%s,%s,%s,%s)',
                (claim_id, line_no, f'Demo line item {line_no}',
                 random.choice(['metal', 'plastic', 'rubber', 'glass', 'labour']),
                 round(claimed / 4, 2), 1),
            )

def main() -> None:
    random.seed(20260911)
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS c FROM policy_products')
            if cur.fetchone()['c'] > 0:
                print('already seeded — run `make reset` first to reseed')
                return
            seed_reference(cur)
            policies = seed_policies(cur)
            seed_claims(cur, policies)
            conn.commit()
    print('seeded: 6 products, 8 fraud indicators, 120 policies, 40 claims with snapshots')

if __name__ == '__main__':
    main()
