"""Reusable service for CLI and AgentCore entrypoints."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from .hooks import create_hooks
from .models import create_model
from .runner import DockerRunner
from .tools import make_tools
from .workspace import Workspace

SOURCE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class AgentRun:
    summary: str
    validation: dict
    attempts: int
    errors: list[str]


def run_story(story: str, workspace_root: str | Path, *, allow_network_install: bool = False,
              runner=None, max_repairs: int = 3) -> AgentRun:
    """Invoke the single Strands agent and enforce validation+bounded repair externally."""
    if not story or not story.strip():
        raise ValueError("A non-empty story is required")
    project = Workspace(workspace_root)
    source = SOURCE_ROOT.resolve()
    if project.root == source or source.is_relative_to(project.root) or project.root.is_relative_to(source):
        raise ValueError("Generated project workspace must be outside the agent repository")
    from strands import Agent

    executor = runner if runner is not None else DockerRunner(project.root, allow_network_install=allow_network_install)
    if allow_network_install:
        installation = executor.run("install")
        if installation.get("status") != "passed":
            # Store as a blocker rather than asking the model to pretend installation succeeded.
            print(f"Dependency install status: {installation.get('status')} ({installation.get('reason', '')})")
    prompt = (SOURCE_ROOT / "prompts" / "frontend_engineer.md").read_text(encoding="utf-8")
    agent = Agent(
        model=create_model(),
        tools=make_tools(project, executor),
        system_prompt=prompt,
        hooks=[create_hooks(project.root.parent / "agent_audit.jsonl", max_calls=100)],
    )
    result_text = ""
    errors = []
    validation = {"status": "not_run"}
    for attempt in range(max_repairs + 1):
        if attempt == 0:
            request = f"User story:\n{story}\n\nCurrent repository inspection:\n{project.inspect()}\nImplement it in the workspace using tools."
        else:
            request = (
                "The external validation controller identified actual failures. "
                "Fix the relevant project files using the tools and rerun validation. "
                f"This is repair attempt {attempt} of {max_repairs}.\n"
                f"Failures: {errors[-1][-5000:]}"
            )
        response = agent(request)
        result_text = str(response)
        validation = executor.validate()
        if validation.get("status") == "passed":
            return AgentRun(result_text, validation, attempt + 1, errors)
        errors.append(str(validation)[:7000])
    return AgentRun(result_text, validation, max_repairs + 1, errors)
