import json
from fastapi import APIRouter, HTTPException
from psycopg.rows import dict_row

from .exif import extract_exif
from .schemas import ClaimCreate
from .checklist import get_checklist
from .quality_gate import check_images_quality
from .storage import upload_image
from .database import get_connection

router = APIRouter()


@router.get("/checklist")
def checklist():
    return {"checklist": get_checklist()}


@router.post("/claims")
def create_claim(claim: ClaimCreate):
    # Step 1: Quality Gate
    image_paths = [img.path for img in claim.images]
    quality = check_images_quality(image_paths)

    if not quality["passed"]:
        return {
            "claim": claim,
            "quality_gate": quality,
            "uploaded_images": [],
        }

    import os
    import logging
    
    logger = logging.getLogger(__name__)

    # Step 2: Policy Lookup & Claim Persistence
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Lookup Policy
                cur.execute("SELECT * FROM policies WHERE id = %s;", (claim.policy_id,))
                policy = cur.fetchone()

                if not policy:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Policy {claim.policy_id} not found"
                    )

                # Create Frozen Snapshot
                policy_snapshot = {
                    "coverage": policy["coverage"],
                    "deductible": float(policy["deductible"]),
                    "vehicle": policy["vehicle"],
                    "valid_from": policy["valid_from"].isoformat() if policy["valid_from"] else None,
                    "valid_to": policy["valid_to"].isoformat() if policy["valid_to"] else None,
                }

                # Persist Claim
                cur.execute(
                    """
                    INSERT INTO claims (policy_id, incident, policy_snapshot, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        claim.policy_id,
                        json.dumps({"description": claim.description}),
                        json.dumps(policy_snapshot),
                        "received",
                    )
                )
                claim_id = cur.fetchone()["id"]
            
            conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during claim persistence: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist claim in database")

    # Step 3: Image Upload, EXIF Stripping, & Persistence
    uploaded_images = []
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for index, image_input in enumerate(claim.images):
                    image_path = image_input.path
                    filename = image_path.split('/')[-1]
                    
                    # 3a. Upload Original
                    original_object_name = f"claims/{claim.policy_id}/{claim_id}/original_{filename}"
                    upload_image(image_path, original_object_name)
                    
                    # 3b. Extract EXIF from original
                    exif_data = extract_exif(image_path)
                    
                    # 3c. Create EXIF-stripped derivative
                    scratch_dir = os.path.join(os.path.dirname(image_path), "scratch")
                    os.makedirs(scratch_dir, exist_ok=True)
                    derivative_local_path = os.path.join(scratch_dir, f"clean_{filename}")
                    
                    from .exif import strip_exif
                    strip_exif(image_path, derivative_local_path)
                    
                    # 3d. Upload Derivative
                    derivative_object_name = f"claims/{claim.policy_id}/{claim_id}/clean_{filename}"
                    derivative_uri = upload_image(derivative_local_path, derivative_object_name)
                    
                    # Clean up local scratch file
                    os.remove(derivative_local_path)
                    
                    # Retrieve quality score for this specific image from our earlier quality gate check
                    img_quality_result = next((item for item in quality.get("images", []) if item["image_path"] == image_path), None)
                    quality_score = img_quality_result["blur"]["score"] if img_quality_result and "blur" in img_quality_result else 0.0

                    # 3e. Persist image metadata to Database
                    cur.execute(
                        """
                        INSERT INTO claim_images 
                        (claim_id, uri, checklist_slot, exif, quality)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            claim_id,
                            derivative_uri,
                            image_input.slot,
                            json.dumps(exif_data),
                            quality_score
                        )
                    )

                    uploaded_images.append({
                        "original_uri": f"s3://claimlens/{original_object_name}",
                        "derivative_uri": derivative_uri,
                        "exif": exif_data,
                    })
            
            conn.commit()
    except Exception as e:
        logger.error(f"Storage or Image Processing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process and store images")

    # Step 4: Enqueue Assessment Job
    try:
        from .queue import enqueue_assessment_job
        enqueue_assessment_job(claim_id, uploaded_images)
    except Exception as e:
        logger.error(f"Redis Queue error: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue assessment job")

    return {
        "claim_id": claim_id,
        "policy_id": claim.policy_id,
        "status": "received",
        "quality_gate": quality,
        "uploaded_images": uploaded_images,
    }
