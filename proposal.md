下面是**参考附件 NMI 文章后重写和增强的 proposal**。我把重点从“做一个 aviation benchmark”进一步提升为：

> **系统研究 Agentic AI 在航空安全关键运行决策中的可靠性边界，并验证不同缓解策略是否真正降低高严重度风险。**

附件文章给我们的关键启发是：NMI 接受的不只是一个数据集，而是一个完整研究闭环：**安全关键问题提出 → 任务体系构建 → 专家审核 → 多模型评估 → 失败模式分析 → SFT/RAG/Agent 等增强实验 → 部署建议**。LabSafety Bench 文章就是这样做的：它构建了 765 个选择题、404 个真实场景和 3,128 个开放式任务，评估 19 个 LLM/VLM，并发现即使强模型在真实场景 hazard identification 上也没有超过 70% 准确率。

---

# Proposal

## Title

**Reliability Limits of Agentic AI in Aviation Operations and Safety**

## Subtitle

**A Systematic Study Across Safety-Critical Decision Workflows**

---

# 1. Core Positioning

This project investigates the reliability limits of agentic AI in aviation operations and safety-critical decision-making.

The study is positioned as a **safety-critical AI reliability study**, not as a simple aviation dataset or leaderboard. Aviation is used as a high-fidelity operational testbed because it combines strict safety rules, time-sensitive decisions, physical constraints, multi-source evidence, human oversight requirements, and measurable operational consequences.

The central claim is:

**Current agentic AI systems can appear competent in aviation-related reasoning, but they remain unreliable for autonomous safety-critical decision-making because their failures are concentrated in hidden constraints, rule applicability, tool interpretation, evidence grounding, and overconfident unsafe recommendations.**

---

# 2. Why This Can Target NMI

The uploaded NMI article provides a strong precedent. It frames laboratory safety as a safety-critical environment where AI may create an “illusion of understanding,” and argues that standard scientific reasoning or domain knowledge evaluations miss operational safety parameters.

Our proposal follows the same NMI logic but extends it in three ways:

1. **From LLM/VLM to agentic AI**
   The focus is not only whether a model answers correctly, but whether an agent can retrieve evidence, call tools, check rules, reason over constraints, and decide when to escalate.

2. **From hazard identification to operational decision-making**
   The aviation tasks require go/no-go judgments, dispatch decisions, separation checks, maintenance release support, runway conflict assessment, and optimization under safety constraints.

3. **From evaluation to mitigation**
   The study will not only reveal failures, but also test whether RAG, tools, multi-agent collaboration, SFT, DPO, and verifier-gated architectures actually reduce high-severity risk.

This is the key difference from a normal benchmark paper.

---

# 3. Research Questions

## RQ1: Capability Boundary

Can current agentic AI systems perform aviation operations and safety tasks across major decision workflows?

## RQ2: Accuracy–Safety Gap

Does high average task accuracy imply low safety risk in aviation operations?

## RQ3: Retrieval and Tool Reliability

Do RAG and tool use improve safety-critical reliability, or do they introduce new failure modes?

## RQ4: Multi-Agent Reliability

Does multi-agent collaboration reduce unsafe recommendations, or does it mainly increase explanation richness?

## RQ5: Domain Adaptation

Can aviation-specific SFT and safety preference optimization reduce high-severity failures?

## RQ6: Verification and Deployment

Do verifier-gated architectures reduce critical failures more effectively than model scaling, RAG, tools, or fine-tuning alone?

---

# 4. Main Hypotheses

## H1: General Competence Does Not Imply Operational Safety

Agents may achieve high scores on aviation knowledge and text reasoning tasks, but still fail on time-sensitive, constraint-heavy, safety-critical decisions.

## H2: Retrieval Improves Evidence but Does Not Guarantee Safety

RAG may improve evidence grounding, but may not prevent safety-constraint omissions. The uploaded NMI article found that a standard RAG setup was often ineffective or detrimental, possibly due to contextual distraction.

## H3: Tools Shift Risk Rather Than Eliminate It

Tool use can improve numerical calculation, parsing, and rule lookup, but agents may select the wrong tool, provide wrong inputs, or misinterpret correct outputs.

## H4: Multi-Agent Debate Does Not Necessarily Reduce Risk

Multi-agent systems may produce more complete explanations but can still converge on unsafe decisions.

## H5: Domain Adaptation Helps but Is Insufficient

Aviation-specific SFT may improve domain fluency and task performance, similar to the SFT gains observed for smaller models in the uploaded NMI article, but fine-tuning alone may not eliminate high-severity failures.

## H6: Verifier-Gated Architectures Are the Most Practical Mitigation

Independent evidence, rule, tool, numerical, and safety verifiers will reduce critical failures more reliably than RAG, tools, or fine-tuning alone.

---

# 5. Proposed System: AeroSafetyEval

The internal evaluation environment will be called **AeroSafetyEval**.

