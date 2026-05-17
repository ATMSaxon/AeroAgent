# PR: Phase 1 Foundation — AeroSafetyEval scaffolding, data, tools, agents, evaluation

**Branch:** `feat/initial-scaffolding-and-docs` → `main`
**Commits:** 10
**Tests:** 353 / 353 passing
**Open URL:** https://github.com/ATMSaxon/AeroAgent/compare/main...feat/initial-scaffolding-and-docs?expand=1

---

## Summary

This PR lands the executable foundation for **AeroSafetyEval**, the research environment supporting the NMI-targeted study of agentic AI reliability in aviation safety-critical decision-making. Five workstreams shipped in parallel by a team of specialised agents (infra, data, tools, agents, evaluation), then hardened by a unified integration-test pass that surfaced 11 cross-module bugs (all fixed).

Nothing in this PR fabricates data, ships fake implementations, or makes safety claims beyond what the code can support. All MOCK/PARTIAL/NOT IMPLEMENTED states are explicit per `CLAUDE.md` §1.2.

## What's in this PR

### 1. Project infrastructure (`aerosafety/`)
- Pydantic v2 shared schemas: `TaskCard`, `AgentTrace`, `ToolCall`, `RetrievedDoc`, `Recommendation`, `TaskProvenance`.
- `ExperimentLogger` (JSONL, mode="x", raises on `run_id` mismatch — no silent overrides per CLAUDE.md §8.1).
- `determinism.py`: `lock_seeds()`, `prompt_hash()`, `assert_eval_mode()`.
- `config/`: frozen YAML configs with model registry.
- `pyproject.toml` with deps declared, none auto-installed.

### 2. Aviation data foundation (`aerosafety/data/`)
- **9-branch aviation safety taxonomy** with subtopics, regulatory grounding, KP seeds.
- **22-source registry** (`source_registry.yaml` v1.2.0) with `residency_restriction`, `requires_user_action`, `critical_path`, `alternative_source_id`, `substitute_source` fields.
- **8 sources enabled for Phase 1 pilot, all globally public (no US-resident gating):** NASA ASRS, NTSB CAROL + full reports, Iowa State Mesonet METAR + TAF (replaces aviationweather.gov), FAA published docs (JO 7110.65, JO 7930.2, AIM, AC subset), eCFR Title 14 Parts 91 + 121, EUROCONTROL RECAT.
- **Downloader scripts** (dry-run only) with sha256 manifests, rate limits, no silent failure.
- **Domain schemas**: `KnowledgePoint` (7 fields per proposal §9.3), `Provenance`, `RawDocument`, `ManifestEntry`.

### 3. Aviation tools (`aerosafety/tools/`) — 10 deterministic tools
| Tool | Standard cited |
|---|---|
| `metar_parser` | WMO No. 306 FM 15-XVI |
| `taf_parser` | WMO No. 306 FM 51-XVI |
| `wind_component` | FAA-H-8083-25C Ch. 5 |
| `notam_parser` | ICAO Annex 15 + FAA JO 7930.2 |
| `time_window_checker` | ICAO Annex 15 §3.6, UTC-only |
| `separation_calculator` | FAA JO 7110.65Z + haversine |
| `wake_category_checker` | ICAO Doc 8643 (verified entries only) |
| `mel_checker` | **MOCK** — real MEL is proprietary |
| `weather_minima_checker` | FAA AIM §5-4-7 |
| `registry` | OpenAI + Anthropic function-calling schemas |

Plus `call_tool()` dispatcher producing `io.ToolCall` records with timing + structured logging.

### 4. Agent systems (`aerosafety/agents/`) — Systems 1-4 + 7
- `system1_direct.py` — Direct LLM baseline
- `system2_rag.py` — RAG with pluggable retriever (BM25 default; naive + constraint-aware variants); guards against empty corpus
- `system3_tool_aug.py` — Tool-augmented agent; validates every tool output before use per CLAUDE.md §8.3
- `system4_multi_agent.py` — Role-specialised pipeline (ops analyst → safety officer → regulation specialist → tool agent → final decision)
- `system7_verifier_gated.py` — wraps System 3 with 6 **independent** verifier modules (evidence, rule, numerical, tool-use, safety-constraint, escalation) per CLAUDE.md §6.3
- `system5_aero_sft.py` + `system6_aero_dpo.py` — `NotImplementedError("Phase 2: requires GPU training")` stubs, no placeholder outputs

All agents emit complete `AgentTrace` records (model_version, prompt_hash, tool_calls, retrieved_docs, recommendation, confidence, escalation, runtime, tokens, hardware, failure flags). `MockLLM` deterministic-for-tests; no real API calls during implementation.

### 5. Evaluation framework (`aerosafety/eval/`) — 10 metrics per proposal §12
TSR, SVR, SCOR, Evidence Faithfulness (4 sub-rates), Tool-Use Reliability (5 sub-rates), CCS (LLM-judge framework with MockJudge; real judge marked PARTIAL IMPLEMENTATION), OFR, SWFR (Low=1, Medium=3, High=5, Critical=10), CASS, Length-Controlled hazard recall (top-3/5/10/unconstrained).

Plus:
- `failure_taxonomy.py` — 7 FailureCategory + 35 FailureMode enums (proposal §14)
- `statistics.py` — seeded 1000-resample bootstrap CI, Wilcoxon paired test, mixed-effects logistic spec, ECE + calibration data
- `reporting.py` — per-task JSONL preserving every failure (CLAUDE.md §3.3), markdown summary
- `runner.py` — `EvalRunner` with `assert_eval_mode()` guard

### 6. Governance docs (`docs/`)
- `expert_review_protocol.md` v0.1 — **non-negotiable for NMI** per CLAUDE.md §3.4. Reviewer eligibility matrix, IAA targets (Cohen's κ, Krippendorff's α, Jaccard), adjudication, frozen-test-split protection, IRB submission path, 5 PI action items.

## What's NOT in this PR (next steps)

- **T6** — NOTAM compliance pilot task family
- **T7** — Weather/Dispatch pilot task family
- **T8** — Integration smoke test (needs API key + cost cap)
- **Real data downloads** — all sources are `enabled: true` but downloaders remain dry-run-only until a dedicated download task is opened
- **Phase 2** — SFT / DPO / Verifier training (needs GPU)

## How to validate locally

```bash
python3 -m venv .venv
.venv/bin/pip install pyyaml pydantic polars structlog psutil pytest pytest-asyncio rank_bm25 statsmodels httpx
AEROSAFETY_EVAL_MODE=1 .venv/bin/python -m pytest tests/ -q
# expected: 353 passed
```

## Reviewer checklist

- [ ] All 10 commits have clean conventional-commit messages
- [ ] No fabricated data, no fake implementations, no overclaim
- [ ] MOCK / NOT IMPLEMENTED markers present where applicable
- [ ] Source registry: every entry has `residency_restriction`
- [ ] No US-resident-gated sources on the critical path
- [ ] `expert_review_protocol.md` reflects the PI's institutional context (will need IRB submission)
- [ ] 353/353 tests pass on a fresh checkout

🤖 Generated with [Claude Code](https://claude.com/claude-code)
