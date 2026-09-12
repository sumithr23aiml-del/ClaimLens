import os
from minio import Minio


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "claimlens")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "claimlens123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "claimlens")


client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


def ensure_bucket():
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)


def upload_image(image_path: str, object_name: str) -> str:
    ensure_bucket()

    client.fput_object(
        MINIO_BUCKET,
        object_name,
        image_path,
    )

    return f"s3://{MINIO_BUCKET}/{object_name}"