It should not be the main title of the paper. It should appear in Methods as the executable environment built to conduct the study.

AeroSafetyEval will include:

1. aviation safety and operations task families;
2. authoritative aviation corpora;
3. structured and open-ended tasks;
4. multimodal tasks;
5. tool-use environments;
6. agent action logs;
7. expert-reviewed ground truth;
8. safety-severity labels;
9. failure-mode annotations;
10. mitigation experiments.

This follows the structure of the uploaded NMI article, where the authors built a taxonomy, collected authoritative corpora, used expert–AI collaboration, refined questions, generated scenarios, cross-reviewed answers, evaluated models, and tested enhancement strategies.

---

# 6. Task Design Philosophy

The task design should follow three principles.

## Principle 1: Foundational + Specialized Coverage

The uploaded NMI article explicitly balances broad applicability and procedural specificity across biology, chemistry, and physics laboratories.

For aviation, we should similarly cover:

1. foundational operational safety rules;
2. common airline/airport/ATM workflows;
3. specialized high-risk scenarios such as wake vortex, maintenance release, NOTAM restrictions, and low-visibility operations.

## Principle 2: Knowledge + Scenario + Decision

Do not only ask aviation knowledge questions.

Each task family should contain:

1. **Knowledge tasks**
   Tests whether the model knows rules, terms, categories, and procedures.

2. **Scenario risk tasks**
   Tests whether the model can identify hidden hazards in realistic scenarios.

3. **Consequence prediction tasks**
   Tests whether the model can predict downstream operational consequences.

4. **Operational decision tasks**
   Tests whether the model can make or support a safety-sensitive recommendation.

5. **Agentic workflow tasks**
   Tests whether the agent retrieves, calculates, checks rules, uses tools, verifies, and escalates properly.

The uploaded article’s HIT and CIT structure is especially useful: HIT evaluates comprehensive hazard perception, while CIT evaluates anticipatory consequence reasoning.

## Principle 3: Expert-Reviewed Ground Truth

Every high-risk task must have:

1. gold decision;
2. required safety constraints;
3. acceptable answer variants;
4. evidence requirements;
5. severity label;
6. escalation label;
7. failure-mode labels.

The uploaded article required expert cross-review to ensure relevance, practicality, and correctness, and used challenging distractors to test deeper safety knowledge.

---

# 7. Aviation Task Families

## Task Family 1: Aviation Safety Report Intelligence

### Data

ASRS reports, incident narratives, voluntary safety reports.

### Tasks

1. event type classification;
2. flight phase identification;
3. contributing factor extraction;
4. causal chain reconstruction;
5. risk severity classification;
6. mitigation recommendation;
7. similar-case retrieval;
8. unsupported recommendation detection.

### Agentic Requirement

The agent must cite evidence from the report, distinguish direct causes from contributing factors, and avoid unsupported mitigation advice.

---

## Task Family 2: Accident and Incident Analysis

### Data

NTSB accident reports, incident summaries, structured accident fields.

### Tasks

1. probable cause identification;
2. contributing factor classification;
3. human factor analysis;
4. maintenance-related factor identification;
5. accident sequence reconstruction;
6. prevention recommendation evaluation.

### Agentic Requirement

The agent must avoid confusing correlation with causality and must distinguish evidence-supported conclusions from speculation.

---

## Task Family 3: Weather and Dispatch Risk

### Data

METAR, TAF, runway configuration, dispatch minima, weather advisories.

### Tasks

1. METAR decoding;
2. TAF interpretation;
3. crosswind and tailwind calculation;
4. visibility and ceiling judgment;
5. alternate airport requirement assessment;
6. delay/divert/cancel/proceed recommendation.

### Required Tools

1. METAR parser;
2. TAF time-window checker;
3. wind component calculator;
4. weather minima checker.

### Critical Failures

1. ignoring gusts;
2. misreading TAF validity;
3. confusing ceiling and visibility;
4. unsafe proceed recommendation.

---

## Task Family 4: NOTAM and Operational Compliance

### Data

FAA NOTAM examples, historical NOTAM snapshots, airport restrictions.

### Tasks

1. NOTAM parsing;
2. effective time judgment;
3. runway/taxiway closure detection;
4. spatial applicability judgment;
5. flight operation compliance;
6. go/no-go recommendation.

### Required Tools

1. NOTAM parser;
2. time-validity checker;
3. runway identifier checker;
4. rule-compliance checker.

### Critical Failures

1. missing active NOTAM;
2. misreading effective time;
3. confusing runway identifiers;
4. treating advisory as mandatory or mandatory as advisory;
5. unsafe compliance judgment.

---

## Task Family 5: Airport Surface Operations

### Data

Airport diagrams, runway/taxiway graph representations, synthetic ground movement scenarios.

### Tasks

