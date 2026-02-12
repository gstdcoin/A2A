# Importing this skill (GitHub / ClawHub / Convex)

If you see a **server error** when importing this repo as a skill (e.g. `githubImport:importGitHubSkill`), use the settings below. The importer must use **branch `master`** and run **install before** the entrypoint.

## For automated import (Convex / ClawHub / similar)

| Field | Value |
|-------|--------|
| **Repository** | `https://github.com/gstdcoin/A2A` |
| **Branch** | `master` (this repo has no `main` branch) |
| **Install (before run)** | `pip install -r requirements.txt && pip install -e .` |
| **Working directory** | Repo root (where `main.py` and `setup.py` are) |
| **Entrypoint** | `python3 main.py` |

## Why "Server Error" can happen

1. **Wrong branch** — If the importer uses `main`, the clone may fail or be empty. Always use **`master`**.
2. **Missing install step** — `main.py` needs the `mcp` package and the SDK. Run the install command from repo root before starting the entrypoint.
3. **Wrong working directory** — Entrypoint must run from repo root so `main.py` can find `python-sdk/` and `starter-kit/`.

## Quick test after clone

```bash
git clone -b master https://github.com/gstdcoin/A2A.git
cd A2A
pip install -r requirements.txt && pip install -e .
python3 main.py
```

If this works locally, the same branch + install + cwd + entrypoint should work in your import pipeline.
