import os
import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://claimlens:claimlens@localhost:5432/claimlens",
)


def get_connection():
    return psycopg.connect(DATABASE_URL)