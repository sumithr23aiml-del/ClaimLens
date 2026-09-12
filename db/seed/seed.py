import csv
import json
import os

import psycopg


DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://claimlens:claimlens@localhost:5432/claimlens",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

PARTS_FILE = os.path.join(BASE_DIR, "data", "catalog", "parts.csv")
LABOR_FILE = os.path.join(BASE_DIR, "data", "catalog", "labor.csv")


def seed_parts(conn):
    with open(PARTS_FILE, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO catalog_parts
                    (part, vehicle_segment, price)
                VALUES (%s, %s, %s)
                ON CONFLICT (part, vehicle_segment)
                DO UPDATE SET price = EXCLUDED.price;
                """,
                (
                    row["part"],
                    row["vehicle_segment"],
                    row["price"],
                ),
            )

    print(f"Seeded {len(rows)} parts")


def seed_labor(conn):
    with open(LABOR_FILE, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO catalog_labor
                    (operation, labor_rate_per_hour)
                VALUES (%s, %s)
                ON CONFLICT (operation)
                DO UPDATE SET
                    labor_rate_per_hour = EXCLUDED.labor_rate_per_hour;
                """,
                (
                    row["operation"],
                    row["labor_rate_per_hour"],
                ),
            )

    print(f"Seeded {len(rows)} labor operations")


def seed_policies(conn):
    policy = {
        "id": "POL001",
        "holder_name_enc": "DEVELOPMENT_USER",
        "vehicle": {"make": "Toyota", "model": "Camry", "year": 2020, "segment": "sedan"},
        "coverage": {"comprehensive": True, "collision": True},
        "deductible": 500.00,
        "valid_from": "2024-01-01",
        "valid_to": "2025-01-01",
    }
    
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policies
                (id, holder_name_enc, vehicle, coverage, deductible, valid_from, valid_to)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                vehicle = EXCLUDED.vehicle,
                coverage = EXCLUDED.coverage,
                deductible = EXCLUDED.deductible,
                valid_from = EXCLUDED.valid_from,
                valid_to = EXCLUDED.valid_to;
            """,
            (
                policy["id"],
                policy["holder_name_enc"],
                json.dumps(policy["vehicle"]),
                json.dumps(policy["coverage"]),
                policy["deductible"],
                policy["valid_from"],
                policy["valid_to"],
            ),
        )

    print("Seeded development policy POL001")


def main():
    with psycopg.connect(DB_URL) as conn:
        seed_policies(conn)
        seed_parts(conn)
        seed_labor(conn)
        conn.commit()

    print("Catalog seeding completed successfully")


if __name__ == "__main__":
    main()