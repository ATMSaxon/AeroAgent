"""
Domain Pydantic schemas for the AeroSafetyEval data curation pipeline.

Governed by CLAUDE.md §2 and proposal §9.3.
KnowledgePoint has exactly 7 domain-content fields per proposal §9.3.

Coordination note (T1 dependency):
  aerosafety/io.py (infra-architect T1) defines: TaskCard, TaskProvenance,
  AgentTrace, ToolCall, RetrievedDoc, Recommendation, SeverityLevel.
  This module defines data-curation-specific types not in io.py:
    Provenance, RawDocument, KnowledgePoint, ManifestEntry.
  Do NOT duplicate TaskCard or AgentTrace here — import from aerosafety.io.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Enums ──────────────────────────────────────────────────────────────────

class DataOrigin(str, Enum):
    REAL = "real"
    SYNTHETIC = "synthetic"   # must be labeled per CLAUDE.md §2.2
    EXPERT_VALIDATED = "expert_validated"  # real + expert review


class LicenseType(str, Enum):
    PUBLIC_DOMAIN = "public_domain"
    OPEN_ACCESS = "open_access"
    RESTRICTED_RESEARCH = "restricted_research"
    COMMERCIAL_RESTRICTED = "commercial_restricted"
    UNKNOWN = "unknown"


class TaskFamilyId(int, Enum):
    SAFETY_REPORT = 1
    ACCIDENT_ANALYSIS = 2
    WEATHER_DISPATCH = 3
    NOTAM_COMPLIANCE = 4
    AIRPORT_SURFACE = 5
    ATC_SEPARATION = 6
    WAKE_VORTEX = 7
    MAINTENANCE_RELEASE = 8
    OPTIMIZATION = 9


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureModeCategory(str, Enum):
    EVIDENCE = "evidence"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    NUMERICAL = "numerical"
    REGULATORY = "regulatory"
    TOOL_USE = "tool_use"
    DECISION = "decision"


# ── Provenance ─────────────────────────────────────────────────────────────

class Provenance(BaseModel):
    """
    Full lineage record for a data item.
    Every record entering the pipeline must carry a Provenance.
    No record may be created without a traceable source.
    """
    source_id: str = Field(
        description="Must match a source_id in source_registry.yaml."
    )
    official_url: str = Field(
        description="URL of the original document or API endpoint."
    )
    access_date: datetime = Field(
        description="UTC datetime when the data was accessed or downloaded."
    )
    license: LicenseType
    sha256: str | None = Field(
        default=None,
        description="SHA-256 hex digest of the raw file at download time."
    )
    document_title: str | None = None
    document_section: str | None = Field(
        default=None,
        description="Chapter, section, or page range within the source document."
    )
    origin: DataOrigin = DataOrigin.REAL
    synthetic_generation_note: str | None = Field(
        default=None,
        description=(
            "Required when origin=SYNTHETIC. Must describe generation rules "
            "per CLAUDE.md §2.2. Leave null for real data."
        )
    )
    preprocessing_steps: list[str] = Field(
        default_factory=list,
        description="Ordered list of transformations applied to the raw data."
    )

    @model_validator(mode="after")
    def synthetic_must_have_note(self) -> Provenance:
        if self.origin == DataOrigin.SYNTHETIC and not self.synthetic_generation_note:
            raise ValueError(
                "synthetic_generation_note is required when origin=SYNTHETIC "
                "(CLAUDE.md §2.2)."
            )
        return self

    @field_validator("sha256")
    @classmethod
    def sha256_format(cls, v: str | None) -> str | None:
        if v is not None and len(v) != 64:
            raise ValueError("sha256 must be a 64-character hex string.")
        return v


# ── RawDocument ────────────────────────────────────────────────────────────

class RawDocument(BaseModel):
    """
    A raw ingested document before knowledge-point extraction.
    Stored in data/raw/ after download.
    """
    doc_id: str = Field(
        description=(
            "Unique identifier: '{source_id}_{sha256[:12]}'. "
            "Computed deterministically from source + content hash."
        )
    )
    provenance: Provenance
    text_content: str | None = Field(
        default=None,
        description="Extracted plain text. Null if binary (PDF/image) not yet parsed."
    )
    raw_file_path: str = Field(
        description="Absolute path to the raw file in data/raw/."
    )
    content_type: str = Field(
        description="MIME type or format descriptor (e.g., 'text/plain', 'application/pdf')."
    )
    language: str = Field(default="en")
    task_families: list[TaskFamilyId] = Field(
        description="Which task families this document is relevant to."
    )
    notes: str | None = None

    @model_validator(mode="after")
    def doc_id_format(self) -> RawDocument:
        if self.provenance.sha256:
            expected = f"{self.provenance.source_id}_{self.provenance.sha256[:12]}"
            if self.doc_id != expected:
                raise ValueError(
                    f"doc_id must be '{expected}' (source_id + sha256[:12])."
                )
        return self


# ── KnowledgePoint (7 fields per proposal §9.3) ───────────────────────────

class KnowledgePoint(BaseModel):
    """
    A structured knowledge point extracted from an authoritative corpus.
    Exactly 7 domain-content fields as defined in proposal §9.3:
      1. rule
      2. constraint
      3. applicability_condition
      4. exception
      5. required_evidence
      6. safety_consequence
      7. possible_wrong_interpretation

    Plus metadata fields (id, source, taxonomy) that are infrastructure,
    not content fields — consistent with proposal intent.
    """

    # ── Infrastructure fields (not counted in the 7) ──────────────────────
    kp_id: str = Field(
        description=(
            "Unique identifier: '{branch_id}.{subtopic_id}.{seq:04d}'. "
            "E.g., '3.3.0001' for branch 3, subtopic 3.3, first KP."
        )
    )
    source_doc_id: str = Field(
        description="doc_id of the RawDocument this KP was extracted from."
    )
    provenance: Provenance
    branch_id: int = Field(ge=1, le=9)
    subtopic_id: str = Field(
        description="E.g., '3.3' — matches aviation_safety_taxonomy.yaml subtopic_id."
    )
    task_families: list[TaskFamilyId]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expert_reviewed: bool = Field(
        default=False,
        description="True only after expert cross-review (proposal §9 Step 6)."
    )

    # ── 7 domain-content fields per proposal §9.3 ─────────────────────────

    # Field 1
    rule: str = Field(
        description=(
            "The core operational rule or regulatory statement. "
            "Must be quoted or closely paraphrased from the authoritative source. "
            "No fabrication (CLAUDE.md §1.1)."
        )
    )

    # Field 2
    constraint: str = Field(
        description=(
            "The operational constraint imposed by the rule. "
            "E.g., 'crosswind must not exceed demonstrated crosswind component'."
        )
    )

    # Field 3
    applicability_condition: str = Field(
        description=(
            "When and where the rule applies. "
            "E.g., 'applies to Part 121 operations at certificated airports'."
        )
    )

    # Field 4
    exception: str | None = Field(
        default=None,
        description=(
            "Documented exceptions or waivers to the rule, if any. "
            "Null if none documented in source."
        )
    )

    # Field 5
    required_evidence: str = Field(
        description=(
            "What evidence an agent must produce to correctly apply this rule. "
            "E.g., 'current METAR with wind and gust fields, runway heading'."
        )
    )

    # Field 6
    safety_consequence: str = Field(
        description=(
            "The safety consequence of violating or misapplying this rule. "
            "Must be grounded in the source or a directly inferable operational outcome."
        )
    )

    # Field 7
    possible_wrong_interpretation: str = Field(
        description=(
            "A plausible wrong interpretation an agent might make. "
            "Used as the basis for diagnostic distractor construction (proposal §9 Step 4)."
        )
    )

    # ── Optional enrichment ───────────────────────────────────────────────
    severity: SeverityLevel | None = Field(
        default=None,
        description="Severity if this rule is violated. Set during expert review."
    )
    failure_mode_categories: list[FailureModeCategory] = Field(
        default_factory=list,
        description="Failure mode categories from proposal §14 taxonomy."
    )
    regulatory_reference: str | None = Field(
        default=None,
        description="CFR/ICAO reference. E.g., '14 CFR 91.169' or 'ICAO Doc 4444 §5.4.1'."
    )

    @field_validator("kp_id")
    @classmethod
    def kp_id_format(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) < 3:
            raise ValueError(
                "kp_id must have format '{branch_id}.{subtopic_index}.{seq:04d}'."
            )
        return v

    @model_validator(mode="after")
    def synthetic_kp_requires_note(self) -> KnowledgePoint:
        if self.provenance.origin == DataOrigin.SYNTHETIC:
            if not self.provenance.synthetic_generation_note:
                raise ValueError(
                    "Synthetic KP must have synthetic_generation_note in provenance."
                )
        return self


# ── Manifest entry (written to manifest.jsonl by downloaders) ─────────────

class ManifestEntry(BaseModel):
    """
    One line of manifest.jsonl written by every downloader script.
    Enables auditability and reproducibility per CLAUDE.md §5.1.
    """
    source_id: str
    url_fetched: str
    access_timestamp: datetime
    local_file_path: str
    sha256: str
    http_status_code: int
    content_length_bytes: int | None = None
    error: str | None = Field(
        default=None,
        description="Non-null if download failed. Downloader must log and re-raise."
    )

    @field_validator("sha256")
    @classmethod
    def sha256_format(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("sha256 must be a 64-character hex string.")
        return v
