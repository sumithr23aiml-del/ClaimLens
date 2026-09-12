from PIL import Image
from PIL.ExifTags import TAGS


def extract_exif(image_path: str) -> dict:
    image = Image.open(image_path)
    exif_data = image.getexif()

    raw_exif = {}
    if exif_data:
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            raw_exif[tag_name] = str(value)

    return {
        "device": raw_exif.get("Model", raw_exif.get("Make")),
        "timestamp": raw_exif.get("DateTime", raw_exif.get("DateTimeOriginal")),
        "gps": None,
        "raw": raw_exif
    }


def strip_exif(input_path: str, output_path: str) -> str:
    """Creates a derivative image with all EXIF metadata stripped."""
    with Image.open(input_path) as img:
        # Pillow's default save behavior strips EXIF 
        # unless explicitly passed via the `exif=` argument.
        
        # We ensure it's in a standard RGB mode for saving to JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.save(output_path, "JPEG", quality=95)
    
    return output_path