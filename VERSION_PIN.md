# A2A Version Pin (Omega Point)

**Submodule Integrity**: This directory contains the Agent-to-Agent communication layer.

To prevent accidental breakage from external library updates:

1. **If A2A is a git submodule**: Pin to a specific commit:
   ```bash
   git submodule update --init A2A
   cd A2A && git checkout <COMMIT_SHA>
   ```

2. **If A2A is vendored**: Document the expected commit/version in this file.

3. **Before updating**: Run integration tests and verify OpenClaw compatibility per `A2A/SKILL.md`.

**Current expectation**: A2A is part of the monorepo. Ensure changes are backward-compatible with the Sovereign/OpenClaw bridge.
