"""Metadata-only Strands hooks. The tool adapters are the actual security controls."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


def create_hooks(audit_path: Path, max_calls: int = 90):
    from strands.hooks import (
        HookProvider, HookRegistry, BeforeToolCallEvent,
        AfterToolCallEvent, BeforeInvocationEvent,
    )

    class ToolBudgetAudit(HookProvider):
        def __init__(self):
            self.calls = 0
            self.lock = Lock()
            audit_path.parent.mkdir(parents=True, exist_ok=True)

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
                if self.calls > max_calls:
                    event.cancel_tool = "Tool budget exhausted; stop and report status."

        def after(self, event: AfterToolCallEvent) -> None:
            # No user story, source code, tool arguments, stdout or credentials in audit logs.
            tool_use = event.tool_use
            tool_name = tool_use.get("name", "unknown") if isinstance(tool_use, dict) else getattr(tool_use, "name", "unknown")
            entry = {"at": datetime.now(timezone.utc).isoformat(), "tool": tool_name,
                     "error": bool(getattr(event, "exception", None))}
            with self.lock:
                with audit_path.open("a", encoding="utf-8") as target:
                    target.write(json.dumps(entry) + "\n")

    return ToolBudgetAudit()
