"""
Image validation utilities for SlabHub.

This module provides functions for validating images, checking for corruption,
blank images, and retrieving image information.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class ImageValidationResult:
    """
    Result of image validation.

    Attributes:
        valid: Whether the image passed validation
        reason: Explanation if validation failed, None if valid
    """
    valid: bool
    reason: Optional[str] = None

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.valid


def validate_image(
    image_path: str | Path,
    min_width: int = 800,
    min_height: int = 800,
    max_size_mb: int = 10,
    check_corruption: bool = True
) -> ImageValidationResult:
    """
    Validate an image file against multiple criteria.

    Checks:
    - File exists and is readable
    - File size is within limits
    - Image dimensions meet minimum requirements
    - Image is not blank (all black or all white)
    - Image is not corrupted (if check_corruption=True)

    Args:
        image_path: Path to the image file
        min_width: Minimum width in pixels (default: 800)
        min_height: Minimum height in pixels (default: 800)
        max_size_mb: Maximum file size in megabytes (default: 10)
        check_corruption: Whether to verify image can be loaded (default: True)

    Returns:
        ImageValidationResult with validation status and failure reason if any

    Example:
        >>> result = validate_image("photo.jpg", min_width=1024, min_height=768)
        >>> if result.valid:
        ...     print("Image is valid")
        >>> else:
        ...     print(f"Invalid: {result.reason}")
    """
    try:
        image_path = Path(image_path)

        # Check if file exists
        if not image_path.exists():
            return ImageValidationResult(
                valid=False,
                reason=f"File does not exist: {image_path}"
            )

        # Check if path is a file
        if not image_path.is_file():
            return ImageValidationResult(
                valid=False,
                reason=f"Path is not a file: {image_path}"
            )

        # Check file size
        file_size_bytes = image_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        if file_size_mb > max_size_mb:
            return ImageValidationResult(
                valid=False,
                reason=f"File size ({file_size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)"
            )

        # Check if file size is suspiciously small (likely corrupted)
        if file_size_bytes < 100:  # Less than 100 bytes
            return ImageValidationResult(
                valid=False,
                reason=f"File size too small ({file_size_bytes} bytes), likely corrupted"
            )

        # Try to open and validate the image
        try:
            with Image.open(image_path) as img:
                # Verify image can be loaded (detects corruption)
                if check_corruption:
                    try:
                        img.verify()
                    except Exception as e:
                        return ImageValidationResult(
                            valid=False,
                            reason=f"Image is corrupted: {e}"
                        )

                    # Re-open after verify (verify closes the file)
                    img = Image.open(image_path)

                # Check dimensions
                width, height = img.size

                if width < min_width or height < min_height:
                    return ImageValidationResult(
                        valid=False,
                        reason=f"Image dimensions ({width}x{height}) below minimum ({min_width}x{min_height})"
                    )

                # Check if image is blank
                if _is_blank_image(img):
                    return ImageValidationResult(
                        valid=False,
                        reason="Image is blank (all black or all white)"
                    )

                # All checks passed
                logger.info(f"Image validation passed: {image_path}")
                return ImageValidationResult(valid=True)

        except OSError as e:
            return ImageValidationResult(
                valid=False,
                reason=f"Cannot open image file: {e}"
            )
        except Exception as e:
            return ImageValidationResult(
                valid=False,
                reason=f"Image validation error: {e}"
            )

    except Exception as e:
        logger.error(f"Unexpected error validating image {image_path}: {e}")
        return ImageValidationResult(
            valid=False,
            reason=f"Validation failed: {e}"
        )


def _is_blank_image(img: Image.Image, threshold: float = 0.95) -> bool:
    """
    Check if an image is blank (all black or all white).

    An image is considered blank if more than threshold% of pixels
    are either very dark or very bright.

    Args:
        img: PIL Image object
        threshold: Percentage of uniform pixels to consider blank (0.0-1.0)

    Returns:
        True if image is blank, False otherwise

    Note:
        This is an internal helper function.
    """
    try:
        # Convert image to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Convert to numpy array for faster processing
        img_array = np.array(img)

        # Calculate mean pixel value across all channels
        # Values range from 0 (black) to 255 (white)
        mean_values = np.mean(img_array, axis=2)

        # Count very dark pixels (near black)
        dark_pixels = np.sum(mean_values < 10)

        # Count very bright pixels (near white)
        bright_pixels = np.sum(mean_values > 245)

        # Total pixels
        total_pixels = mean_values.size

        # Calculate percentage of uniform pixels
        uniform_ratio = (dark_pixels + bright_pixels) / total_pixels

        is_blank = uniform_ratio >= threshold

        if is_blank:
            logger.warning(
                f"Image appears blank: {uniform_ratio*100:.1f}% uniform pixels "
                f"({dark_pixels} dark, {bright_pixels} bright)"
            )

        return is_blank

    except Exception as e:
        logger.error(f"Error checking if image is blank: {e}")
        # If we can't determine, assume it's not blank to be safe
        return False


def get_image_info(image_path: str | Path) -> Optional[dict]:
    """
    Retrieve detailed information about an image file.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary with image information:
        {
            'width': int,           # Width in pixels
            'height': int,          # Height in pixels
            'format': str,          # Image format (JPEG, PNG, etc.)
            'mode': str,            # Color mode (RGB, RGBA, L, etc.)
            'file_size_mb': float,  # File size in megabytes
            'file_size_bytes': int  # File size in bytes
        }
        Returns None if error occurs

    Example:
        >>> info = get_image_info("photo.jpg")
        >>> if info:
        ...     print(f"Image: {info['width']}x{info['height']}, {info['format']}")
        ...     print(f"Size: {info['file_size_mb']:.2f}MB")
    """
    try:
        image_path = Path(image_path)

        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None

        if not image_path.is_file():
            logger.error(f"Path is not a file: {image_path}")
            return None

        # Get file size
        file_size_bytes = image_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Open image and get info
        with Image.open(image_path) as img:
            info = {
                'width': img.width,
                'height': img.height,
                'format': img.format or 'Unknown',
                'mode': img.mode,
                'file_size_mb': round(file_size_mb, 2),
                'file_size_bytes': file_size_bytes
            }

            logger.debug(
                f"Image info for {image_path.name}: "
                f"{info['width']}x{info['height']}, "
                f"{info['format']}, {info['mode']}, "
                f"{info['file_size_mb']}MB"
            )

            return info

    except OSError as e:
        logger.error(f"Failed to open image {image_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting image info for {image_path}: {e}")
        return None
