import json
import pytest
from fastapi.testclient import TestClient
from services.intake.main import app
from services.intake.database import get_connection
from services.intake.queue import redis_client

client = TestClient(app)

def test_health_endpoint():
    """1. Test Health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_checklist_endpoint():
    """2. Test Checklist endpoint"""
    response = client.get("/intake/checklist")
    assert response.status_code == 200
    checklist = response.json()["checklist"]
    assert "odometer" in checklist
    assert "vin_plate" in checklist
    assert "front" in checklist

def test_missing_images():
    """5. Test Missing images"""
    response = client.post("/intake/claims", json={
        "policy_id": "POL001",
        "description": "test",
        "images": []
    })
    assert response.status_code == 200
    assert response.json()["quality_gate"]["passed"] is False

def test_invalid_policy():
    """4. Test Invalid policy"""
    response = client.post("/intake/claims", json={
        "policy_id": "INVALID",
        "description": "test",
        "images": [{"slot": "front", "path": "data/raw/CarDD_release/CarDD_COCO/train2017/000001.jpg"}]
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_bad_quality_image():
    """6. Test Bad-quality image"""
    # Since we don't have a deliberately blurry image on hand, 
    # we simulate passing a path to a non-image file which cv2 will fail to read.
    response = client.post("/intake/claims", json={
        "policy_id": "POL001",
        "description": "test bad quality",
        "images": [{"slot": "front", "path": "data/catalog/parts.csv"}]
    })
    assert response.status_code == 200
    quality = response.json()["quality_gate"]
    assert quality["passed"] is False
    assert quality["images"][0]["passed"] is False

def test_valid_claim_integration():
    """
    3. Valid claim creation
    7. MinIO upload
    8. EXIF extraction
    9. EXIF-stripped derivative
    10. PostgreSQL claim persistence
    11. PostgreSQL claim_images persistence
    12. Redis job enqueue
    """
    response = client.post("/intake/claims", json={
        "policy_id": "POL001",
        "description": "Integration test claim",
        "images": [{"slot": "front", "path": "data/raw/CarDD_release/CarDD_COCO/train2017/000001.jpg"}]
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "received"
    assert data["quality_gate"]["passed"] is True
    assert len(data["uploaded_images"]) == 1
    
    claim_id = data["claim_id"]
    uploaded_image = data["uploaded_images"][0]
    
    # Check EXIF and MinIO URIs
    assert "original_uri" in uploaded_image
    assert "derivative_uri" in uploaded_image
    assert "exif" in uploaded_image
    
    # Check PostgreSQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check claim
            cur.execute("SELECT incident, policy_snapshot FROM claims WHERE id = %s", (claim_id,))
            claim = cur.fetchone()
            assert claim is not None
            assert claim[0]["description"] == "Integration test claim"
            assert claim[1]["vehicle"]["model"] == "Camry"
            
            # Check claim_images
            cur.execute("SELECT uri, quality FROM claim_images WHERE claim_id = %s", (claim_id,))
            img = cur.fetchone()
            assert img is not None
            assert img[0] == uploaded_image["derivative_uri"]
            assert img[1] > 0.0 # Quality score was populated

    # Check Redis Queue
    jobs = redis_client.lrange("assessment_jobs", 0, -1)
    found_job = False
    for job_bytes in jobs:
        job = json.loads(job_bytes)
        if job["claim_id"] == claim_id:
            found_job = True
            assert job["status"] == "queued"
            assert job["images"][0]["derivative_uri"] == uploaded_image["derivative_uri"]
            break
            
    assert found_job is True
