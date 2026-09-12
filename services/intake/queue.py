import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL)


def enqueue_assessment_job(claim_id: int, uploaded_images: list):
    """Enqueues an assessment job in Redis for future processing."""
    payload = {
        "job_type": "assessment",
        "claim_id": claim_id,
        "images": uploaded_images,
        "status": "queued",
    }
    
    # Push the job to the right side of the list (queue)
    redis_client.rpush("assessment_jobs", json.dumps(payload))
    return True
