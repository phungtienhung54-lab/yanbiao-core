# yanbiao-core
A human‑in‑the‑loop sharded memory architecture to mitigate concept‑drift for long‑context LLM, based on the Yanbiao Theory.
# yanbiao-core

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
- **High Quality**: 101 test cases, 99.78% coverage, GitHub Actions CI.

## 🚀 Quick Start

### Install dependencies
```bash
pip install -r requirements.txt

## 📊 Performance Benchmarks

Measured on Windows 11, Python 3.12.3, JSON file storage.

| Benchmark | Scale | Time |
|---|---|---|
| Belief query | 1,000 entries | 0.60 ms |
| Fact query | 1,000 entries | 0.47 ms |
| Concurrent belief registration | 100 threads | 49.33 ms |
| Concurrent sandbox creation | 50 threads | passed |
| Bulk cross-validation | 500 facts | 627 ms |

> Note: Cross-validation time is dominated by per-fact JSON file writes (~1.25 ms per validation). Batch writes or SQLite storage is planned for V1.2.

## 📄 License

This project is licensed under the [MIT](LICENSE) license.