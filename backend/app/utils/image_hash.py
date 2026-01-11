"""
Image hashing utilities for duplicate detection and comparison.

This module provides functions for calculating perceptual hashes of images
and comparing them to find duplicates.
"""

import logging
from pathlib import Path
from typing import Optional

import imagehash
from PIL import Image

logger = logging.getLogger(__name__)


def calculate_perceptual_hash(image_path: str | Path, hash_size: int = 8) -> Optional[str]:
    """
    Calculate the average perceptual hash of an image.

    The average hash is resistant to scaling and aspect ratio changes.

    Args:
        image_path: Path to the image file
        hash_size: Size of the hash (default: 8, produces 64-bit hash)

    Returns:
        Hexadecimal string representation of the hash, or None if error occurs

    Example:
        >>> hash_str = calculate_perceptual_hash("photo.jpg")
        >>> print(hash_str)
        'a1b2c3d4e5f67890'
    """
    try:
        image_path = Path(image_path)

        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None

        if not image_path.is_file():
            logger.error(f"Path is not a file: {image_path}")
            return None

        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Calculate average hash
            hash_value = imagehash.average_hash(img, hash_size=hash_size)

            # Convert to hex string
            return str(hash_value)

    except OSError as e:
        logger.error(f"Failed to open image {image_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calculating perceptual hash for {image_path}: {e}")
        return None


def calculate_difference_hash(image_path: str | Path, hash_size: int = 8) -> Optional[str]:
    """
    Calculate the difference hash (dHash) of an image.

    The difference hash is more robust to gamma correction and color histogram adjustments
    compared to average hash.

    Args:
        image_path: Path to the image file
        hash_size: Size of the hash (default: 8, produces 64-bit hash)

    Returns:
        Hexadecimal string representation of the hash, or None if error occurs

    Example:
        >>> hash_str = calculate_difference_hash("photo.jpg")
        >>> print(hash_str)
        'f1e2d3c4b5a69788'
    """
    try:
        image_path = Path(image_path)

        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None

        if not image_path.is_file():
            logger.error(f"Path is not a file: {image_path}")
            return None

        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Calculate difference hash
            hash_value = imagehash.dhash(img, hash_size=hash_size)

            # Convert to hex string
            return str(hash_value)

    except OSError as e:
        logger.error(f"Failed to open image {image_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calculating difference hash for {image_path}: {e}")
        return None


def compare_hashes(hash1: str, hash2: str) -> int:
    """
    Compare two image hashes and return the Hamming distance.

    The Hamming distance is the number of bit positions in which the two hashes differ.
    A distance of 0 means the hashes are identical.

    Args:
        hash1: First hash as hexadecimal string
        hash2: Second hash as hexadecimal string

    Returns:
        Hamming distance between the hashes (0 = identical)
        Returns -1 if hashes are invalid or comparison fails

    Example:
        >>> distance = compare_hashes(hash1, hash2)
        >>> if distance == 0:
        ...     print("Images are identical")
        >>> elif distance < 10:
        ...     print("Images are very similar")
    """
    try:
        if not hash1 or not hash2:
            logger.error("One or both hashes are empty")
            return -1

        # Convert hex strings back to ImageHash objects
        hash_obj1 = imagehash.hex_to_hash(hash1)
        hash_obj2 = imagehash.hex_to_hash(hash2)

        # Calculate Hamming distance
        distance = hash_obj1 - hash_obj2

        return int(distance)

    except ValueError as e:
        logger.error(f"Invalid hash format: {e}")
        return -1
    except Exception as e:
        logger.error(f"Error comparing hashes: {e}")
        return -1


def is_duplicate(hash1: str, hash2: str, threshold: int = 10) -> bool:
    """
    Check if two image hashes represent duplicate or very similar images.

    Args:
        hash1: First hash as hexadecimal string
        hash2: Second hash as hexadecimal string
        threshold: Maximum Hamming distance to consider as duplicate (default: 10)
                  Lower values = stricter matching

    Returns:
        True if images are considered duplicates, False otherwise

    Example:
        >>> if is_duplicate(hash1, hash2, threshold=5):
        ...     print("Images are duplicates")
    """
    try:
        distance = compare_hashes(hash1, hash2)

        if distance == -1:
            return False

        return distance <= threshold

    except Exception as e:
        logger.error(f"Error checking for duplicate: {e}")
        return False


def find_duplicates(
    image_hashes: dict[str, str],
    threshold: int = 10
) -> list[tuple[str, str, int]]:
    """
    Find all duplicate pairs in a set of image hashes.

    Args:
        image_hashes: Dictionary mapping image IDs to their hash strings
        threshold: Maximum Hamming distance to consider as duplicate (default: 10)

    Returns:
        List of tuples (id1, id2, distance) for all duplicate pairs found.
        Pairs are only returned once (no duplicates like (A,B) and (B,A)).

    Example:
        >>> hashes = {
        ...     "img1": "a1b2c3d4",
        ...     "img2": "a1b2c3d5",
        ...     "img3": "ffffffff"
        ... }
        >>> duplicates = find_duplicates(hashes, threshold=5)
        >>> for id1, id2, dist in duplicates:
        ...     print(f"{id1} and {id2} are similar (distance: {dist})")
    """
    duplicates = []

    try:
        if not image_hashes:
            logger.warning("Empty image_hashes dictionary provided")
            return duplicates

        # Convert dict to list of (id, hash) tuples for easier iteration
        items = list(image_hashes.items())

        # Compare each pair only once
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                id1, hash1 = items[i]
                id2, hash2 = items[j]

                distance = compare_hashes(hash1, hash2)

                # Skip invalid comparisons
                if distance == -1:
                    continue

                # Check if within threshold
                if distance <= threshold:
                    duplicates.append((id1, id2, distance))

        # Sort by distance (most similar first)
        duplicates.sort(key=lambda x: x[2])

        logger.info(f"Found {len(duplicates)} duplicate pairs out of {len(items)} images")

        return duplicates

    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        return duplicates
