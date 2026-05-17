"""
Tests for multimodal schema extensions and PDF extractor infrastructure.

Per CLAUDE.md §1.2: no mock implementations disguised as real ones.
Per CLAUDE.md §3.3: failures are preserved, not suppressed.
"""

from __future__ import annotations

import hashlib
import importlib
import sys
from pathlib import Path

import pytest

from aerosafety.io import (
    MultimodalAttachment,
    TaskCard,
    TaskProvenance,
    validate_attachments,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def synthetic_provenance() -> TaskProvenance:
    return TaskProvenance(
        source="SYNTHETIC",
        generation_rule="Created for multimodal schema unit tests only.",
    )


@pytest.fixture()
def base_task_card(synthetic_provenance: TaskProvenance) -> TaskCard:
    return TaskCard(
        task_id="SYNTHETIC-MM-001",
        family="airport_surface",
        task_type="A",
        prompt="[SYNTHETIC] Is the depicted runway clear for landing?",
        gold_decision="Yes",
        required_safety_constraints=["Runway must be free of obstructions."],
        severity="High",
        escalation_required=False,
        provenance=synthetic_provenance,
        split="dev",
    )


# ---------------------------------------------------------------------------
# 1. test_attachment_schema_roundtrip
# ---------------------------------------------------------------------------

def test_attachment_schema_roundtrip(
    synthetic_provenance: TaskProvenance,
    base_task_card: TaskCard,
) -> None:
    """MultimodalAttachment survives model_dump → model_validate round-trip."""
    att = MultimodalAttachment(
        attachment_id="att-001",
        kind="image",
        file_path="airport_diagrams/airport_surface_SYNTHETIC-MM-001_001.png",
        description="[SYNTHETIC] Airport diagram crop for schema test.",
        provenance=synthetic_provenance,
        sha256="a" * 64,
    )
    card = base_task_card.model_copy(update={"attachments": [att]})

    dumped = card.model_dump()
    rebuilt = TaskCard.model_validate(dumped)

    assert len(rebuilt.attachments) == 1
    restored = rebuilt.attachments[0]
    assert restored.attachment_id == "att-001"
    assert restored.kind == "image"
    assert restored.sha256 == "a" * 64
    assert restored.provenance.source == "SYNTHETIC"


def test_attachment_kind_all_literals(synthetic_provenance: TaskProvenance) -> None:
    """All four AttachmentKind values are accepted by the schema."""
    for kind in ("image", "pdf_region", "trajectory_plot", "lidar_plot"):
        att = MultimodalAttachment(
            attachment_id=f"att-{kind}",
            kind=kind,  # type: ignore[arg-type]
            file_path=f"test/{kind}.png",
            description=f"[SYNTHETIC] {kind} test.",
            provenance=synthetic_provenance,
            sha256="b" * 64,
        )
        assert att.kind == kind


def test_attachment_kind_rejects_invalid(synthetic_provenance: TaskProvenance) -> None:
    """Unknown kind values are rejected at construction time."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MultimodalAttachment(
            attachment_id="bad",
            kind="video",  # type: ignore[arg-type]
            file_path="test/video.mp4",
            description="[SYNTHETIC] invalid kind.",
            provenance=synthetic_provenance,
            sha256="c" * 64,
        )


# ---------------------------------------------------------------------------
# 2. test_taskcard_with_no_attachments_backward_compat
# ---------------------------------------------------------------------------

def test_taskcard_with_no_attachments_backward_compat(
    base_task_card: TaskCard,
) -> None:
    """
    TaskCards constructed without the attachments field default to an empty list.
    This verifies backward compatibility with the 793 existing text-only cards.
    """
    assert base_task_card.attachments == []

    # Also verify that a dict without the 'attachments' key round-trips cleanly.
    dumped = base_task_card.model_dump()
    assert "attachments" in dumped  # field is present in serialized form
    assert dumped["attachments"] == []

    rebuilt = TaskCard.model_validate(dumped)
    assert rebuilt.attachments == []


def test_taskcard_without_attachments_key_in_dict(
    base_task_card: TaskCard,
) -> None:
    """A dict missing the 'attachments' key is accepted (backward compat)."""
    dumped = base_task_card.model_dump()
    del dumped["attachments"]  # simulate a pre-extension serialized card
    rebuilt = TaskCard.model_validate(dumped)
    assert rebuilt.attachments == []


# ---------------------------------------------------------------------------
# 3. test_validate_attachments_catches_sha256_mismatch
# ---------------------------------------------------------------------------

def test_validate_attachments_passes_on_correct_sha256(
    tmp_path: Path,
    base_task_card: TaskCard,
    synthetic_provenance: TaskProvenance,
) -> None:
    """validate_attachments passes silently when file exists and sha256 matches."""
    img_file = tmp_path / "airport_diagrams" / "airport_surface_SYNTHETIC-MM-001_001.png"
    img_file.parent.mkdir(parents=True)
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)  # minimal fake PNG bytes

    correct_digest = hashlib.sha256(img_file.read_bytes()).hexdigest()
    att = MultimodalAttachment(
        attachment_id="att-001",
        kind="image",
        file_path="airport_diagrams/airport_surface_SYNTHETIC-MM-001_001.png",
        description="[SYNTHETIC] test attachment.",
        provenance=synthetic_provenance,
        sha256=correct_digest,
    )
    card = base_task_card.model_copy(update={"attachments": [att]})
    validate_attachments(card, base_dir=tmp_path)  # must not raise


def test_validate_attachments_catches_sha256_mismatch(
    tmp_path: Path,
    base_task_card: TaskCard,
    synthetic_provenance: TaskProvenance,
) -> None:
    """validate_attachments raises ValueError when sha256 digest does not match."""
    img_file = tmp_path / "airport_diagrams" / "airport_surface_SYNTHETIC-MM-001_001.png"
    img_file.parent.mkdir(parents=True)
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    att = MultimodalAttachment(
        attachment_id="att-001",
        kind="image",
        file_path="airport_diagrams/airport_surface_SYNTHETIC-MM-001_001.png",
        description="[SYNTHETIC] test attachment.",
        provenance=synthetic_provenance,
        sha256="dead" * 16,  # deliberately wrong digest
    )
    card = base_task_card.model_copy(update={"attachments": [att]})

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_attachments(card, base_dir=tmp_path)


def test_validate_attachments_catches_missing_file(
    tmp_path: Path,
    base_task_card: TaskCard,
    synthetic_provenance: TaskProvenance,
) -> None:
    """validate_attachments raises FileNotFoundError when file is absent."""
    att = MultimodalAttachment(
        attachment_id="att-missing",
        kind="pdf_region",
        file_path="airport_diagrams/does_not_exist.png",
        description="[SYNTHETIC] missing file test.",
        provenance=synthetic_provenance,
        sha256="e" * 64,
    )
    card = base_task_card.model_copy(update={"attachments": [att]})

    with pytest.raises(FileNotFoundError, match="att-missing"):
        validate_attachments(card, base_dir=tmp_path)


def test_validate_attachments_not_called_on_construction(
    synthetic_provenance: TaskProvenance,
) -> None:
    """
    Constructing a TaskCard with a non-existent file_path must NOT raise —
    I/O validation is intentionally deferred to validate_attachments().
    """
    att = MultimodalAttachment(
        attachment_id="att-deferred",
        kind="image",
        file_path="/nonexistent/path/that/does/not/exist.png",
        description="[SYNTHETIC] deferred I/O test.",
        provenance=synthetic_provenance,
        sha256="f" * 64,
    )
    # This must not raise FileNotFoundError during Pydantic construction.
    card = TaskCard(
        task_id="SYNTHETIC-MM-002",
        family="airport_surface",
        task_type="B",
        prompt="[SYNTHETIC] Deferred I/O test.",
        gold_decision="N/A",
        required_safety_constraints=[],
        severity="Low",
        escalation_required=False,
        provenance=synthetic_provenance,
        attachments=[att],
    )
    assert len(card.attachments) == 1


# ---------------------------------------------------------------------------
# 4. test_pdf_extractor_imports_cleanly_when_deps_missing
# ---------------------------------------------------------------------------

class _BlockedModule:
    """Sentinel placed in sys.modules to simulate a missing package."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __getattr__(self, item: str) -> object:
        raise ModuleNotFoundError(f"No module named '{self._name}'")


def test_pdf_extractor_raises_import_error_when_pdf2image_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When pdf2image is not installed, importing the extractor raises ImportError
    with a message pointing to aerosafety[multimodal].
    """
    mod_name = "aerosafety.data.extractors.pdf_image_extractor"
    # Remove cached extractor module so the import runs fresh.
    monkeypatch.delitem(sys.modules, mod_name, raising=False)
    # Block pdf2image by inserting a broken sentinel.
    monkeypatch.setitem(sys.modules, "pdf2image", _BlockedModule("pdf2image"))  # type: ignore[arg-type]

    with pytest.raises(ImportError, match="aerosafety\\[multimodal\\]"):
        importlib.import_module(mod_name)


def test_pdf_extractor_raises_import_error_when_pillow_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When Pillow is not installed, importing the extractor raises ImportError
    with a message pointing to aerosafety[multimodal].
    """
    mod_name = "aerosafety.data.extractors.pdf_image_extractor"
    monkeypatch.delitem(sys.modules, mod_name, raising=False)
    # Restore pdf2image but block PIL.
    monkeypatch.delitem(sys.modules, "pdf2image", raising=False)
    monkeypatch.setitem(sys.modules, "PIL", _BlockedModule("PIL"))  # type: ignore[arg-type]
    # Also block PIL.Image and PIL.PngImagePlugin which the extractor imports directly.
    monkeypatch.setitem(sys.modules, "PIL.Image", _BlockedModule("PIL"))  # type: ignore[arg-type]
    monkeypatch.setitem(sys.modules, "PIL.PngImagePlugin", _BlockedModule("PIL"))  # type: ignore[arg-type]

    with pytest.raises(ImportError, match="aerosafety\\[multimodal\\]"):
        importlib.import_module(mod_name)
