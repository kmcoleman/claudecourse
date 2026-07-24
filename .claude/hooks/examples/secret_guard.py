#!/usr/bin/env python3
"""PreToolUse secret guard — refuses a Write/Edit whose content carries a secret.

This is a copyable stub. To use it:
  1. Copy it up one level, into .claude/hooks/secret_guard.py
  2. Wire it into .claude/settings.json as a PreToolUse hook that matches
     Write|Edit (see .claude/hooks/examples/settings.hooks.json for the shape).

Because a PreToolUse hook runs BEFORE the tool executes, denying here means the
write never lands on disk. (A PostToolUse hook cannot do this — by the time it
runs, the file is already written. Prevention belongs in PreToolUse.)

Contract with Claude Code:
  - The pending tool call arrives as JSON on stdin.
  - Print a permissionDecision of "deny" (exit 0) to block the call, or stay
    silent (exit 0) to let the normal permission flow proceed.
"""
import json
import re
import sys

# Patterns that must never be written into a review artifact. Extend this list
# with anything specific to your engagement (internal token prefixes, etc.).
SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]",        # API-key style tokens, e.g. sk-fake-secret-12345
    r"ANTHROPIC_API_KEY",     # a named credential env var
    r"password:",             # a password field in YAML/JSON/text
    r"Bearer ",               # an Authorization: Bearer <token> header
]

event = json.load(sys.stdin)                       # the PreToolUse event
tool_input = event.get("tool_input", {})

# Write carries the body in "content"; Edit carries it in "new_string".
# Join whatever is present so one guard covers both tools.
pending_text = " ".join(
    str(tool_input.get(field, "")) for field in ("content", "new_string")
)

for pattern in SECRET_PATTERNS:
    if re.search(pattern, pending_text):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"secret-guard: matched /{pattern}/ in the pending write "
                    "to {}; refused before it reached disk.".format(
                        tool_input.get("file_path", "the target file")
                    )
                ),
            }
        }))
        sys.exit(0)                                # deny and stop

sys.exit(0)                                        # no match -> allow normally
