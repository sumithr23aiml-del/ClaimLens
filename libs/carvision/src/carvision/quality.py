import cv2


def check_blur(image_path: str, threshold: float = 100.0) -> dict:
    image = cv2.imread(image_path)

    if image is None:
        return {
            "passed": False,
            "score": 0.0,
            "reason": "Unable to read image",
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()

    return {
        "passed": bool(score >= threshold),
        "score": round(float(score), 2),
        "reason": (
            "Image is sharp"
            if score >= threshold
            else "Image is too blurry"
        ),
    }


def check_exposure(image_path: str) -> dict:
    image = cv2.imread(image_path)

    if image is None:
        return {
            "passed": False,
            "score": 0.0,
            "reason": "Unable to read image",
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(gray.mean())

    passed = 40 <= mean_brightness <= 220

    return {
        "passed": bool(passed),
        "score": round(mean_brightness, 2),
        "reason": (
            "Exposure is acceptable"
            if passed
            else "Image is too dark or too bright"
        ),
    }


def check_distance(image_path: str) -> dict:
    image = cv2.imread(image_path)

    if image is None:
        return {
            "passed": False,
            "score": 0.0,
            "reason": "Unable to read image",
        }

    height, width = image.shape[:2]
    # Simple heuristic for M1: Image must be at least 300x300.
    # In M2 this will use YOLO bounding boxes to check vehicle area.
    passed = (height >= 300 and width >= 300)

    return {
        "passed": bool(passed),
        "score": float(height * width),
        "reason": (
            "Distance/framing is acceptable"
            if passed
            else "Image is too small or taken from too far away"
        ),
    }


def check_image_quality(image_path: str) -> dict:
    blur = check_blur(image_path)
    exposure = check_exposure(image_path)
    distance = check_distance(image_path)

    passed = blur["passed"] and exposure["passed"] and distance["passed"]

    reasons = []

    if not blur["passed"]:
        reasons.append(blur["reason"])

    if not exposure["passed"]:
        reasons.append(exposure["reason"])

    if not distance["passed"]:
        reasons.append(distance["reason"])

    return {
        "passed": passed,
        "blur": blur,
        "exposure": exposure,
        "distance": distance,
        "reason": (
            "Image quality accepted"
            if passed
            else "; ".join(reasons)
        ),
    }