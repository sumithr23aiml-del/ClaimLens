import sys

sys.path.append("libs/carvision/src")

from carvision.quality import check_image_quality


def check_images_quality(image_paths: list[str]) -> dict:
    if not image_paths:
        return {
            "passed": False,
            "reason": "No images provided",
            "images": [],
        }

    results = []

    for image_path in image_paths:
        result = check_image_quality(image_path)

        results.append({
            "image_path": image_path,
            **result,
        })

    passed = all(result["passed"] for result in results)

    return {
        "passed": passed,
        "reason": (
            "All images passed quality checks"
            if passed
            else "One or more images failed quality checks"
        ),
        "images": results,
    }