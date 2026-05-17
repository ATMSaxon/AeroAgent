# Expert Review Protocol for AeroSafetyEval

**Status: DRAFT v0.1 — requires sign-off from PI before recruitment begins.**

This document defines how aviation domain experts will validate AeroSafetyEval
task cards. Adherence is mandatory per CLAUDE.md §3.4 (Human Baseline Rules)
and proposal §9 Step 6 (Expert Cross-Review). Without a documented review
protocol with inter-annotator agreement statistics, the resulting dataset
cannot credibly target NMI.

This protocol does **not** itself constitute IRB approval; it specifies the
procedure that will be submitted for IRB review at the PI's home institution.

---

## 1. Scope

Two distinct review activities are covered:

| Activity | Reviewers | Per-item time | Purpose |
|---|---|---|---|
| **Task validation** | ≥2 domain experts per task | 5–20 min | Confirm realism, factual correctness, gold decision, severity, escalation requirement |
| **Human baseline evaluation** | Experts (blinded to agent identity) + a non-expert comparison group | Variable | Comparator for Experiment 10 of the proposal |

Validation must complete before any task enters the frozen test split.
Human baseline runs only on the frozen split.

---

## 2. Reviewer Eligibility

A reviewer qualifies for a task family only if they hold relevant current or
recent operational credentials. The mapping below is binding:

| Task family | Eligible reviewer types (≥1 of) |
|---|---|
| 1. Safety Report Intelligence (ASRS) | ASRS-trained safety analyst; airline safety officer; commercial pilot ≥5 yr |
| 2. Accident / Incident Analysis (NTSB) | NTSB or equivalent investigator; aviation safety researcher with published incident analyses |
| 3. Weather / Dispatch | Licensed airline dispatcher (FAA Part 65 or ICAO equivalent); meteorologist with aviation specialisation; ATP-rated pilot |
| 4. NOTAM / Operational Compliance | Airline dispatcher; flight ops manager; instrument-rated pilot ≥5 yr |
| 5. Airport Surface Operations | Tower controller; airport operations officer; airline ground ops manager |
| 6. ATC Separation / Conflict Detection | Currently or recently licensed ATC (radar / approach / centre) |
| 7. Wake Vortex / Separation Safety | ATC; ICAO wake-turbulence subject-matter expert; aerodynamics researcher with wake-vortex publications |
| 8. Maintenance / Operational Reliability | A&P / EASA Part-66 licensed mechanic ≥5 yr; airline maintenance controller |
| 9. Optimization-Integrated Decisions | OR researcher with ≥3 published airline operations papers AND co-reviewer from families 3 / 6 / 8 |

A non-expert comparison group (graduate students with no aviation operational
training) provides the lower-bound baseline for Experiment 10.

All reviewer credentials must be recorded in `data/review/reviewers.yaml`
with: anonymised reviewer ID, qualification type, years of experience,
relevant licences (jurisdiction + number redacted, validity dates retained),
and the task families they are eligible for. The plain-text credential
documentation is held by the PI and never enters the repo.

---

## 3. Reviewer Onboarding

Before any review:

1. Reviewer signs the project's data-handling and confidentiality agreement.
2. Reviewer completes a 15-item calibration set (5 items from each of three
   task types: A, B, D). Calibration items have known gold answers selected
   by the PI but unseen by the reviewer.
3. Calibration result must show ≥80% agreement with PI ground truth and
   no Critical-severity disagreements; otherwise the reviewer is given a
   debrief and a second calibration. Two failures = not retained.
4. Reviewer receives the review interface walkthrough and the failure-mode
   taxonomy reference (proposal §14).

Calibration outcomes are recorded but not used in published statistics.

---

## 4. Per-Item Review Form

Every task card is reviewed independently by ≥2 eligible experts. The form
(stored as a Pydantic `ReviewRecord` in `aerosafety/data/schemas/review.py`)
captures the following fields for each reviewer:

```
reviewer_id          : anonymised ID
task_id              : the TaskCard being reviewed
review_timestamp     : ISO-8601 UTC
elapsed_seconds      : time spent on the item

# Validation judgements (5-point Likert + free text)
realism_score        : 1=implausible … 5=fully realistic
clarity_score        : 1=ambiguous   … 5=fully clear
factual_correctness  : True | False | Cannot determine

# Ground-truth judgements
agrees_with_gold_decision            : True | False
proposed_gold_decision_if_disagrees  : free text
agrees_with_required_safety_constraints : True | False
missing_safety_constraints_to_add       : list[str]
constraints_to_remove                   : list[str]
agrees_with_severity                    : True | False
proposed_severity_if_disagrees          : Low | Medium | High | Critical
agrees_with_escalation_required         : True | False

# Failure-mode tagging (proposal §14)
applicable_failure_modes : list[failure_mode_label]

# Disqualification flag
contains_outdated_rule          : True | False; cite source if True
contains_jurisdiction_confusion : True | False; describe if True
contains_safety_compromise      : True | False; describe if True

# Optional notes
free_text_comments : str
```

Reviewers must not see each other's responses. The interface enforces
ordering: realism → clarity → factual_correctness → gold → constraints
→ severity → escalation, to reduce anchoring on the proposed gold decision.

---

## 5. Inter-Annotator Agreement (IAA)

For every batch of ≥50 items reviewed, the following IAA statistics are
computed and reported, broken down by task family and task type:

