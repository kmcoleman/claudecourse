"""Day 4 Cycle 5 checkpoint — the enforcement layer (hooks).

Two things get checked here:

  1. The copyable hook stubs the kit ships in .claude/hooks/examples/ actually
     work — the PreToolUse guard denies a secret-bearing write, and the
     PostToolUse audit logger appends a well-formed JSON line. These always run,
     because the stubs always ship.

  2. If the learner has wired hooks into .claude/settings.json (Cycle 5), that
     configuration is structurally valid and points at scripts that exist. This
     part self-skips on a fresh clone that hasn't reached Day 4 yet.

The stubs are the reference implementation: a learner who copies them and wires
them the way Cycle 5 describes ends up with exactly the behavior tested below.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / ".claude" / "hooks" / "examples"
GUARD = EXAMPLES / "secret_guard.py"
AUDIT = EXAMPLES / "audit_write.py"

SETTINGS = [
    ROOT / ".claude" / "settings.json",
    ROOT / ".claude" / "settings.local.json",
]


def _run_hook(script: Path, event: dict, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc


# --------------------------------------------------------------------------
# The shipped stubs — these are the reference implementation
# --------------------------------------------------------------------------

def test_guard_and_audit_stubs_ship():
    assert GUARD.exists(), (
        "The PreToolUse guard stub is missing from .claude/hooks/examples/. "
        "Day 4 Cycle 5 has learners copy and wire it."
    )
    assert AUDIT.exists(), (
        "The PostToolUse audit stub is missing from .claude/hooks/examples/."
    )


def test_guard_blocks_a_secret_bearing_write():
    """The canonical guardrail test: sk-fake-secret-12345 must be refused."""
    proc = _run_hook(GUARD, {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "findings.json",
            "content": 'rationale: token leaked here sk-fake-secret-12345',
        },
    })
    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny", (
        "The guard let a write containing sk-fake-secret-12345 through. A "
        "PreToolUse hook that returns permissionDecision 'deny' stops the write "
        "before it reaches disk — that is the whole point of the guardrail."
    )


def test_guard_also_covers_edit_new_string():
    """Edit puts the new text in new_string, not content — cover both."""
    proc = _run_hook(GUARD, {
        "tool_name": "Edit",
        "tool_input": {"file_path": "x", "new_string": "Authorization: Bearer abc123"},
    })
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_guard_allows_an_ordinary_write():
    """A clean write must pass silently — no false positives on real findings."""
    proc = _run_hook(GUARD, {
        "tool_name": "Write",
        "tool_input": {"file_path": "findings.json", "content": "category: sod_conflict"},
    })
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "", (
        "The guard blocked an ordinary finding. It should stay silent (allow) "
        "unless it actually matches a secret pattern."
    )


def test_audit_appends_a_wellformed_line(tmp_path):
    proc = _run_hook(
        AUDIT,
        {
            "tool_name": "Write",
            "session_id": "sess-test",
            "tool_input": {"file_path": "findings.json"},
            "tool_response": {},
        },
        env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path), "MERIDIAN_QUARTER": "2026-Q3"},
    )
    assert proc.returncode == 0, proc.stderr

    log = tmp_path / "audit" / "2026-Q3.jsonl"
    assert log.exists(), "The audit hook did not create audit/2026-Q3.jsonl."

    lines = [ln for ln in log.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1, "The audit hook should append exactly one line per write."
    entry = json.loads(lines[0])
    assert set(entry) == {"ts", "tool", "path", "session_id"}, (
        f"Each audit line needs ts, tool, path, session_id — got {sorted(entry)}."
    )
    assert entry["tool"] == "Write" and entry["path"] == "findings.json"
    assert entry["ts"].endswith("Z"), "Timestamps should be UTC (…Z)."


def test_audit_is_append_only(tmp_path):
    """A second write must add a line, not overwrite the first."""
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "MERIDIAN_QUARTER": "2026-Q3"}
    for path in ("findings.json", "exemptions.json"):
        _run_hook(AUDIT, {
            "tool_name": "Write", "session_id": "s",
            "tool_input": {"file_path": path},
        }, env_extra=env)
    log = tmp_path / "audit" / "2026-Q3.jsonl"
    lines = [ln for ln in log.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2, "The audit log must be append-only, one line per write."


# --------------------------------------------------------------------------
# The learner's own wiring — self-skips until Day 4 Cycle 5 is done
# --------------------------------------------------------------------------

def _configured_hooks():
    for path in SETTINGS:
        if not path.exists():
            continue
        try:
            cfg = json.loads(path.read_text())
        except json.JSONDecodeError:
            pytest.fail(f"{path.name} is not valid JSON — Claude Code cannot load it.")
        if isinstance(cfg.get("hooks"), dict) and cfg["hooks"]:
            return path, cfg["hooks"]
    return None, None


def test_learner_hook_config_is_valid_if_present():
    path, hooks = _configured_hooks()
    if hooks is None:
        pytest.skip(
            "No hooks configured in .claude/settings.json yet. Work through "
            "Day 4 Cycle 5 to add the PreToolUse guard and PostToolUse audit."
        )

    for event in ("PreToolUse", "PostToolUse"):
        assert event in hooks, (
            f"{path.name} defines hooks but no {event} entry. Cycle 5 wires a "
            "PreToolUse guard and a PostToolUse audit."
        )
        groups = hooks[event]
        assert isinstance(groups, list) and groups, f"{event} must be a non-empty list."
        for group in groups:
            assert "Write" in group.get("matcher", "") or "Edit" in group.get("matcher", ""), (
                f"The {event} matcher should target Write|Edit, got "
                f"{group.get('matcher')!r}."
            )
            for handler in group.get("hooks", []):
                assert handler.get("type") == "command", (
                    f"{event} handler needs type 'command'."
                )
                assert handler.get("command"), f"{event} handler needs a command."
