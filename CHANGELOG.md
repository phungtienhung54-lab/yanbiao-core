# Changelog

## [1.1.0] - 2026-09-21
### Added
- Integrated GitHub Actions CI/CD pipeline with coverage gate (threshold 95%).
- Added 55 new boundary and exception test cases, total 101 tests.
### Changed
- Global test coverage increased from 76% to 99.78% (statements/branches).
- Optimized `semantic_gate.py` logic and removed dead code.
- Fixed PIF mock interference, floating-point precision assertions, and cross-platform line-ending issues.