1. runway incursion risk detection;
2. taxi route conflict detection;
3. hold-short compliance check;
4. runway crossing conflict assessment;
5. aircraft–vehicle conflict detection;
6. surface movement sequencing.

### Required Tools

1. airport graph tool;
2. route conflict checker;
3. runway occupancy calculator;
4. spatial intersection checker.

### Critical Failures

1. missing runway crossing conflicts;
2. ignoring hold-short instructions;
3. failing to detect simultaneous runway occupancy;
4. unsafe taxi or crossing recommendation.

---

## Task Family 6: Air Traffic Separation and Conflict Detection

### Data

ADS-B trajectories, synthetic conflict scenarios, terminal airspace tracks.

### Tasks

1. horizontal separation check;
2. vertical separation check;
3. loss-of-separation detection;
4. conflict prediction;
5. time-to-conflict estimation;
6. resolution recommendation assessment.

### Required Tools

1. distance calculator;
2. trajectory interpolation tool;
3. time synchronization tool;
4. conflict detection tool.

### Critical Failures

1. unit conversion error;
2. ignoring vertical separation;
3. failing to predict future conflict;
4. unsafe resolution recommendation.

---

## Task Family 7: Wake Vortex and Separation Safety

### Data

Aircraft type tables, wake categories, runway configuration, wind profiles, LiDAR-derived wake scenarios.

### Tasks

1. wake category identification;
2. static separation minima judgment;
3. dynamic separation recommendation;
4. wake persistence interpretation;
5. LiDAR detection result interpretation;
6. throughput–safety trade-off explanation.

### Required Tools

1. wake category checker;
2. wind profile interpreter;
3. separation rule checker;
4. wake-risk calculator.

### Critical Failures

1. ignoring preceding aircraft category;
2. misinterpreting wind effect;
3. misreading LiDAR output;
4. recommending insufficient separation.

---

## Task Family 8: Maintenance and Operational Reliability

### Data

Maintenance discrepancy records, MEL-like rules, system failure descriptions, service difficulty reports.

### Tasks

1. dispatch eligibility judgment;
2. maintenance restriction identification;
3. required action extraction;
4. operational limitation assessment;
5. repeat-failure risk recognition;
6. safe release recommendation.

### Required Tools

1. MEL rule checker;
2. fault-condition matcher;
3. maintenance restriction checker.

### Critical Failures

1. recommending dispatch when not allowed;
2. ignoring MEL conditions;
3. missing repeat defects;
4. misinterpreting redundancy;
5. unsafe release decision.

---

## Task Family 9: Optimization-Integrated Aviation Decisions

### Data

Runway sequencing scenarios, wake-constrained scheduling instances, gate assignment instances, ground delay scenarios, low-altitude corridor allocation cases.

### Tasks

1. runway sequencing;
2. gate assignment;
3. arrival–departure balancing;
4. wake-separation-constrained sequencing;
5. ground delay allocation;
6. low-altitude corridor capacity allocation;
7. emergency diversion assignment.

### Required Tools

1. optimization solver;
2. constraint checker;
3. feasibility verifier;
4. objective-value calculator.

### Critical Failures

1. generating infeasible models;
2. ignoring safety constraints;
3. optimizing efficiency at the expense of safety;
4. misinterpreting solver output.

---

# 8. Task Types Within Each Family

Each task family should include four task types.

## Type A: Structured Knowledge and Rule Questions

Purpose:

Evaluate domain knowledge and rule recognition.

Example:

Given a runway closure NOTAM, identify whether a planned operation is affected.

Scoring:

Exact match or structured label accuracy.

---

## Type B: Passive Hazard Identification

This is the aviation analogue of HIT in the uploaded article.

Purpose:

Evaluate whether the agent can identify all relevant operational hazards in a static scenario.

Example:

Given a METAR, TAF, runway configuration, NOTAM, and aircraft type, identify all safety-relevant hazards before departure.

Scoring:

Coverage of ground-truth hazard points.

---

## Type C: Active Consequence Prediction

This is the aviation analogue of CIT.

Purpose:

Evaluate whether the agent can predict consequences of a risky action.

Example:

If the aircraft departs despite the active NOTAM and crosswind condition, what operational and safety consequences could occur?

Scoring:

Coverage of immediate and downstream consequences.

---

## Type D: Agentic Operational Decision

Purpose:

Evaluate whether the agent can retrieve evidence, call tools, check constraints, and produce an operational recommendation.

Example:

Should this flight proceed, delay, divert, or require human escalation?

Scoring:

Decision correctness, evidence grounding, tool-use reliability, safety violation, escalation appropriateness.

---

# 9. Data Curation Pipeline

The proposal should use a more rigorous pipeline than the earlier version.

## Step 1: Construct Aviation Safety Taxonomy

Build a taxonomy covering:

1. flight operations;
2. airport operations;
3. air traffic management;
4. dispatch and weather;
5. NOTAM and compliance;
6. wake vortex and separation;
7. maintenance release;
8. accident causation;
9. optimization-integrated operations.

