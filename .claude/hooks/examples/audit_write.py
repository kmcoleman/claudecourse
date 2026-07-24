#!/usr/bin/env python3
"""PostToolUse audit logger — records every completed Write/Edit.

This is a copyable stub. To use it:
  1. Copy it up one level, into .claude/hooks/audit_write.py
  2. Wire it into .claude/settings.json as a PostToolUse hook that matches
     Write|Edit (see .claude/hooks/examples/settings.hooks.json for the shape).

A PostToolUse hook runs AFTER the tool succeeds, so it is the honest place for
an audit trail: it records writes that actually happened. It appends one JSON
line per event to audit/<quarter>.jsonl, giving you a tamper-evident record of
every change to a review artifact — whether or not anyone was watching the run.

Contract with Claude Code:
  - The completed tool call arrives as JSON on stdin (including tool_response).
  - This hook only records; it exits 0 and blocks nothing.
"""
import datetime
import json
import os
import sys

event = json.load(sys.stdin)                       # the PostToolUse event
tool_input = event.get("tool_input", {})

entry = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    ),
    "tool": event.get("tool_name"),                # "Write" or "Edit"
    "path": tool_input.get("file_path"),           # what was written
    "session_id": event.get("session_id"),         # which run did it
}

# Write into <project>/audit/<quarter>.jsonl. CLAUDE_PROJECT_DIR is set by
# Claude Code; MERIDIAN_QUARTER lets the same hook serve Q3, Q4, and beyond.
quarter = os.environ.get("MERIDIAN_QUARTER", "2026-Q3")
audit_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), "audit")
os.makedirs(audit_dir, exist_ok=True)

with open(os.path.join(audit_dir, f"{quarter}.jsonl"), "a") as log:
    log.write(json.dumps(entry) + "\n")

sys.exit(0)                                        # record only; never blocks
