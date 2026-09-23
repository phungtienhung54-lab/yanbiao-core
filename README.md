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
- **High Quality**: 130+ test cases, 99% coverage, GitHub Actions CI + Codecov.

## 🚀 Quick Start

### Install dependencies
```bash
pip install -r requirements.txt