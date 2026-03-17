CLOUDINARY_BASE = "https://res.cloudinary.com/dalaxsevq/image/upload/vinted"

def get_image_url(image_id):
    """Return Cloudinary URL for a catalog image by ID."""
    return f"{CLOUDINARY_BASE}/{image_id}.jpg"
