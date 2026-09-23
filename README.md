# yanbiao-core

[![Run Tests](https://github.com/phungtienhung54-lab/yanbiao-core/actions/workflows/test.yml/badge.svg)](https://github.com/phungtienhung54-lab/yanbiao-core/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/phungtienhung54-lab/yanbiao-core/branch/main/graph/badge.svg)](https://codecov.io/gh/phungtienhung54-lab/yanbiao-core)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A human-in-the-loop sharded memory architecture to mitigate concept-drift for long-context LLM, based on the Yanbiao Theory.

## ✨ Features
- **Sharded Memory Architecture**: Layer 0 Core Protocol / Layer 1 Fact Engine / Layer 2 Belief System / Layer 3 Sandbox Engine.
- **User Isolation**: Beliefs are strictly isolated per user and per session; no cross-talk.
- **Fact Verification**: PIF guard (subjective opinion filtering) and cross-validation.
- **Creative Sandbox**: Supports fictional reality deduction with automatic disclaimers and concept-swap protection.
- **High Quality**: 168+ test cases, 99% coverage, GitHub Actions CI + Codecov.
- **Audit Trail**: Every fact/belief/orchestrator/sandbox operation is logged.
- **Dual Backend Storage**: JSON for lightweight scenarios, SQLite for high-performance batch operations (up to 35x faster).

## 🚀 Quick Start

### Install dependencies
- `pip install -r requirements.txt`

### Run tests
- `pytest tests/ --cov=core --cov=orchestrator --cov-branch --cov-report=term-missing`

### Enable SQLite backend (optional)
- `from core.fact_engine import FactEngine`
- `engine = FactEngine("./data", use_sqlite=True)`
- `engine.cross_validate_batch(fact_ids, "source_A")`

## 📊 Performance Benchmarks

| Benchmark | Scale | Time |
|---|---|---|
| Belief query | 1,000 entries | 1.10 ms |
| Fact query | 1,000 entries | 0.90 ms |
| Concurrent belief registration | 100 threads | 89.78 ms |
| Concurrent sandbox creation | 50 threads | passed |

### Storage Backend Comparison

| Operation | JSON | SQLite (single) | SQLite (batch) |
|---|---|---|---|
| 500 facts cross-validation | 586.67 ms | 131.33 ms | 16.66 ms |
| Speedup | 1x | 4.5x | 35x+ |

## 📄 License

This project is licensed under the [MIT](LICENSE) license.