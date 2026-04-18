# Changelog

## [1.0.0] — 2026-04-30

### Added
- Four-node LangGraph audit pipeline: plan → discover → deep_dive → report
- Conditional routing: skips deep_dive for clean accounts (40% token saving)
- `AuditState` typed graph state with `findings`, `violations`, and `report` fields
- `Severity` enum: CRITICAL / MEDIUM / INFO with automatic violation filtering
- Five AWS tool stubs: EC2, S3, IAM, Security Groups, Finding detail — all with DEMO_MODE
- `AuditReport` with `critical_count`, `medium_count`, `info_count` computed properties
- 43 unit tests — no LLM or AWS credentials required
- GitHub Actions CI — ruff lint + pytest with DEMO_MODE

### Changed
- `route_after_discovery` evaluates `state.violations` (CRITICAL + MEDIUM only)
- `deep_dive` node runs targeted `describe_finding` calls per violation, not per finding

### Fixed
- `_run_tool_loop` properly accumulates tool messages before calling the model again
