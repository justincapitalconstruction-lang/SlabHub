"""
Label Printer for SlabHub
Generates PDF labels for PM-241BT thermal printer (4x6 inch labels)
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from backend.app.config import settings
from backend.app.utils.qr_generator import generate_qr_code

logger = logging.getLogger(__name__)


def _parse_label_size(label_size: str) -> tuple[float, float]:
    """
    Parse label size string to width and height in inches.

    Args:
        label_size: Label size in format "WxH" (e.g., "4x6")

    Returns:
        tuple: (width, height) in inches

    Raises:
        ValueError: If label_size format is invalid
    """
    try:
        width_str, height_str = label_size.lower().split('x')
        width = float(width_str.strip())
        height = float(height_str.strip())
        return width, height
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Invalid label_size format: '{label_size}'. Expected format: 'WxH' (e.g., '4x6')"
        ) from e


def generate_label_pdf(slab, output_path: Optional[Path] = None) -> Path:
    """
    Generate a 4x6 inch PDF label for a slab.

    Creates a professional-looking label with QR code, slab details,
    and formatted layout optimized for PM-241BT thermal printer.

    Layout:
        - QR code: 2x2 inches, top-left corner
        - Slab name: Large bold text, top-right
        - Stone type, finish, supplier: Medium text below name
        - Dimensions: L x W x Thickness (if available)
        - Location: Physical location (if available)
        - Public ID: Small text at bottom for reference

    Args:
        slab: Slab model instance with attributes (name, stone_type, etc.)
        output_path: Optional custom output path. If not provided,
                    uses settings.label_output_folder

    Returns:
        Path: Path to the generated PDF file

    Raises:
        ValueError: If slab is None or missing required fields
        IOError: If unable to create output directory or save file

    Example:
        >>> from backend.app.models import Slab
        >>> slab = Slab(public_id="aB3x9Km2", name="Calacatta Gold")
        >>> pdf_path = generate_label_pdf(slab)
        >>> print(pdf_path)
        Path("./data/labels/aB3x9Km2.pdf")
    """
    if slab is None:
        raise ValueError("slab cannot be None")

    if not hasattr(slab, 'public_id') or not slab.public_id:
        raise ValueError("slab must have a valid public_id")

    # Determine output path
    if output_path is None:
        output_folder = Path(settings.label_output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / f"{slab.public_id}.pdf"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating label PDF for slab: {slab.public_id}")

    # Parse label dimensions
    label_width, label_height = _parse_label_size(settings.label_size)
    page_width = label_width * inch
    page_height = label_height * inch

    # Create PDF canvas
    c = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))

    # Generate QR code
    try:
        qr_path = generate_qr_code(slab.public_id)
        logger.debug(f"Generated QR code at: {qr_path}")
    except Exception as e:
        logger.error(f"Failed to generate QR code for {slab.public_id}: {e}")
        raise

    # Define layout constants (in inches, converted to points)
    margin = 0.25 * inch
    qr_size = 2.0 * inch
    text_start_x = margin + qr_size + 0.2 * inch  # Text starts after QR + spacing

    # Draw QR code (top-left corner with margin)
    try:
        c.drawImage(
            str(qr_path),
            margin,  # x position
            page_height - margin - qr_size,  # y position (from top)
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True
        )
    except Exception as e:
        logger.error(f"Failed to draw QR code image: {e}")
        raise IOError(f"Cannot draw QR code image: {e}") from e

    # Current y position for text (starting from top)
    y_pos = page_height - margin

    # Draw slab name (large, bold)
    c.setFont("Helvetica-Bold", 18)
    slab_name = getattr(slab, 'name', 'N/A')
    if slab_name and len(slab_name) > 20:
        # Split long names into two lines
        c.drawString(text_start_x, y_pos, slab_name[:20])
        y_pos -= 20
        c.drawString(text_start_x, y_pos, slab_name[20:40])
        y_pos -= 25
    else:
        c.drawString(text_start_x, y_pos, slab_name or 'N/A')
        y_pos -= 25

    # Draw stone type
    c.setFont("Helvetica-Bold", 12)
    stone_type = getattr(slab, 'stone_type', None)
    if stone_type:
        c.drawString(text_start_x, y_pos, f"Type: {stone_type}")
        y_pos -= 18

    # Draw finish
    c.setFont("Helvetica", 11)
    finish = getattr(slab, 'finish', None)
    if finish:
        c.drawString(text_start_x, y_pos, f"Finish: {finish}")
        y_pos -= 16

    # Draw supplier
    supplier = getattr(slab, 'supplier', None)
    if supplier:
        c.drawString(text_start_x, y_pos, f"Supplier: {supplier}")
        y_pos -= 16

    # Draw dimensions if available
    length = getattr(slab, 'length', None)
    width = getattr(slab, 'width', None)
    thickness = getattr(slab, 'thickness', None)

    if length or width or thickness:
        y_pos -= 8  # Extra spacing before dimensions
        c.setFont("Helvetica-Bold", 11)

        dim_parts = []
        if length:
            dim_parts.append(f"L: {length:.1f}\"")
        if width:
            dim_parts.append(f"W: {width:.1f}\"")
        if thickness:
            dim_parts.append(f"T: {thickness:.2f}\"")

        dimensions_text = " x ".join(dim_parts)
        c.drawString(text_start_x, y_pos, f"Dimensions: {dimensions_text}")
        y_pos -= 18

    # Draw square footage if available
    square_feet = getattr(slab, 'square_feet', None)
    if square_feet:
        c.setFont("Helvetica", 10)
        c.drawString(text_start_x, y_pos, f"Area: {square_feet:.2f} sq ft")
        y_pos -= 16

    # Draw location if available
    location = getattr(slab, 'location', None)
    if location:
        y_pos -= 8  # Extra spacing
        c.setFont("Helvetica-Bold", 12)
        c.drawString(text_start_x, y_pos, f"Location: {location}")
        y_pos -= 18

    # Draw public ID at bottom for reference
    c.setFont("Helvetica", 8)
    c.drawString(margin, margin, f"ID: {slab.public_id}")

    # Draw generated date/time at bottom right
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.drawRightString(page_width - margin, margin, timestamp)

    # Save PDF
    try:
        c.save()
        logger.info(f"Label PDF saved successfully: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save PDF to {output_path}: {e}")
        raise IOError(f"Cannot save PDF file: {e}") from e

    return output_path


def generate_batch_labels(slabs: List, output_folder: Path) -> Path:
    """
    Generate a multi-page PDF with labels for multiple slabs.

    Creates a single PDF file with one label per page, suitable for
    batch printing on PM-241BT thermal printer.

    Args:
        slabs: List of Slab model instances
        output_folder: Folder to save the batch PDF

    Returns:
        Path: Path to the generated batch PDF file

    Raises:
        ValueError: If slabs list is empty or None
        IOError: If unable to create output directory or save file

    Example:
        >>> from backend.app.models import Slab
        >>> slabs = [slab1, slab2, slab3]
        >>> pdf_path = generate_batch_labels(slabs, Path("./labels"))
        >>> print(pdf_path)
        Path("./labels/labels_batch_20260110_143052.pdf")
    """
    if not slabs:
        raise ValueError("slabs list cannot be empty or None")

    # Create output folder if it doesn't exist
    output_folder = Path(output_folder)
    try:
        output_folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output folder {output_folder}: {e}")
        raise IOError(f"Cannot create output directory: {e}") from e

    # Generate batch filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_folder / f"labels_batch_{timestamp}.pdf"

    logger.info(f"Generating batch labels for {len(slabs)} slabs")

    # Parse label dimensions
    label_width, label_height = _parse_label_size(settings.label_size)
    page_width = label_width * inch
    page_height = label_height * inch

    # Create PDF canvas
    c = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))

    # Generate label for each slab
    for idx, slab in enumerate(slabs, start=1):
        logger.debug(f"Processing slab {idx}/{len(slabs)}: {slab.public_id}")

        try:
            # Generate QR code for this slab
            qr_path = generate_qr_code(slab.public_id)

            # Define layout constants
            margin = 0.25 * inch
            qr_size = 2.0 * inch
            text_start_x = margin + qr_size + 0.2 * inch

            # Draw QR code
            c.drawImage(
                str(qr_path),
                margin,
                page_height - margin - qr_size,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True
            )

            # Current y position for text
            y_pos = page_height - margin

            # Draw slab name
            c.setFont("Helvetica-Bold", 18)
            slab_name = getattr(slab, 'name', 'N/A')
            if slab_name and len(slab_name) > 20:
                c.drawString(text_start_x, y_pos, slab_name[:20])
                y_pos -= 20
                c.drawString(text_start_x, y_pos, slab_name[20:40])
                y_pos -= 25
            else:
                c.drawString(text_start_x, y_pos, slab_name or 'N/A')
                y_pos -= 25

            # Draw stone type
            c.setFont("Helvetica-Bold", 12)
            stone_type = getattr(slab, 'stone_type', None)
            if stone_type:
                c.drawString(text_start_x, y_pos, f"Type: {stone_type}")
                y_pos -= 18

            # Draw finish
            c.setFont("Helvetica", 11)
            finish = getattr(slab, 'finish', None)
            if finish:
                c.drawString(text_start_x, y_pos, f"Finish: {finish}")
                y_pos -= 16

            # Draw supplier
            supplier = getattr(slab, 'supplier', None)
            if supplier:
                c.drawString(text_start_x, y_pos, f"Supplier: {supplier}")
                y_pos -= 16

            # Draw dimensions
            length = getattr(slab, 'length', None)
            width = getattr(slab, 'width', None)
            thickness = getattr(slab, 'thickness', None)

            if length or width or thickness:
                y_pos -= 8
                c.setFont("Helvetica-Bold", 11)
                dim_parts = []
                if length:
                    dim_parts.append(f"L: {length:.1f}\"")
                if width:
                    dim_parts.append(f"W: {width:.1f}\"")
                if thickness:
                    dim_parts.append(f"T: {thickness:.2f}\"")
                dimensions_text = " x ".join(dim_parts)
                c.drawString(text_start_x, y_pos, f"Dimensions: {dimensions_text}")
                y_pos -= 18

            # Draw square footage
            square_feet = getattr(slab, 'square_feet', None)
            if square_feet:
                c.setFont("Helvetica", 10)
                c.drawString(text_start_x, y_pos, f"Area: {square_feet:.2f} sq ft")
                y_pos -= 16

            # Draw location
            location = getattr(slab, 'location', None)
            if location:
                y_pos -= 8
                c.setFont("Helvetica-Bold", 12)
                c.drawString(text_start_x, y_pos, f"Location: {location}")
                y_pos -= 18

            # Draw public ID at bottom
            c.setFont("Helvetica", 8)
            c.drawString(margin, margin, f"ID: {slab.public_id}")

            # Draw page number and timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.drawRightString(page_width - margin, margin, f"{idx}/{len(slabs)} - {timestamp}")

            # Add new page for next slab (except for last one)
            if idx < len(slabs):
                c.showPage()

        except Exception as e:
            logger.error(f"Error generating label for slab {slab.public_id}: {e}")
            # Continue with next slab instead of failing entire batch
            if idx < len(slabs):
                c.showPage()
            continue

    # Save the PDF
    try:
        c.save()
        logger.info(f"Batch labels PDF saved successfully: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save batch PDF to {output_path}: {e}")
        raise IOError(f"Cannot save batch PDF file: {e}") from e

    return output_path
