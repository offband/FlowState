---
id: python-standards
uuid: 24ecda44-c02a-558b-806e-4db847a6db6b
type: runtime_object
title: Python Development Standards
tags:
  - python
  - cli
  - packaging
version: 1.0
created_at: 2026-05-09T00:00:00+00:00
updated_at: 2026-05-09T00:00:00+00:00
---

# Python Development Standards

Prefer simple, inspectable Python.

Use:

- Python 3.11+
- `pyproject.toml`
- `src/` package layout
- `argparse` for low-dependency CLIs unless richer UX is needed
- `pytest` for tests
- typed dataclasses for core value objects

Avoid:

- hidden global state
- network dependencies in core file operations
- framework-heavy abstractions before behavior is proven
- generated code that humans cannot comfortably inspect
