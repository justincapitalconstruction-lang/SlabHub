"""
QR Code Generator for SlabHub
Generates QR codes for slab public IDs and short ID generation
"""
import logging
import secrets
import string
from pathlib import Path
from typing import Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_L

from backend.app.config import settings

logger = logging.getLogger(__name__)


def generate_short_id(length: int = 8) -> str:
    """
    Generate a URL-safe random ID using base62 (alphanumeric).

    Uses base62 character set (0-9, a-z, A-Z) which is URL-safe
    and provides good readability while maintaining uniqueness.

    Args:
        length: Length of the generated ID (default: 8)

    Returns:
        str: Random alphanumeric string of specified length

    Example:
        >>> generate_short_id(8)
        'aB3x9Km2'
    """
    # Base62 alphabet (URL-safe, no special characters)
    alphabet = string.ascii_letters + string.digits  # a-z, A-Z, 0-9

    # Use secrets module for cryptographically strong randomness
    short_id = ''.join(secrets.choice(alphabet) for _ in range(length))

    logger.debug(f"Generated short ID: {short_id}")
    return short_id


def generate_qr_code(
    public_id: str,
    output_folder: Optional[Path] = None
) -> Path:
    """
    Generate a QR code for a slab's public ID.

    Creates a QR code that encodes the public URL for the slab
    and saves it as a PNG image file.

    Args:
        public_id: The public identifier for the slab
        output_folder: Optional custom output folder. If not provided,
                      uses settings.qr_output_folder

    Returns:
        Path: Path to the saved QR code PNG file

    Raises:
        ValueError: If public_id is empty or None
        IOError: If unable to create output directory or save file

    Example:
        >>> qr_path = generate_qr_code("aB3x9Km2")
        >>> print(qr_path)
        Path("./data/qr/aB3x9Km2.png")
    """
    if not public_id:
        raise ValueError("public_id cannot be empty or None")

    # Determine output folder
    if output_folder is None:
        output_folder = Path(settings.qr_output_folder)
    else:
        output_folder = Path(output_folder)

    # Create output directory if it doesn't exist
    try:
        output_folder.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using QR output folder: {output_folder}")
    except Exception as e:
        logger.error(f"Failed to create QR output directory {output_folder}: {e}")
        raise IOError(f"Cannot create output directory: {e}") from e

    # Construct the public URL
    base_url = settings.public_base_url.rstrip('/')
    qr_url = f"{base_url}/s/{public_id}"
    logger.info(f"Generating QR code for URL: {qr_url}")

    # Create QR code instance with specified configuration
    qr = qrcode.QRCode(
        version=1,  # Size 1 (21x21 modules) - smallest, auto-adjusts if needed
        error_correction=ERROR_CORRECT_L,  # ~7% error correction (lowest)
        box_size=10,  # 10 pixels per module
        border=4,  # 4 modules border (minimum per spec)
    )

    # Add data to QR code
    qr.add_data(qr_url)
    qr.make(fit=True)  # Auto-adjust version if needed

    # Create image with PIL backend
    img = qr.make_image(fill_color="black", back_color="white")

    # Determine output path
    output_path = output_folder / f"{public_id}.png"

    # Save the image
    try:
        img.save(str(output_path))
        logger.info(f"QR code saved successfully: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save QR code to {output_path}: {e}")
        raise IOError(f"Cannot save QR code image: {e}") from e

    return output_path
