"""Minimal audit/limit hooks. Actual security boundaries are in tools + container."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


def create_hooks(audit_path: Path, max_calls: int = 80):
    from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent, BeforeInvocationEvent

    class ToolAuditHooks(HookProvider):
        def __init__(self):
            self.calls = 0
            self.lock = Lock()

        def register_hooks(self, registry: HookRegistry) -> None:
            registry.add_callback(BeforeInvocationEvent, self.reset)
            registry.add_callback(BeforeToolCallEvent, self.before)
            registry.add_callback(AfterToolCallEvent, self.after)

        def reset(self, event: BeforeInvocationEvent) -> None:
            with self.lock:
                self.calls = 0

        def before(self, event: BeforeToolCallEvent) -> None:
            with self.lock:
                self.calls += 1
                allowed = self.calls <= max_calls
            if not allowed:
                event.cancel_tool = "Tool-call budget exhausted. Stop and report current results."

        def after(self, event: AfterToolCallEvent) -> None:
            # Never log content or tool inputs: they might contain sensitive source.
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": event.tool_use.get("name", "unknown"),
                "duration_s": event.duration,
                "tool_error": isinstance(event.result, Exception),
            }
            with self.lock:
                with audit_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")

    return ToolAuditHooks()
