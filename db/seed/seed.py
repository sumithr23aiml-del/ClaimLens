import os

import json
from datetime import date, timedelta

import psycopg

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://claimlens:claimlens@localhost:5432/claimlens",
)

POLICY_PRODUCTS = [
    ("MOTOR-COMP", "Motor Comprehensive", "motor", 5000, 0),
    ("MOTOR-TP", "Motor Third Party", "motor", 0, 0),
    ("HEALTH-BASIC", "Health Basic", "health", 1000, 30),
    ("HEALTH-PLUS", "Health Plus", "health", 500, 15),
    ("PROPERTY-HOME", "Home Property", "property", 2500, 0),
    ("TRAVEL-PLUS", "Travel Plus", "travel", 250, 0),
]


def seed_claims(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                p.policy_id,
                p.policy_number,
                p.product_id,
                p.inception_date,
                p.expiry_date,
                pv.version_no,
                c.sum_insured,
                c.deductible
            FROM policies p
            JOIN policy_versions pv
                ON pv.policy_id = p.policy_id
            JOIN coverages c
                ON c.version_id = pv.version_id
            WHERE pv.version_no = 1
            ORDER BY p.policy_number
            LIMIT 40;
        """)

        policies = cur.fetchall()

        for i, policy in enumerate(policies, start=1):
            (
                policy_id,
                policy_number,
                product_id,
                inception_date,
                expiry_date,
                version_no,
                sum_insured,
                deductible,
            ) = policy

            loss_date = inception_date + timedelta(days=30 + i)

            claim_number = f"CLM-{i:04d}"

            cur.execute(
                """
                INSERT INTO claims
                    (
                        claim_number,
                        policy_id,
                        peril,
                        loss_date,
                        loss_location,
                        claimed_amount,
                        description,
                        status,
                        assigned_to
                    )
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, 'documents_pending', %s)
                ON CONFLICT (claim_number)
                DO UPDATE SET
                    policy_id = EXCLUDED.policy_id,
                    peril = EXCLUDED.peril,
                    loss_date = EXCLUDED.loss_date,
                    loss_location = EXCLUDED.loss_location,
                    claimed_amount = EXCLUDED.claimed_amount,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    assigned_to = EXCLUDED.assigned_to
                RETURNING claim_id;
                """,
                (
                    claim_number,
                    policy_id,
                    "accidental_damage",
                    loss_date,
                    "Chennai",
                    25000 + (i * 500),
                    f"Demo insurance claim {i:04d}",
                    "demo-adjuster",
                ),
            )

            claim_id = cur.fetchone()[0]

            # Immutable FNOL policy snapshot
            terms = {
                "sum_insured": float(sum_insured),
                "deductible": float(deductible),
                "source": "policy_version_1",
            }

            cur.execute(
                """
                INSERT INTO policy_snapshots
                    (
                        claim_id,
                        policy_number,
                        product_id,
                        version_no,
                        inception_date,
                        expiry_date,
                        terms
                    )
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (claim_id)
                DO UPDATE SET
                    policy_number = EXCLUDED.policy_number,
                    product_id = EXCLUDED.product_id,
                    version_no = EXCLUDED.version_no,
                    inception_date = EXCLUDED.inception_date,
                    expiry_date = EXCLUDED.expiry_date,
                    terms = EXCLUDED.terms;
                """,
                (
                    claim_id,
                    policy_number,
                    product_id,
                    version_no,
                    inception_date,
                    expiry_date,
                    json.dumps(terms),
                ),
            )

    print("Seeded 40 demo claims with policy snapshots")

def seed_policy_products(conn):
    with conn.cursor() as cur:
        for product_id, name, lob, deductible, waiting_days in POLICY_PRODUCTS:
            cur.execute(
                """
                INSERT INTO policy_products
                    (
                        product_id,
                        product_name,
                        line_of_business,
                        base_deductible,
                        waiting_period_days,
                        depreciation_schedule
                    )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (product_id)
                DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    line_of_business = EXCLUDED.line_of_business,
                    base_deductible = EXCLUDED.base_deductible,
                    waiting_period_days = EXCLUDED.waiting_period_days,
                    depreciation_schedule = EXCLUDED.depreciation_schedule;
                """,
                (
                    product_id,
                    name,
                    lob,
                    deductible,
                    waiting_days,
                    "{}",
                ),
            )


def seed_policies(conn):
    with conn.cursor() as cur:
        for i in range(1, 121):
            external_ref = f"DEMO-CUST-{i:03d}"

            # Customer
            cur.execute(
                """
                INSERT INTO customers
                    (external_ref, full_name, email, phone, city)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (external_ref)
                DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    city = EXCLUDED.city
                RETURNING customer_id;
                """,
                (
                    external_ref,
                    f"Demo Customer {i:03d}",
                    f"customer{i:03d}@claimlens.demo",
                    f"+91990000{i:04d}",
                    "Chennai",
                ),
            )

            customer_id = cur.fetchone()[0]

            product_id = POLICY_PRODUCTS[(i - 1) % len(POLICY_PRODUCTS)][0]

            inception = date(2025, 1, 1) + timedelta(days=(i - 1) % 30)
            expiry = date(2026, 12, 31)

            policy_number = f"CL-POL-{i:04d}"

            # Policy
            cur.execute(
                """
                INSERT INTO policies
                    (
                        policy_number,
                        product_id,
                        customer_id,
                        inception_date,
                        expiry_date,
                        status
                    )
                VALUES (%s, %s, %s, %s, %s, 'active')
                ON CONFLICT (policy_number)
                DO UPDATE SET
                    product_id = EXCLUDED.product_id,
                    customer_id = EXCLUDED.customer_id,
                    inception_date = EXCLUDED.inception_date,
                    expiry_date = EXCLUDED.expiry_date,
                    status = EXCLUDED.status
                RETURNING policy_id;
                """,
                (
                    policy_number,
                    product_id,
                    customer_id,
                    inception,
                    expiry,
                ),
            )

            policy_id = cur.fetchone()[0]

            # Policy version
            cur.execute(
                """
                INSERT INTO policy_versions
                    (
                        policy_id,
                        version_no,
                        effective_from,
                        effective_to,
                        endorsement_reason
                    )
                VALUES (%s, 1, %s, %s, %s)
                ON CONFLICT (policy_id, version_no)
                DO UPDATE SET
                    effective_from = EXCLUDED.effective_from,
                    effective_to = EXCLUDED.effective_to,
                    endorsement_reason = EXCLUDED.endorsement_reason
                RETURNING version_id;
                """,
                (
                    policy_id,
                    inception,
                    expiry,
                    "Initial policy issuance",
                ),
            )

            version_id = cur.fetchone()[0]

            # Coverage
            cur.execute(
                """
                INSERT INTO coverages
                    (
                        version_id,
                        peril,
                        sum_insured,
                        sub_limit,
                        deductible,
                        coinsurance_pct
                    )
                VALUES
                    (%s, 'general', 500000, NULL, %s, 0)
                ON CONFLICT (version_id, peril)
                DO UPDATE SET
                    sum_insured = EXCLUDED.sum_insured,
                    deductible = EXCLUDED.deductible;
                """,
                (
                    version_id,
                    POLICY_PRODUCTS[(i - 1) % len(POLICY_PRODUCTS)][3],
                ),
            )

    print("Seeded 120 policies with versions and coverages")

FRAUD_INDICATORS = [
    ("DUPLICATE_DOCUMENT", 1, "Same document checksum appears across claims", 20),
    ("EXCESSIVE_CLAIM_AMOUNT", 1, "Claimed amount is unusually high for the policy", 15),
    ("RECENT_POLICY_INCEPTION", 1, "Loss occurs shortly after policy inception", 15),
    ("LATE_REPORTING", 1, "Claim was reported significantly after the loss date", 10),
    ("MULTIPLE_CLAIMS", 1, "Customer has multiple recent claims", 15),
    ("POLICY_LAPSE", 1, "Policy status indicates a lapse around the loss", 10),
    ("DOCUMENT_MISMATCH", 1, "Extracted document fields conflict with policy data", 10),
    ("SUSPICIOUS_INVOICE", 1, "Invoice contains suspicious or inconsistent information", 15),
]


def seed_fraud_indicators(conn):
    with conn.cursor() as cur:
        for code, version, description, weight in FRAUD_INDICATORS:
            cur.execute(
                """
                INSERT INTO fraud_indicators
                    (
                        indicator_code,
                        version,
                        description,
                        weight,
                        params,
                        is_active
                    )
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (indicator_code, version)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    weight = EXCLUDED.weight,
                    params = EXCLUDED.params,
                    is_active = EXCLUDED.is_active;
                """,
                (
                    code,
                    version,
                    description,
                    weight,
                    "{}",
                ),
            )

    print(f"Seeded {len(FRAUD_INDICATORS)} fraud indicators")


def main():
    with psycopg.connect(DB_URL) as conn:
        seed_policy_products(conn)
        seed_policies(conn)
        seed_claims(conn)
        seed_fraud_indicators(conn)
        conn.commit()

    print("M1 policy and claim seeding completed successfully") 


if __name__ == "__main__":
    main()