#!/usr/bin/env python3
"""
Extract airport diagram page images from FAA Chart Supplement PDFs.

Per CLAUDE.md §2.1: source is FAA Chart Supplement, cycle 20260514.
Per CLAUDE.md §5.1: manifest records sha256, page, source_pdf, timestamp.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aerosafety.data.extractors.pdf_image_extractor import extract_page_image

PDF_BASE = PROJECT_ROOT / "data/raw/FAA_CHART_SUPPL/2026-05-17"
OUTPUT_DIR = PROJECT_ROOT / "data/multimodal/airport_diagrams"
MANIFEST_PATH = OUTPUT_DIR / "manifest.jsonl"

# Airport to (pdf_filename, page_num) mapping
# Source: pdftotext search of FAA Chart Supplement cycle 20260514
AIRPORT_PAGES: list[dict] = [
    # Northeast US (NE)
    {"airport_id": "KJFK", "pdf": "FAA_CS_NE_20260514.pdf", "page": 228},
    {"airport_id": "KLGA", "pdf": "FAA_CS_NE_20260514.pdf", "page": 230},
    {"airport_id": "KEWR", "pdf": "FAA_CS_NE_20260514.pdf", "page": 174},
    {"airport_id": "KBOS", "pdf": "FAA_CS_NE_20260514.pdf", "page": 122},
    {"airport_id": "KPHL", "pdf": "FAA_CS_NE_20260514.pdf", "page": 299},
    {"airport_id": "KDCA", "pdf": "FAA_CS_NE_20260514.pdf", "page": 55},
    {"airport_id": "KIAD", "pdf": "FAA_CS_NE_20260514.pdf", "page": 57},
    {"airport_id": "KBWI", "pdf": "FAA_CS_NE_20260514.pdf", "page": 93},
    # East Central US (EC)
    {"airport_id": "KORD", "pdf": "FAA_CS_EC_20260514.pdf", "page": 44},
    {"airport_id": "KDTW", "pdf": "FAA_CS_EC_20260514.pdf", "page": 175},
    {"airport_id": "KMDW", "pdf": "FAA_CS_EC_20260514.pdf", "page": 43},
    # North Central US (NC)
    {"airport_id": "KMSP", "pdf": "FAA_CS_NC_20260514.pdf", "page": 193},
    {"airport_id": "KSTL", "pdf": "FAA_CS_NC_20260514.pdf", "page": 275},
    # South Central US (SC)
    {"airport_id": "KDFW", "pdf": "FAA_CS_SC_20260514.pdf", "page": 311},
    {"airport_id": "KIAH", "pdf": "FAA_CS_SC_20260514.pdf", "page": 360},
    {"airport_id": "KAUS", "pdf": "FAA_CS_SC_20260514.pdf", "page": 272},
    {"airport_id": "KHOU", "pdf": "FAA_CS_SC_20260514.pdf", "page": 365},
    {"airport_id": "KSAT", "pdf": "FAA_CS_SC_20260514.pdf", "page": 438},
    # Southeast US (SE)
    {"airport_id": "KATL", "pdf": "FAA_CS_SE_20260514.pdf", "page": 205},
    {"airport_id": "KMIA", "pdf": "FAA_CS_SE_20260514.pdf", "page": 143},
    {"airport_id": "KMCO", "pdf": "FAA_CS_SE_20260514.pdf", "page": 152},
    {"airport_id": "KFLL", "pdf": "FAA_CS_SE_20260514.pdf", "page": 110},
    {"airport_id": "KTPA", "pdf": "FAA_CS_SE_20260514.pdf", "page": 180},
    {"airport_id": "KCLT", "pdf": "FAA_CS_SE_20260514.pdf", "page": 308},
    # Southwest US (SW)
    {"airport_id": "KLAS", "pdf": "FAA_CS_SW_20260514.pdf", "page": 403},
    {"airport_id": "KPHX", "pdf": "FAA_CS_SW_20260514.pdf", "page": 78},
    {"airport_id": "KSAN", "pdf": "FAA_CS_SW_20260514.pdf", "page": 274},
    {"airport_id": "KSFO", "pdf": "FAA_CS_SW_20260514.pdf", "page": 277},
    {"airport_id": "KLAX", "pdf": "FAA_CS_SW_20260514.pdf", "page": 202},
    {"airport_id": "KDEN", "pdf": "FAA_CS_SW_20260514.pdf", "page": 346},
    {"airport_id": "KSLC", "pdf": "FAA_CS_SW_20260514.pdf", "page": 503},
    {"airport_id": "KABQ", "pdf": "FAA_CS_SW_20260514.pdf", "page": 431},
    # Northwest US (NW)
    {"airport_id": "KSEA", "pdf": "FAA_CS_NW_20260514.pdf", "page": 272},
    {"airport_id": "KPDX", "pdf": "FAA_CS_NW_20260514.pdf", "page": 202},
]

TARGET_DPI = 150  # Start at 150 DPI; we'll downscale further if >500KB
MAX_FILE_BYTES = 500 * 1024  # 500 KB hard limit


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_records = []
    total_bytes = 0
    failed = []

    for entry in AIRPORT_PAGES:
        airport_id = entry["airport_id"]
        pdf_filename = entry["pdf"]
        page_num = entry["page"]
        pdf_path = PDF_BASE / pdf_filename

        if not pdf_path.exists():
            print(f"  SKIP: PDF not found: {pdf_path}", flush=True)
            failed.append({"airport_id": airport_id, "reason": "pdf_not_found"})
            continue

        out_path = OUTPUT_DIR / f"{airport_id}_diagram.png"
        attachment_id = f"MM-AS-{airport_id}-diagram"

        print(f"  Extracting {airport_id} from {pdf_filename} p.{page_num} ...", flush=True)

        try:
            extract_page_image(
                pdf_path=pdf_path,
                page_num=page_num,
                output_path=out_path,
                dpi=TARGET_DPI,
            )
        except Exception as exc:
            print(f"  ERROR extracting {airport_id}: {exc}", flush=True)
            failed.append({"airport_id": airport_id, "reason": str(exc)})
            continue

        file_size = out_path.stat().st_size

        # Downscale if > 500 KB
        if file_size > MAX_FILE_BYTES:
            print(
                f"  {airport_id}: {file_size/1024:.0f} KB > 500 KB, downscaling ...",
                flush=True,
            )
            from PIL import Image
            img = Image.open(str(out_path))
            # Reduce resolution until under limit: try sequential scale factors
            for scale in [0.75, 0.60, 0.50, 0.40]:
                w = int(img.width * scale)
                h = int(img.height * scale)
                resized = img.resize((w, h), Image.LANCZOS)
                resized.save(str(out_path), format="PNG", optimize=True)
                file_size = out_path.stat().st_size
                if file_size <= MAX_FILE_BYTES:
                    print(f"  {airport_id}: scaled to {scale:.0%} -> {file_size/1024:.0f} KB", flush=True)
                    break
            else:
                print(f"  WARNING: {airport_id} still {file_size/1024:.0f} KB after max downscale", flush=True)

        digest = sha256_file(out_path)
        file_size = out_path.stat().st_size
        total_bytes += file_size

        record = {
            "attachment_id": attachment_id,
            "airport_id": airport_id,
            "source_pdf": f"data/raw/FAA_CHART_SUPPL/2026-05-17/{pdf_filename}",
            "page_num": page_num,
            "sha256": digest,
            "content_length": file_size,
            "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        manifest_records.append(record)
        print(f"  OK {airport_id}: {file_size/1024:.0f} KB  sha256={digest[:12]}...", flush=True)

    # Write manifest
    with MANIFEST_PATH.open("w") as f:
        for rec in manifest_records:
            f.write(json.dumps(rec) + "\n")

    print(f"\n=== DONE ===")
    print(f"Extracted: {len(manifest_records)} airports")
    print(f"Failed: {len(failed)} - {[f['airport_id'] for f in failed]}")
    print(f"Total PNG bytes: {total_bytes:,} ({total_bytes/1024/1024:.1f} MB)")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
