# Changelog

## [1.2.0-dev] - 2026-09-23
### Added
- **Audit Log module** (`core/audit_log.py`): JSONL-based append-only audit trail with full change history.
- Audit integration in `FactEngine`: register and cross_validate operations are now traceable.
- Audit integration in `BeliefEngine`: register and weight adjustment operations are now traceable.
- Full-chain audit in `YanbiaoCore.process`: every message processing leaves an orchestrator audit record.
- `get_system_state()` now returns audit statistics.
- 20 new tests in `tests/test_audit.py`, 2 new tests in `tests/test_integration.py`.

### Changed
- `FactEngine` and `BeliefEngine` constructors accept optional `audit_log` parameter (backward compatible).
- Test suite expanded from 133 to 155 tests.

### Coverage
- `core/audit_log.py`: 100%
- `core/fact_engine.py`: 100%
- `core/belief_engine.py`: 100%
- Global: 99%

## [1.1.0] - 2026-09-21
### Added
- Integrated GitHub Actions CI/CD pipeline with coverage gate (threshold 95%).
- Added 55 new boundary and exception test cases, total 101 tests.
### Changed
- Global test coverage increased from 76% to 99.78% (statements/branches).
- Optimized `semantic_gate.py` logic and removed dead code.
- Fixed PIF mock interference, floating-point precision assertions, and cross-platform line-ending issues.