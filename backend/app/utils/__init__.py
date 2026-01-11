"""
Utility modules for SlabHub backend.

This package provides various utility functions for image processing,
validation, duplicate detection, QR code generation, and label printing.
"""

# Image hashing utilities
from .image_hash import (
    calculate_difference_hash,
    calculate_perceptual_hash,
    compare_hashes,
    find_duplicates,
    is_duplicate,
)

# Image validation utilities
from .image_validator import (
    ImageValidationResult,
    get_image_info,
    validate_image,
)

# QR code generation utilities
from .qr_generator import (
    generate_qr_code,
    generate_short_id,
)

# Label printing utilities
from .label_printer import (
    generate_label_pdf,
    generate_batch_labels,
)

__all__ = [
    # Image hashing
    "calculate_perceptual_hash",
    "calculate_difference_hash",
    "compare_hashes",
    "is_duplicate",
    "find_duplicates",
    # Image validation
    "ImageValidationResult",
    "validate_image",
    "get_image_info",
    # QR code generation
    "generate_qr_code",
    "generate_short_id",
    # Label printing
    "generate_label_pdf",
    "generate_batch_labels",
]
