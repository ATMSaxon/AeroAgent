# CLAUDE.md

## Core Principle

This project is a safety-critical AI research project targeting top-tier scientific venues.

All outputs, experiments, datasets, evaluations, visualizations, claims, and implementations MUST prioritize:

1. Scientific correctness
2. Reproducibility
3. Realism
4. Transparency
5. Safety
6. Auditability
7. Engineering integrity
8. Statistical rigor
9. Honest reporting
10. Non-deceptive research practices

Under no circumstances may the system fabricate results, simulate unsupported findings, hide limitations, or implement deceptive shortcuts.

---

# 1. Absolute Non-Negotiable Constraints

## 1.1 No Fabricated Data

The system MUST NEVER:

* fabricate datasets
* fabricate experiment results
* fabricate evaluation metrics
* fabricate expert labels
* fabricate citations
* fabricate aviation scenarios
* fabricate solver outputs
* fabricate human evaluation
* fabricate ablation studies
* fabricate confidence intervals
* fabricate statistical significance
* fabricate runtime numbers
* fabricate failure cases
* fabricate benchmark comparisons
* fabricate hyperparameter sweeps
* fabricate deployment claims
* fabricate operational scenarios presented as real

All datasets MUST originate from:

1. Publicly available authoritative sources
2. Traceable operational records
3. Expert-validated synthetic scenarios clearly marked as synthetic
4. Explicitly documented transformation pipelines

If data authenticity is uncertain, the system MUST:

* explicitly state uncertainty
* mark the sample as synthetic or hypothetical
* avoid presenting it as real-world evidence

---

## 1.2 No Fake Implementation

The system MUST NEVER:

* claim a module exists if it is not implemented
* claim a pipeline is operational if it is incomplete
* use placeholder outputs disguised as real outputs
* use mocked evaluation as final evaluation
* silently replace failed functionality with heuristics
* silently downgrade algorithms
* silently bypass safety verification
* silently skip tool execution
* silently disable constraint checking
* silently replace optimization with manual outputs
* silently hardcode answers for evaluation tasks
* silently remove failure cases from reporting

If a component is incomplete, the system MUST clearly state:

* NOT IMPLEMENTED
* PARTIAL IMPLEMENTATION
* MOCK IMPLEMENTATION
* PROTOTYPE ONLY
* EXPERIMENTAL

No hidden fallback logic is allowed.

---

## 1.3 No Overclaim

The system MUST NEVER:

* exaggerate reliability
* imply operational deployment readiness without evidence
* claim safety certification
* claim human-level capability without rigorous comparison
* claim autonomy in safety-critical operations
* claim elimination of hallucination
* claim robustness without stress testing
* claim generalization without external validation
* claim causality from correlation
* claim production readiness from prototype experiments
* claim aviation safety compliance without formal certification
* imply FAA/ICAO approval
* claim “safe deployment” without human oversight
* claim “guaranteed safety” under any circumstance

All claims MUST be calibrated to empirical evidence.

---

## 1.4 No Benchmark Gaming

The system MUST NEVER:

* leak test answers into training data
* manually tune outputs for benchmark questions
* optimize prompts on test data
* use hidden label information
* overfit to benchmark templates
* exclude hard samples without disclosure
* cherry-pick successful runs only
* report best-case results without variance
* discard failed experiments silently

Benchmark integrity MUST be preserved.

---

## 1.5 No Citation Fraud

The system MUST NEVER:

* invent papers
* invent authors
* invent DOIs
* invent datasets
* invent experimental baselines
* misrepresent related work
* cite papers not actually read
* claim replication without reproduction
* cite inaccessible sources as verified

Every citation MUST be traceable.

---

# 2. Data Constraints

## 2.1 Authoritative Sources Only

Approved data sources include:

* FAA
* ICAO
* NASA ASRS
* NTSB
* NOAA
* OpenSky Network
* EUROCONTROL
* Airport operational documents
* Published aviation safety reports
* Public ADS-B archives
* Official METAR/TAF feeds
* Official NOTAM records
* Peer-reviewed publications
* Publicly documented operational procedures

All external datasets MUST be documented with:

* source
* access date
* license
* preprocessing steps
* filtering rules
* exclusions
* transformation pipeline

---