This mirrors the uploaded article’s approach of starting with a domain taxonomy before task generation.

---

## Step 2: Collect Authoritative Corpora

Use only authoritative or traceable sources for safety-critical tasks.

Candidate sources:

1. FAA documents;
2. ICAO documents;
3. NASA ASRS;
4. NTSB reports;
5. METAR/TAF archives;
6. NOTAM snapshots;
7. aircraft wake category tables;
8. airport diagrams;
9. public ADS-B data;
10. maintenance safety documents;
11. airport and airline operational manuals where available.

The uploaded article emphasizes authoritative corpora and expert cross-review as core design principles.

---

## Step 3: Extract Key Operational Knowledge Points

For each corpus, extract:

1. rule;
2. constraint;
3. applicability condition;
4. exception;
5. required evidence;
6. safety consequence;
7. possible wrong interpretation.

Example:

For NOTAM:

* rule: runway 09/27 closed;
* condition: valid between specified UTC times;
* applicability: airport/runway-specific;
* wrong interpretation: local-time/UTC confusion;
* consequence: unsafe runway use.

---

## Step 4: Generate Structured Diagnostic Tasks

Create diagnostic tasks from each knowledge point.

Unlike ordinary MCQs, aviation diagnostic questions should include:

1. plausible unsafe distractors;
2. partially correct but incomplete options;
3. advisory/mandatory confusion;
4. time-window traps;
5. unit-conversion traps;
6. missing exception traps.

The uploaded article used misleading but plausible distractors to test deeper safety knowledge.

---

## Step 5: Generate Realistic Scenarios

Each scenario should be seeded from one or more validated knowledge points.

Scenario elements:

1. operational context;
2. aircraft type;
3. airport/runway status;
4. weather;
5. NOTAM;
6. traffic condition;
7. maintenance condition;
8. decision objective;
9. possible unsafe action.

The uploaded article generated realistic scenarios from validated MCQs and then had experts verify authenticity and ground truth.

---

## Step 6: Expert Cross-Review

Each high-risk scenario should be reviewed by at least two domain reviewers.

Reviewer types:

1. aviation safety expert;
2. pilot/dispatcher/ATC expert;
3. maintenance expert for maintenance tasks;
4. airport operations expert for surface tasks;
5. optimization expert for solver tasks.

Review outputs:

1. factual correctness;
2. realism;
3. gold decision;
4. safety constraints;
5. severity label;
6. escalation requirement;
7. acceptable answer variants.

---

## Step 7: Build Multimodal Tasks

Add visual and tabular inputs:

1. airport diagrams;
2. taxiway graphs;
3. runway layouts;
4. LiDAR wake plots;
5. weather radar snapshots;
6. trajectory plots;
7. maintenance status tables;
8. Gantt charts for sequencing tasks.

The uploaded article includes text-with-image questions designed so that the visual element is necessary, not redundant.

For aviation, the same principle should apply: the text should not fully reveal the visual hazard. The model must actually interpret the diagram, trajectory, or plot.

---

# 10. Agent Systems to Evaluate

## System 1: Direct LLM

No retrieval, no tools, no verifier.

Purpose:

Basic model-level baseline.

---

## System 2: RAG Agent

Uses aviation evidence retrieval before answering.

Purpose:

Test whether retrieval improves evidence grounding and whether it causes contextual distraction.

---

## System 3: Tool-Augmented Agent

Can call parsers, calculators, rule checkers, conflict detectors, and solvers.

Purpose:

Test whether tool use improves operational reliability.

---

## System 4: Multi-Agent System

Role-specialized agents:

1. operations analyst;
2. safety officer;
3. regulation specialist;
4. tool-use agent;
5. final decision agent.

Purpose:

Test whether multi-agent collaboration reduces safety risk.

---

## System 5: Aviation-SFT Agent

Open-source model fine-tuned on aviation instruction data.

Purpose:

Test whether domain adaptation improves aviation-specific reliability.

---

## System 6: Aviation-DPO Agent

Preference-optimized model trained on safe vs unsafe answer pairs.

Purpose:

Test whether safety preference optimization reduces unsafe recommendations.

---

## System 7: Verifier-Gated Agent

The final answer must pass independent checks before output.

Verifier modules:

1. evidence verifier;
2. rule verifier;
3. numerical verifier;
4. tool-use verifier;
5. safety-constraint verifier;
6. escalation verifier.

Purpose:

Test whether verification reduces critical failures.

---

# 11. Training Components

## 11.1 Aero-SFT

### Objective

Improve aviation-domain instruction following, terminology, and structured output.

### Training Data

1. ASRS reasoning examples;
2. NTSB causal analysis examples;
3. weather dispatch examples;
4. NOTAM compliance examples;
5. wake separation examples;
6. maintenance release examples;
7. optimization interpretation examples.

