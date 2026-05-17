# Synthetic Data — Labeling Rules and Constraints

## Status

All content in this directory is SYNTHETIC.

This label means: these data items were generated programmatically or by human
construction, not copied or extracted from real-world operational records.

---

## When Synthetic Data Is Permitted

Per CLAUDE.md §2.2, synthetic data MAY be used ONLY IF:

1. It is explicitly labeled `SYNTHETIC` — every file, every record, every field.
2. It is generated from real operational constraints (airspace rules, regulatory limits,
   physical aircraft performance parameters derived from authoritative sources).
3. It is physically plausible — no impossible scenarios.
4. It does NOT replace real validation data in any evaluation set.
5. Its generation rules are documented in `generation_configs/` (see below).
6. It is NEVER presented as real-world evidence.

---

## Labeling Convention

Every synthetic record must carry:

```json
{
  "data_label": "SYNTHETIC",
  "provenance": {
    "origin": "synthetic",
    "synthetic_generation_note": "<description of generation rules>",
    "source_id": "<base source_id the constraints are grounded in>",
    ...
  }
}
```

No synthetic record may omit `data_label: SYNTHETIC`.

---

## Prohibited Uses

Synthetic data from this directory MUST NOT be used as:

- Ground-truth answers in the frozen evaluation (test) set.
- Evidence for safety-critical claims in research papers.
- Input to expert annotation as if it were real operational data.
- Training examples labeled as real ASRS/NTSB/METAR records.

---

## Generation Configs

Every batch of synthetic data must have a corresponding config file at:

```
data/synthetic/generation_configs/{batch_id}_config.yaml
```

Config must include:
- `batch_id`: unique identifier
- `generated_at`: UTC timestamp
- `task_family`: which task family this synthetic data serves
- `grounding_sources`: list of authoritative source_ids the constraints come from
- `generation_method`: description of the generation procedure
- `physical_constraints_applied`: list of rules enforced during generation
- `validation_checks`: what was checked to verify plausibility
- `known_limitations`: what is NOT realistic about this synthetic batch

---

## Separation from Real Data

The evaluation pipeline enforces separation:

- Any record with `data_label: SYNTHETIC` is excluded from the frozen test set.
- Training and dev sets may include synthetic records, always with the label.
- Mixing synthetic and real records in aggregated outputs requires explicit
  per-record labeling and a disclosure in any reported results.

---

## Governing Policy

CLAUDE.md §2.2 — Synthetic Data Rules.
CLAUDE.md §1.1 — No Fabricated Data (fabricated ≠ synthetic; fabricated means
  invented without constraint grounding or presented as real).
