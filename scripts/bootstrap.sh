#!/usr/bin/env bash
# Secondary fallback for macOS/Linux. Windows (bootstrap.ps1) is the supported path.
set -euo pipefail
command -v python3 >/dev/null || { echo "install Python 3.11+ first"; exit 1; }
command -v git >/dev/null || { echo "install Git first"; exit 1; }
# Node is optional: it's only used to install the Claude Code CLI below. The
# Python kit (venv, deps, generator, pytest) needs none of it, so a missing
# Node warns and skips rather than blocking setup.
if command -v node >/dev/null && command -v npm >/dev/null; then
  npm install -g @anthropic-ai/claude-code || true
else
  echo "[warn] Node/npm not found — skipping Claude Code CLI install."
  echo "       Install Node LTS + 'npm i -g @anthropic-ai/claude-code' later if you want the CLI."
fi
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
[ -f .env ] || cp .env.example .env
if grep -q '^ANTHROPIC_API_KEY=.\+' .env; then
  export ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)"
  ./.venv/bin/python -m pytest -q
  echo "== READY: environment green (including live API) =="
else
  ./.venv/bin/python -m pytest -m "not api" -q
  echo "== Offline checks green. Add ANTHROPIC_API_KEY to .env and re-run. =="
fi