### Key Test

Does SFT improve only average performance, or does it reduce high-severity failure?

---

## 11.2 AeroSafety-DPO

### Objective

Align the model toward safer aviation decisions.

### Preference Pair Types

1. safe vs unsafe recommendation;
2. evidence-supported vs unsupported answer;
3. complete constraint reasoning vs incomplete reasoning;
4. conservative escalation vs overconfident automation;
5. correct tool use vs wrong tool use;
6. rule-compliant vs rule-violating decision.

The uploaded article constructed DPO preference pairs by pairing correct-answer explanations with incorrect-answer explanations.

For aviation, DPO pairs should emphasize downstream operational consequences, not only correct labels.

---

## 11.3 AeroVerifier

### Objective

Train independent verifier models to detect unsafe or unsupported outputs.

### Inputs

1. scenario;
2. retrieved evidence;
3. tool outputs;
4. agent reasoning trace;
5. final recommendation.

### Outputs

1. pass;
2. fail;
3. needs human escalation;
4. violated constraint;
5. severity level;
6. missing evidence type.

### Verifier Tasks

1. evidence support detection;
2. safety constraint omission detection;
3. rule applicability checking;
4. numerical consistency checking;
5. tool-call correctness checking;
6. escalation necessity classification.

---

# 12. Evaluation Metrics

## 12.1 Task Success Rate

Measures final decision correctness.

[
TSR = \frac{1}{N}\sum_{i=1}^{N}\mathbb{1}(\hat{y_i}=y_i)
]

---

## 12.2 Safety Violation Rate

Measures unsafe recommendations.

[
SVR = \frac{1}{N}\sum_{i=1}^{N}\mathbb{1}(\text{unsafe recommendation}_i)
]

Examples:

1. recommending departure despite active runway closure;
2. ignoring wake separation;
3. ignoring weather minima;
4. recommending dispatch despite MEL restriction;
5. missing loss-of-separation risk.

---

## 12.3 Safety Constraint Omission Rate

Measures omitted critical constraints.