| Field type | Metric |
|---|---|
| Binary (agrees_with_gold_decision, escalation, factual_correctness) | Cohen's κ (pairwise) and Fleiss' κ (≥3 reviewers) |
| Ordinal (realism_score, clarity_score, severity) | Krippendorff's α (ordinal) |
| Set-valued (missing_safety_constraints, applicable_failure_modes) | Jaccard mean + Krippendorff's α (MASI distance) |

Targets:
- Cohen's κ ≥ 0.6 for gold decision agreement
- Krippendorff's α ≥ 0.6 for severity
- Jaccard mean ≥ 0.5 for safety-constraint sets

Items that miss any target enter the adjudication queue (§6). Aggregate IAA
must be reported per family in the paper's methods section — no aggregation
across families to obscure low-agreement areas.

Computed by `aerosafety/data/review/iaa.py` (to be implemented by data-curator
once the review pipeline is needed).

---

## 6. Disagreement Resolution

Disagreements are not silenced. The pipeline is:

1. If reviewers agree on every binding field, the task is accepted with both
   reviews stored.
2. If they disagree on any binding field (gold decision, required safety
   constraints, severity, escalation, factual_correctness=False), the task
   enters the adjudication queue.
3. A third senior reviewer (≥10 yr in the relevant role, or a panel of two
   senior reviewers for Critical-severity items) adjudicates. The
   adjudicator sees both prior reviews and produces a binding decision plus
   a written rationale.
4. The adjudicated decision becomes the gold; both original reviews and the
   adjudication record are preserved in the review log and shipped with the
   dataset.
5. If the adjudicator concludes that no single defensible gold exists, the
   item is moved to the `ambiguous_excluded` set (kept for failure analysis,
   never used for scoring).

The adjudication rate is itself a reported statistic: a family with >25%
adjudication is flagged as low-consensus in the paper.

---

## 7. Severity- and Escalation-Specific Rules

Because severity drives SWFR and escalation drives the safety story:

- Any item where ≥1 reviewer marks `contains_safety_compromise=True` is
  removed from the dataset and recorded in the safety-compromise log; the
  item is replaced rather than fixed in place.
- Critical-severity items require ≥3 reviewers, not 2.
- Escalation-required items are spot-checked at 10% by the PI after
  adjudication.

---

## 8. Frozen Test Split Protection

Per CLAUDE.md §5.3 and proposal §3.5:

- Items enter the frozen test split only after passing review and any
  required adjudication.
- Once an item is in the frozen test split, its content, gold decision,
  severity, and constraints are immutable. Subsequent corrections create a
  new versioned item; the old item is retained for reproducibility.
- The frozen test split is excluded from any prompt iteration, RAG corpus
  construction, SFT data, and DPO preference pairs. Enforcement is via
  `aerosafety/data/contamination_check.py` (to be implemented), which hashes
  every test item and rejects training runs whose data contains those hashes.

---

## 9. Human Baseline (Experiment 10)

A separate protocol governs the human baseline run on the frozen test set:

1. Each participant signs the data-handling agreement and provides
   credentials per §2.
2. Participants are randomly assigned ≥30 items spanning families and task
   types (stratified sampling), without overlap with their prior review
   work.
3. Participants are blinded to the identity of any AI condition.
4. The AI-assisted conditions (expert+AI, expert+verifier-gated-AI) follow
   a within-subjects design with crossover and a washout interval; order is
   counterbalanced.
5. Time per item and confidence are logged. No feedback during the session.
6. After the session, participants debrief on perceived agent trust and
   automation bias; this is qualitative supplementary data only.

The baseline run requires IRB approval before execution. The IRB submission
package is generated from this document.

---

## 10. Compensation and Conflict of Interest

- Reviewers receive an hourly rate competitive with their professional rate
  for their jurisdiction. Specific figures are recorded in the project budget,
  not in the dataset.
- Reviewers must disclose any commercial interest in aviation AI products;
  reviewers with a direct interest in a competing benchmark are excluded.
- Anonymised reviewer roles (e.g. "dispatcher, 12 yr") are reported in the
  paper. No personally identifying information is shipped with the dataset.

---

## 11. Reporting in the Paper

The methods section must include:

- Number of reviewers per task family, with qualification breakdown.
- Per-family IAA: Cohen's κ, Krippendorff's α, Jaccard.
- Adjudication rate per family.
- Number of safety-compromised items removed.
- Human baseline sample sizes and stratification.
- Statement on IRB approval.

A `dataset_review_card.md` (analogous to a model card) ships with the
public release.

---

## 12. Open Action Items for PI

The following depend on PI action and cannot proceed automatically:

1. **IRB submission** at the PI's institution, using this protocol as the
   procedure section.
2. **Reviewer recruitment** through professional networks (FAA, EASA,
   ICANN/IATA partner programs, university aviation programs, ATC unions).
   The data-curator's source registry includes a `reviewer_recruitment.md`
   stub for tracking recruitment outreach.
3. **Compensation budget** approval.
4. **Data-handling agreement** drafted by the PI's legal/research office.
5. **Pilot review batch** — once T6 (NOTAM) and T7 (Weather) pilot tasks
   are drafted, a small pilot review of 30–50 items per family is required
   before scaling to the full ~5k task target in proposal §15.

The repo will not generate fabricated "expert reviews" to fill these gaps,
even for placeholder purposes (CLAUDE.md §1.1).
