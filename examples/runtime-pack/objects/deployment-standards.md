---
id: deployment-standards
uuid: 1fccf9b6-3c5b-5a42-af0b-c107366550f3
type: runtime_object
title: Deployment Standards
tags:
  - deployment
  - release
version: 1.0
created_at: 2026-05-09T00:00:00+00:00
updated_at: 2026-05-09T00:00:00+00:00
---

# Deployment Standards

Deployment behavior should be explicit and reversible.

Before release:

- run tests
- verify package metadata
- confirm install path
- document environment variables
- avoid embedding private secrets in repo artifacts

For local runtime systems:

- keep runtime state under the configured runtime home
- keep project repos lightweight
- make bootstrap files safe to commit
- document how to rotate credentials