[
SCOR = \frac{# \text{omitted critical constraints}}{# \text{critical constraints}}
]

---

## 12.4 Evidence Faithfulness

Submetrics:

1. correct evidence citation rate;
2. unsupported claim rate;
3. hallucinated evidence rate;
4. contradiction with evidence rate.

---

## 12.5 Tool-Use Reliability

Submetrics:

1. required tool call rate;
2. correct tool selection rate;
3. correct tool input rate;
4. correct tool-output interpretation rate;
5. tool misuse rate.

---

## 12.6 Consequence Coverage Score

For active consequence prediction tasks:

[
CCS = \frac{# \text{covered consequence points}}{# \text{ground-truth consequence points}}
]

This follows the uploaded article’s open-ended scoring idea, where each ground-truth point is assessed individually and the final score is the fraction of covered points.

---

## 12.7 Overconfident Failure Rate

[
OFR = \frac{# \text{wrong high-confidence answers}}{# \text{wrong answers}}
]

This is essential for deployment risk.

---

## 12.8 Severity-Weighted Failure Rate

[
SWFR = \frac{1}{N}\sum_{i=1}^{N} w_i \cdot \mathbb{1}(\text{failure}_i)
]

Suggested weights:

| Severity |                                        Meaning | Weight |
| -------- | ---------------------------------------------: | -----: |
| Low      |                 Minor factual or wording error |      1 |
| Medium   | Operationally relevant but not safety-critical |      3 |
| High     |            Compliance or safety-relevant error |      5 |
| Critical |  Unsafe recommendation with severe consequence |     10 |

---

## 12.9 Cost-Adjusted Safety Score

[
CASS =
\frac{
TSR \times (1-SVR)
}{
1+\alpha C_{\text{token}}+\beta C_{\text{tool}}+\gamma T
}
]

This compares safety gain against token cost, tool calls, and latency.

---

## 12.10 Output-Length-Controlled Safety Recall

The uploaded article showed that verbose outputs can artificially improve hazard coverage, and controlled model outputs to exactly three, five, or ten hazards to separate real capability from verbosity.

For aviation, open-ended hazard identification should be evaluated under:

1. unconstrained output;
2. top-3 hazards;
3. top-5 hazards;
4. top-10 hazards.

This prevents verbose agents from winning by listing everything.

---

# 13. Experimental Plan

## Experiment 1: Cross-Workflow Reliability

### Purpose

Evaluate all agent systems across all aviation task families.

### Systems

1. Direct LLM;
2. RAG agent;
3. tool-augmented agent;
4. multi-agent system;
5. Aero-SFT;
6. AeroSafety-DPO;
7. verifier-gated agent.

### Main Metrics

1. TSR;
2. SVR;
3. SCOR;
4. evidence faithfulness;
5. tool-use reliability;
6. SWFR;
7. CASS.

### Expected Finding

Models perform better on structured knowledge tasks than on realistic operational decision workflows.

---

## Experiment 2: Structured vs Scenario Gap

### Purpose

Measure the performance gap between rule knowledge and scenario reasoning.

### Design

Compare:

1. structured diagnostic questions;
2. passive hazard identification;
3. active consequence prediction;
4. operational decision tasks.

### Expected Finding

Agents may know aviation rules but fail to apply them in realistic, multi-constraint scenarios.

This mirrors the uploaded article’s finding that models performed much worse on scenario-based tasks than on structured MCQs.

---

## Experiment 3: Accuracy–Safety Gap

### Purpose

Test whether high task accuracy implies low safety risk.

### Design

For each model and agent architecture, plot:

1. task success rate;
2. safety violation rate;
3. severity-weighted failure rate.

### Expected Finding

Some systems will have strong average accuracy but still produce critical unsafe recommendations.

---

## Experiment 4: RAG Contextual Distraction

### Purpose

Test whether RAG improves safety or distracts the model.

### Systems

1. no RAG;
2. naive RAG;
3. domain-filtered RAG;
4. constraint-aware RAG;
5. RAG + verifier.

### Expected Finding

Naive RAG may improve evidence citation but not safety; constraint-aware RAG plus verification should perform better.

This directly builds on the uploaded article’s finding that standard RAG was not a “silver bullet” and was often detrimental.

---

## Experiment 5: Tool-Use Reliability

### Purpose

Evaluate whether tools improve safety-critical decisions.

### Systems

1. no tools;
2. calculators only;
3. parsers + calculators;
4. parsers + calculators + rule checkers;
5. full tool suite;
6. full tool suite + verifier.

### Expected Finding

Tools improve local computations but create new failure modes in tool selection, input construction, and output interpretation.

---

## Experiment 6: Multi-Agent Reliability

### Purpose

Test whether multi-agent collaboration improves aviation safety.

### Systems

1. single agent;
2. multi-agent debate;
3. role-specialized multi-agent;
4. role-specialized multi-agent + verifier.

### Expected Finding

Multi-agent systems may increase explanation richness but not consistently reduce high-severity errors unless paired with verification.

---

## Experiment 7: Domain Adaptation

### Purpose

Evaluate aviation-specific SFT and DPO.

### Systems

1. base open-source model;
2. Aero-SFT;
3. AeroSafety-DPO;
4. Aero-SFT + RAG;
5. AeroSafety-DPO + verifier.

### Expected Finding

SFT improves aviation language and rule familiarity; DPO improves safety preference; verifier-gating remains necessary for critical decisions.

---

## Experiment 8: Verifier-Gated Mitigation

### Purpose

Determine whether independent verification is the strongest mitigation strategy.

### Verifier Combinations

1. evidence verifier only;
2. rule verifier only;
3. numerical verifier only;
4. tool-use verifier only;
5. safety verifier only;
6. full verifier-gated pipeline.

### Expected Finding

Full verifier-gating produces the largest reduction in critical failures, with increased cost and latency.

---

## Experiment 9: Multimodal Aviation Reasoning

### Purpose

Evaluate tasks requiring visual and textual integration.

### Inputs

1. airport diagrams;
2. taxiway graphs;
3. runway maps;
4. trajectory plots;
5. weather radar images;
6. LiDAR wake signatures;
7. maintenance status tables.

### Expected Finding

Multimodal aviation tasks reveal additional failures in spatial reasoning, visual grounding, and diagram interpretation.

---

## Experiment 10: Human Baseline and Human Oversight

### Purpose

Compare agent performance with human experts and evaluate human-review value.

### Human Groups

1. non-expert aviation students;
2. trained aviation students;
3. pilots/dispatchers/ATC/maintenance experts;
4. expert + AI assistance;
5. expert + verifier-gated AI assistance.

### Expected Finding

AI assistance may improve speed or recall in low-risk tasks, but expert oversight remains necessary for high-risk decisions.

The uploaded article included human evaluation and IRB approval; a similar human-evaluation protocol will be important for NMI credibility.

---

# 14. Failure Mode Taxonomy

## A. Evidence Failures

1. hallucinated evidence;
2. unsupported claim;
3. wrong citation;
4. selective evidence use;
5. contradiction with evidence.

## B. Temporal Failures

1. NOTAM validity error;
2. TAF time-window error;
3. stale information use;
4. UTC/local time confusion;
5. sequence-ordering error.

## C. Spatial Failures

1. wrong runway applicability;
2. wrong airport applicability;
3. airspace boundary error;
4. taxiway/runway graph error;
5. trajectory conflict miss.

## D. Numerical and Physical Failures

1. crosswind miscalculation;
2. distance calculation error;
3. altitude separation error;
4. unit conversion error;
5. wake persistence misinterpretation.

## E. Regulatory and Procedural Failures

1. rule misapplication;
2. exception ignored;
3. advisory/mandatory confusion;
4. MEL condition omission;
5. separation minima omission.

## F. Tool-Use Failures

1. missing required tool call;
2. wrong tool selected;
3. wrong tool input;
4. correct output misinterpreted;
5. tool output overtrusted.

## G. Decision Failures

1. unsafe recommendation;
2. over-conservative recommendation;
3. missing escalation;
4. overconfident wrong answer;
5. incomplete final decision.

The uploaded article’s case analysis identified hallucination, poor reasoning, visual interpretation difficulty, misaligned safety priorities, and lack of comprehensiveness as major model failures. Our taxonomy should be more operational and agent-specific.

---

# 15. Data Scale

Recommended final scale:

| Component                          |      Target Scale |
| ---------------------------------- | ----------------: |
| Raw aviation documents/snippets    | 100,000–1,000,000 |
| Structured diagnostic tasks        |       3,000–5,000 |
| Scenario-based risk tasks          |       3,000–6,000 |
| Agentic operational decision tasks |       2,000–5,000 |
| Multimodal tasks                   |       1,000–3,000 |
| Optimization-integrated tasks      |       1,000–2,000 |
| Expert-reviewed core test set      |       2,000–5,000 |
| High-severity stress-test set      |       1,000–3,000 |
| SFT samples                        |    50,000–200,000 |
| DPO preference pairs               |    20,000–100,000 |
| Verifier labels                    |    50,000–300,000 |

The paper should emphasize the **expert-reviewed core test set** and **high-severity stress-test set**, not just total size.

---

# 16. Manuscript Storyline

The paper should be written around five results.

## Result 1

**Aviation operations expose a gap between task competence and operational reliability.**

Agents perform reasonably on structured aviation knowledge tasks but fail more often in realistic safety-critical scenarios.

## Result 2

**High average accuracy masks high-severity unsafe recommendations.**

Safety violation rate and severity-weighted failure rate reveal risks hidden by standard accuracy.

## Result 3

**RAG, tools, and multi-agent collaboration improve partial capabilities but do not eliminate critical failures.**

Each enhancement helps locally but introduces or leaves unresolved safety risks.

## Result 4

**Domain adaptation improves aviation fluency but does not remove hidden constraint failures.**

SFT and DPO improve average performance, but high-severity errors remain.

## Result 5

**Verifier-gated architectures provide the strongest near-term mitigation.**

Independent evidence, rule, numerical, tool, and escalation checks reduce critical failures and define practical deployment boundaries.

---

# 17. Figure Plan

## Figure 1: Aviation as a Safety-Critical Agentic AI Testbed

Show:

1. aviation task families;
2. agent systems;
3. tool environment;
4. verifiers;
5. risk-sensitive metrics.

## Figure 2: Task Construction Pipeline

Show:

1. authoritative corpora;
2. knowledge-point extraction;
3. diagnostic task generation;
4. scenario generation;
5. expert cross-review;
6. operational decision task construction;
7. evaluation and mitigation experiments.

This should visually parallel the methodology figure in the uploaded NMI article, but adapted to agentic aviation workflows.

## Figure 3: Structured–Scenario–Decision Performance Gap

Show model performance across:

1. structured rule tasks;
2. hazard identification;
3. consequence prediction;
4. operational decision;
5. agentic tool-use tasks.

## Figure 4: Accuracy–Safety Gap

Scatter plot:

* x-axis: task success rate;
* y-axis: severity-weighted failure rate;
* point size: cost;
* color: agent architecture.

## Figure 5: Effect of Mitigation Strategies

Compare:

1. direct LLM;
2. RAG;
3. tools;
4. multi-agent;
5. SFT;
6. DPO;
7. verifier-gated agent.

## Figure 6: Failure Mode Distribution and Deployment Boundary

Show:

1. failure taxonomy;
2. severity distribution;
3. mitigation effectiveness;
4. recommended deployment category.

---

# 18. Deployment Boundary Map

## Category 1: Low-Risk Assistance

Suitable tasks:

1. summarizing safety reports;
2. retrieving similar cases;
3. drafting human-reviewed safety briefings;
4. extracting non-critical information.

## Category 2: Human-Reviewed Decision Support

Suitable tasks:

1. risk factor identification;
2. NOTAM summarization;
3. weather briefing support;
4. maintenance discrepancy summarization.

## Category 3: Verifier-Gated Use Only

Suitable tasks:

1. NOTAM compliance judgment;
2. weather dispatch recommendation;
3. wake separation assessment;
4. runway conflict screening;
5. maintenance release support.

## Category 4: Not Suitable for Autonomous Deployment

Unsuitable tasks:

1. final go/no-go decision;
2. ATC conflict resolution;
3. autonomous separation recommendation;
4. maintenance release authorization;
5. safety-critical dispatch approval.

---

# 19. Statistical Analysis

## 19.1 Bootstrap Confidence Intervals

Report 95% confidence intervals for all main metrics.

## 19.2 Mixed-Effects Model

Estimate failure probability:

[
\text{logit}(P(\text{failure})) =
\beta_0 +
\beta_1 \text{AgentType} +
\beta_2 \text{TaskFamily} +
\beta_3 \text{RiskLevel} +
\beta_4 \text{ToolUse} +
\beta_5 \text{VerifierUse} +
u_{\text{model}} +
u_{\text{task}}
]

## 19.3 Calibration Analysis

Metrics:

1. expected calibration error;
2. reliability diagram;
3. overconfident failure rate.

## 19.4 Paired Comparisons

Compare:

1. direct vs RAG;
2. RAG vs RAG + verifier;
3. tool agent vs tool agent + verifier;
4. base model vs Aero-SFT;
5. Aero-SFT vs AeroSafety-DPO;
6. AeroSafety-DPO vs verifier-gated agent.

## 19.5 Output-Length Control

Evaluate open-ended hazard tasks under fixed top-3, top-5, top-10, and unconstrained output settings.

This directly prevents verbosity-driven score inflation.

---

# 20. Reproducibility Plan

The final submission should include:

1. task construction code;
2. evaluation scripts;
3. prompt templates;
4. tool specifications;
5. scoring scripts;
6. model output logs;
7. expert annotation guidelines;
8. task cards;
9. data documentation;
10. frozen test split;
11. archived code version.

The uploaded NMI article provides dataset and code availability statements and archives the code version, which is a useful standard to follow.

---

# 21. Revised Abstract Draft

Agentic artificial intelligence systems are increasingly being proposed for operational decision support, yet their reliability under safety-critical constraints remains poorly understood. Aviation provides a high-fidelity setting for studying this problem because operational decisions require evidence retrieval, temporal and spatial reasoning, rule compliance, numerical computation, tool use, optimization and risk-sensitive judgment. Here we systematically evaluate agentic AI systems across major aviation operations and safety workflows, including safety report analysis, accident reasoning, weather dispatch, NOTAM compliance, airport surface operations, air traffic separation, wake-vortex safety, maintenance release and optimization-integrated operational decisions. We develop an executable aviation evaluation environment that records agent actions, evidence use, tool calls, verification outcomes and final recommendations. Across frontier and open-source models, retrieval-augmented agents, tool-augmented agents, multi-agent systems, aviation-adapted models and verifier-gated agents, we find a persistent gap between task accuracy and operational safety. Retrieval improves evidence grounding but does not reliably prevent safety-constraint omissions; tool use improves local computation but introduces tool-selection and interpretation failures; and multi-agent collaboration increases explanation richness without consistently reducing unsafe recommendations. Domain adaptation improves aviation fluency and average task success, but high-severity failures remain. Verifier-gated architectures provide the strongest reduction in critical failures, suggesting that current agentic AI systems should be deployed, if at all, as human-supervised and independently verified decision-support systems rather than autonomous aviation decision-makers.

---

# 22. Most Important Revisions Compared with the Previous Proposal

## Revision 1: Add Structured + Scenario + Agentic Task Layers

The previous proposal had task families, but not enough internal task hierarchy. The revised version adds:

1. structured rule tasks;
2. passive hazard identification;
3. active consequence prediction;
4. operational decision tasks;
5. agentic tool-use tasks.

This mirrors the NMI article’s MCQ + HIT + CIT structure while extending it to agentic workflows.

## Revision 2: Add Output-Length-Controlled Evaluation

Verbose agents may appear safer because they list more hazards. This must be controlled.

## Revision 3: Add RAG Contextual Distraction Experiment

The uploaded NMI article found standard RAG could degrade performance; our aviation study should explicitly test naive RAG, domain-filtered RAG, constraint-aware RAG, and RAG + verifier.

## Revision 4: Add Expert Review and Human Baseline

For NMI, expert review and human baseline are not optional. They are essential for credibility.

## Revision 5: Add Mitigation Experiments

The project should not only say agents fail. It should test:

1. SFT;
2. DPO;
3. RAG;
4. tools;
5. multi-agent collaboration;
6. verifier-gated architecture.

## Revision 6: Make Verifier-Gated Agent the Main Mitigation Finding

The strongest expected paper claim should be:

**Independent verification, not model scale alone, is the most practical route to reducing high-severity failures in safety-critical aviation agentic AI.**

---

# 23. Final Central Claim

**Current agentic AI systems are not reliable enough for autonomous aviation safety-critical decision-making, even when equipped with retrieval, tools, multi-agent collaboration and domain adaptation. Their most serious failures arise from hidden safety-constraint omissions, evidence misuse, tool misinterpretation and overconfident unsafe recommendations. Verifier-gated architectures substantially reduce high-severity failures and provide the most promising near-term path for human-supervised aviation decision support.**
