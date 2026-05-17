"""
aerosafety.training — Phase 2 dataset construction pipeline.

Converts pilot TaskCards (and future AgentTraces from T8b) into training-ready
JSONL files for SFT, DPO preference optimisation, and AeroVerifier training.

No GPU, no API, no model loading. Pure data transforms.
"""
