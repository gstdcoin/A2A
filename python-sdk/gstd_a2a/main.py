#!/usr/bin/env python3
"""
🦾 GSTD A2A — Точка входа для автономного агента

Запуск:
    python3 -m gstd_a2a.main

Или после установки:
    cd A2A && pip install -e . && python3 -m gstd_a2a.main
"""
import os

# Load A2A/.env if present
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from .agent import Agent

def run():
    """Entry point for console_scripts."""
    Agent.run()

if __name__ == "__main__":
    run()
