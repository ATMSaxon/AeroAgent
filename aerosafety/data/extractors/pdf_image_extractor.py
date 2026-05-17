"""
PDF-to-image extraction utilities for multimodal TaskCard attachments.

Requires the `aerosafety[multimodal]` extra:
    pip install aerosafety[multimodal]

Per CLAUDE.md §8.1: ImportError is raised explicitly — no silent fallback.
Provenance metadata (source PDF, page, bbox, timestamp) is embedded in
PNG metadata for auditability (CLAUDE.md §5.1, §5.2).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Tuple

# Raise an explicit, actionable ImportError if optional deps are missing.
# Do NOT silently catch or replace with stubs (CLAUDE.md §1.2, §8.1).
try:
    from pdf2image import convert_from_path  # type: ignore[import-untyped]
except ImportError as _e:
    raise ImportError(
        "pdf2image is required for PDF extraction. "
        "Install the multimodal extras: pip install 'aerosafety[multimodal]'"
    ) from _e

try:
    from PIL import Image, PngImagePlugin  # type: ignore[import-untyped]
except ImportError as _e:
    raise ImportError(
        "Pillow is required for PDF extraction. "
        "Install the multimodal extras: pip install 'aerosafety[multimodal]'"
    ) from _e

# Bbox type: (x0_pt, y0_pt, x1_pt, y1_pt) in PDF point coordinates (72 pt/inch)
BboxPt = Tuple[float, float, float, float]


def _build_png_metadata(
    pdf_path: Path,
    page_num: int,
    dpi: int,
    bbox_pt: BboxPt | None,
) -> PngImagePlugin.PngInfo:
    """Return a PngInfo block with provenance embedded in PNG tEXt chunks."""
    info = PngImagePlugin.PngInfo()
    info.add_text("source_pdf", str(pdf_path.resolve()))
    info.add_text("page_num", str(page_num))
    info.add_text("dpi", str(dpi))
    if bbox_pt is not None:
        info.add_text("bbox_pt", f"{bbox_pt[0]},{bbox_pt[1]},{bbox_pt[2]},{bbox_pt[3]}")
    info.add_text(
        "extraction_timestamp",
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    return info


def extract_page_image(
    pdf_path: Path | str,
    page_num: int,
    output_path: Path | str,
    dpi: int = 200,
) -> Path:
    """
    Render a single PDF page to a PNG file.

    Args:
        pdf_path:    Path to the source PDF.
        page_num:    1-based page index (matches PDF viewer conventions).
        output_path: Destination PNG path (created or overwritten).
        dpi:         Render resolution. Default 200 is adequate for airport diagrams.

    Returns:
        Resolved output_path.

    Raises:
        FileNotFoundError: if pdf_path does not exist.
        ValueError: if page_num < 1.
    """
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if page_num < 1:
        raise ValueError(f"page_num must be >= 1, got {page_num}")

    pages = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=page_num,
        last_page=page_num,
    )
    if not pages:
        raise ValueError(f"No page rendered for page_num={page_num} in {pdf_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    png_info = _build_png_metadata(pdf_path, page_num, dpi, bbox_pt=None)
    pages[0].save(str(output_path), format="PNG", pnginfo=png_info)
    return output_path.resolve()


def extract_region(
    pdf_path: Path | str,
    page_num: int,
    bbox_pt: BboxPt,
    output_path: Path | str,
    dpi: int = 200,
) -> Path:
    """
    Render a rectangular region of a PDF page to a PNG file.

    Args:
        pdf_path:    Path to the source PDF.
        page_num:    1-based page index.
        bbox_pt:     Region in PDF point coordinates (x0, y0, x1, y1).
                     Origin is bottom-left (PDF convention); 72 pt == 1 inch.
        output_path: Destination PNG path (created or overwritten).
        dpi:         Render resolution.

    Returns:
        Resolved output_path.

    Raises:
        FileNotFoundError: if pdf_path does not exist.
        ValueError: if page_num < 1 or bbox is degenerate.
    """
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if page_num < 1:
        raise ValueError(f"page_num must be >= 1, got {page_num}")

    x0, y0, x1, y1 = bbox_pt
    if x1 <= x0 or y1 <= y0:
        raise ValueError(
            f"Degenerate bbox_pt: x1 must be > x0 and y1 must be > y0, got {bbox_pt}"
        )

    # Render at full page first, then crop.
    # pdf2image coordinate origin is top-left in pixel space; PDF origin is bottom-left.
    pages = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=page_num,
        last_page=page_num,
    )
    if not pages:
        raise ValueError(f"No page rendered for page_num={page_num} in {pdf_path}")

    page_img: Image.Image = pages[0]
    page_h_px, page_w_px = page_img.height, page_img.width

    # Convert PDF pt → pixels.  1 pt = 1/72 inch; at `dpi` dpi → dpi/72 px/pt.
    scale = dpi / 72.0

    # PDF y-axis: 0 at bottom; Pillow y-axis: 0 at top.
    # Assume standard US Letter (612 × 792 pt) if we can't introspect page size.
    # We infer page height in pt from the rendered pixel height.
    page_h_pt = page_h_px / scale

    left   = int(x0 * scale)
    right  = int(x1 * scale)
    # Flip y: PDF y0 (bottom of region) maps to Pillow top at (page_h_pt - y1)
    top    = int((page_h_pt - y1) * scale)
    bottom = int((page_h_pt - y0) * scale)

    # Clamp to image bounds
    left   = max(0, min(left,   page_w_px))
    right  = max(0, min(right,  page_w_px))
    top    = max(0, min(top,    page_h_px))
    bottom = max(0, min(bottom, page_h_px))

    cropped = page_img.crop((left, top, right, bottom))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    png_info = _build_png_metadata(pdf_path, page_num, dpi, bbox_pt=bbox_pt)
    cropped.save(str(output_path), format="PNG", pnginfo=png_info)
    return output_path.resolve()
