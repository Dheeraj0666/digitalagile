"""Launch a Strands frontend engineer against a supplied disposable workspace.

Requires installed strands-agents, Docker, AWS Bedrock access for a real run.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .hooks import create_hooks
from .runner import DockerRunner
from .tools import make_tools
from .workspace import Workspace


def main():
    parser = argparse.ArgumentParser(description="Digital Agile Frontend Engineer POC")
    parser.add_argument("--workspace", required=True, help="An EXISTING project directory, separate from this agent code")
    parser.add_argument("--story", required=True, help="Business requirement or user story")
    parser.add_argument("--allow-network-install", action="store_true", help="Explicitly allow npm ci with Docker network access")
    args = parser.parse_args()

    project = Workspace(args.workspace)
    source_root = Path(__file__).resolve().parents[1]
    if project.root == source_root or source_root.is_relative_to(project.root) or project.root.is_relative_to(source_root):
        raise SystemExit("Workspace must be separate from the agent source repository")

    from strands import Agent
    from strands.models import BedrockModel

    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if not model_id:
        raise SystemExit("Set BEDROCK_MODEL_ID to an approved accessible Bedrock model ID")
    region = os.environ.get("AWS_REGION", "us-east-1")
    runner = DockerRunner(project.root, allow_network_install=args.allow_network_install)
    prompt = (source_root / "prompts" / "frontend_engineer.md").read_text(encoding="utf-8")
    audit_path = source_root / "agent_audit.jsonl"
    agent = Agent(
        model=BedrockModel(model_id=model_id, region_name=region),
        tools=make_tools(project, runner),
        system_prompt=prompt,
        hooks=[create_hooks(audit_path, max_calls=80)],
        callback_handler=None,
    )
    result = agent(args.story)
    print(result)


if __name__ == "__main__":
    main()