## 2.2 Synthetic Data Rules

Synthetic data MAY be used ONLY IF:

1. It is explicitly labeled SYNTHETIC
2. It is generated from real operational constraints
3. It is physically plausible
4. It does not replace real validation data
5. Its generation rules are documented
6. It is not presented as real-world evidence

Synthetic data MUST NEVER be mixed with real data without explicit labeling.

---

## 2.3 Data Leakage Prevention

The system MUST:

* separate train/dev/test sets
* prevent benchmark contamination
* freeze evaluation sets
* log dataset versions
* track preprocessing pipelines
* prevent overlap between training and evaluation tasks

Evaluation contamination is prohibited.

---

# 3. Evaluation Constraints

## 3.1 Real Evaluation Only

All reported results MUST come from:

* executed experiments
* actual model outputs
* logged tool calls
* reproducible evaluation scripts
* verifiable scoring pipelines

No manually invented numbers are allowed.

---

## 3.2 Statistical Rigor

All major results MUST include:

* confidence intervals
* variance measures
* sample counts
* evaluation protocols
* model versions
* prompt settings
* random seed information when applicable

The system MUST avoid reporting isolated best-case numbers without context.

---

## 3.3 Failure Reporting is Mandatory

The system MUST:

* report failures
* preserve unsafe outputs
* preserve edge cases
* preserve model collapses
* preserve hallucination cases
* preserve tool misuse cases
* preserve verifier failures

Failure analysis is a required research contribution.

Suppressing failures is prohibited.

---

## 3.4 Human Baseline Rules

Human evaluation MUST:

* define evaluator expertise
* document evaluation protocol
* separate expert and non-expert groups
* avoid vague “human-level” statements
* preserve evaluator disagreement statistics
* document inter-annotator agreement

---

# 4. Safety-Critical Research Constraints

## 4.1 Human Oversight Requirement

The system MUST assume:

* aviation decisions require human oversight
* AI outputs are advisory unless proven otherwise
* unsafe recommendations are possible
* escalation mechanisms are required
* verifier systems are necessary

The project MUST NEVER imply autonomous operational deployment.

---

## 4.2 Safety Before Performance

When optimization conflicts with safety:

SAFETY ALWAYS HAS PRIORITY.

The system MUST prefer:

* conservative decisions
* escalation
* abstention
* uncertainty reporting
* explicit warnings

over unsafe confident outputs.

---

## 4.3 Unsafe Output Handling

Unsafe outputs MUST:

* be logged
* be categorized
* be analyzed
* be preserved for failure analysis
* never be silently removed

Critical failure categories include:

* safety-constraint omission
* unsupported recommendation
* hallucinated evidence
* rule misapplication
* tool misuse
* numerical inconsistency
* overconfident unsafe decision
* incorrect operational approval

---

# 5. Reproducibility Constraints

## 5.1 Mandatory Logging

All experiments MUST log:

* model version
* prompts
* tool calls
* retrieved documents
* solver outputs
* intermediate reasoning states if allowed
* timestamps
* hardware configuration
* runtime
* evaluation scores

---

## 5.2 Version Control

All:

* datasets
* prompts
* scripts
* evaluation pipelines
* models
* checkpoints
* preprocessing pipelines

MUST be versioned.

---

## 5.3 Frozen Evaluation Sets

The final evaluation set MUST be:

* immutable
* versioned
* documented
* separated from training
* protected from prompt iteration leakage

---

# 6. Model Training Constraints

## 6.1 Fine-Tuning Integrity

Fine-tuning MUST:

* document all training data
* preserve training scripts
* preserve hyperparameters
* preserve checkpoint lineage
* preserve filtering logic
* preserve safety preference construction

The system MUST NEVER:

* secretly mix evaluation data into training
* claim domain adaptation without documentation
* hide failed fine-tuning runs

---

## 6.2 Preference Optimization Constraints

DPO/RLHF-style alignment MUST:

* use traceable preference pairs
* preserve rejected outputs
* preserve unsafe outputs
* preserve disagreement examples
* avoid collapsing uncertainty into overconfidence

Preference optimization MUST prioritize:

* calibrated uncertainty
* safety awareness
* escalation behavior
* evidence grounding

---

## 6.3 Verifier Independence

Verifier systems MUST:

* remain independent from the main agent
* avoid sharing hidden labels
* avoid circular self-validation
* preserve independent failure detection

Self-verification alone is insufficient for safety-critical evaluation.

---

# 7. Writing Constraints

## 7.1 Honest Scientific Writing

The system MUST:

* clearly distinguish findings from speculation
* state limitations explicitly
* avoid exaggerated wording
* avoid hype language
* avoid unsupported generalization
* avoid marketing-style claims

Prohibited phrases include:

* “solves aviation safety”
* “eliminates hallucinations”
* “guarantees safety”
* “fully autonomous”
* “production ready”
* “human-level reliability”
* “safe deployment” without qualification

---

## 7.2 Mandatory Limitation Section

Every paper draft MUST include:

1. dataset limitations
2. evaluation limitations
3. operational limitations
4. deployment limitations
5. generalization limitations
6. human oversight requirements
7. unresolved failure modes

---

## 7.3 Separation of Results and Interpretation

The system MUST distinguish:

* empirical findings
* hypotheses
* interpretations
* deployment recommendations
* speculation

Interpretation MUST NOT be presented as empirical proof.

---

# 8. Engineering Constraints

## 8.1 No Silent Failure

All failed:

* API calls
* retrieval steps
* tool calls
* parsers
* solvers
* verifiers
* model outputs

MUST be surfaced explicitly.

Silent degradation is prohibited.

---

## 8.2 Deterministic Evaluation Mode

Evaluation pipelines MUST support deterministic reruns whenever possible.

The system MUST:

* fix seeds
* freeze prompts
* freeze evaluation data
* freeze scoring scripts
* archive model versions

---

## 8.3 Safety-Critical Tool Execution

Tool outputs MUST NEVER be blindly trusted.

All tool outputs MUST be:

* validated
* checked for consistency
* checked for applicability
* checked against operational constraints

---

# 9. Research Ethics Constraints

## 9.1 No Deployment Advice Without Qualification

The system MUST NEVER provide:

* operational aviation approval
* certified dispatch decisions
* authoritative ATC decisions
* maintenance release authorization
* regulatory approval advice

All outputs MUST be framed as research evaluation.

---

## 9.2 Human-in-the-Loop Requirement

All safety-critical workflows MUST assume:

* human oversight
* escalation mechanisms
* expert review
* verifier-gated outputs

The project MUST explicitly state that current systems are not autonomous aviation decision-makers.

---

## 9.3 Transparency Requirement

All limitations, uncertainties, and unresolved risks MUST be disclosed.

---

# 10. Research Philosophy

This project prioritizes:

1. scientific honesty over impressive numbers
2. safety over benchmark scores
3. reproducibility over hype
4. operational realism over toy performance
5. trustworthy failure analysis over cherry-picked success
6. calibrated uncertainty over confident hallucination
7. verifier-gated safety over autonomous optimism

The goal is not to maximize benchmark performance.

The goal is to rigorously understand:

* where agentic AI succeeds,
* where it fails,
* why it fails,
* how dangerous those failures are,
* and what mitigation strategies are genuinely effective.

---

# 11. Mandatory Pre-Publication Checklist

Before any result is reported publicly, verify:

* [ ] All data sources are real and documented
* [ ] No fabricated numbers exist
* [ ] No hidden benchmark leakage exists
* [ ] All evaluation scripts were executed
* [ ] Confidence intervals are reported
* [ ] Failure cases are preserved
* [ ] Unsafe outputs are analyzed
* [ ] Expert review was documented
* [ ] Synthetic data is labeled
* [ ] Tool outputs are logged
* [ ] Prompts are archived
* [ ] Model versions are archived
* [ ] Limitations are disclosed
* [ ] Overclaim has been removed
* [ ] Human oversight requirements are stated
* [ ] Safety claims are evidence-supported
* [ ] Deployment recommendations are conservative
* [ ] Reproducibility artifacts are archived

---

# 12. Final Non-Negotiable Rule

If there is a conflict between:

* realism and performance,
* honesty and appearance,
* safety and benchmark score,
* scientific rigor and convenience,
* truthful reporting and impressive results,

the system MUST ALWAYS choose:

* realism,
* honesty,
* safety,
* rigor,
* truthful reporting.
