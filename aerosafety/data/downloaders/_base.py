"""
Shared base utilities for all AeroSafetyEval downloader scripts.

Contracts enforced here (CLAUDE.md §8.1, hard rules from task brief):
  - Log every URL fetched with timestamp.
  - Write manifest.jsonl with sha256 + source_url + access_timestamp.
  - Fail loudly on HTTP errors — no silent fallback.
  - Respect documented rate limits via configurable delay.
  - Never execute downloads automatically; callers must invoke explicitly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Root paths — resolved relative to project root at import time.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
RAW_DATA_DIR = _PROJECT_ROOT / "data" / "raw"
MANIFEST_PATH = _PROJECT_ROOT / "data" / "raw" / "manifest.jsonl"


def _ensure_dirs(destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest_entry(entry: dict[str, Any]) -> None:
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def fetch_url(
    source_id: str,
    url: str,
    destination_path: Path,
    *,
    session: requests.Session | None = None,
    rate_limit_seconds: float = 1.0,
    headers: dict[str, str] | None = None,
    stream: bool = True,
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Fetch a single URL to destination_path.

    Logs the URL, writes a manifest entry, and raises on any non-2xx response.
    Never silently falls back on error (CLAUDE.md §8.1).

    Returns the manifest entry dict.
    """
    _ensure_dirs(destination_path.parent)
    sess = session or requests.Session()
    access_ts = datetime.now(timezone.utc)

    logger.info("FETCH source_id=%s url=%s -> %s", source_id, url, destination_path)

    response = sess.get(url, headers=headers, stream=stream, timeout=timeout)

    manifest_entry: dict[str, Any] = {
        "source_id": source_id,
        "url_fetched": url,
        "access_timestamp": access_ts.isoformat(),
        "local_file_path": str(destination_path),
        "sha256": "",
        "http_status_code": response.status_code,
        "content_length_bytes": None,
        "error": None,
    }

    if not response.ok:
        err_msg = (
            f"HTTP {response.status_code} fetching {url} for source {source_id}. "
            f"Response: {response.text[:200]}"
        )
        manifest_entry["error"] = err_msg
        _write_manifest_entry(manifest_entry)
        logger.error("FETCH FAILED: %s", err_msg)
        # Fail loudly — no silent fallback per hard rule 3.
        response.raise_for_status()

    bytes_written = 0
    with open(destination_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                bytes_written += len(chunk)

    sha = _sha256_file(destination_path)
    manifest_entry["sha256"] = sha
    manifest_entry["content_length_bytes"] = bytes_written

    _write_manifest_entry(manifest_entry)
    logger.info(
        "FETCH OK source_id=%s sha256=%s bytes=%d path=%s",
        source_id, sha, bytes_written, destination_path,
    )

    time.sleep(rate_limit_seconds)
    return manifest_entry


def fetch_json_api(
    source_id: str,
    url: str,
    params: dict[str, Any] | None = None,
    *,
    session: requests.Session | None = None,
    rate_limit_seconds: float = 1.0,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Call a JSON API endpoint and return the parsed response body.

    Does NOT write to disk — caller is responsible for persisting response.
    Logs the request and raises on non-2xx responses.
    """
    sess = session or requests.Session()
    access_ts = datetime.now(timezone.utc)

    logger.info(
        "API CALL source_id=%s url=%s params=%s", source_id, url, params
    )

    response = sess.get(url, params=params, headers=headers, timeout=timeout)

    if not response.ok:
        err_msg = (
            f"HTTP {response.status_code} calling {url} "
            f"params={params} for source {source_id}. "
            f"Response: {response.text[:200]}"
        )
        logger.error("API CALL FAILED: %s", err_msg)
        response.raise_for_status()

    body = response.json()
    logger.info(
        "API CALL OK source_id=%s url=%s status=%d",
        source_id, url, response.status_code,
    )
    time.sleep(rate_limit_seconds)
    return body
