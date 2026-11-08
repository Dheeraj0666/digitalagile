"""AgentCore Runtime wrapper. Trusted-code POC only; not an untrusted-code service."""
from __future__ import annotations
import base64
import io
import os
import re
import tempfile
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from digitalagile.frontend_agent.engine import run_story
from digitalagile.frontend_agent.projects import prepare_new, prepare_existing
from digitalagile.frontend_agent.runner import TrustedProcessRunner
from digitalagile.frontend_agent.artifacts import export_project

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Invoke one frontend engineer against a brand-new or pre-reviewed public GitHub project."""
    if os.environ.get("AGENTCORE_ALLOW_TRUSTED_RUNNER") != "1":
        return {"status": "blocked", "reason": "Set AGENTCORE_ALLOW_TRUSTED_RUNNER=1 only after reviewing its POC security limitations"}
    story = payload.get("story") or payload.get("prompt")
    if not isinstance(story, str) or not 1 <= len(story.strip()) <= 12000:
        return {"status": "error", "reason": "story must be 1..12000 characters"}
    repo = payload.get("repo_url")
    if repo is not None and not isinstance(repo, str):
        return {"status": "error", "reason": "repo_url must be a string"}
    allow_install = payload.get("allow_network_install") is True
    with tempfile.TemporaryDirectory(prefix="digitalagile_") as tmp:
        root = Path(tmp) / "project"
        if repo:
            prepare_existing(root, repo)
        else:
            prepare_new(root)
        runner = TrustedProcessRunner(root, allow_network_install=allow_install)
        run = run_story(story, root, runner=runner, max_repairs=2)
        destination = Path(tmp) / "output.zip"
        export_project(root, destination)
        archive = destination.read_bytes()
        output = {
            "status": run.validation["status"],
            "validation": run.validation,
            "attempts": run.attempts,
            "summary": run.summary[-5000:],
            "warnings": ["Trusted-code POC. npm scripts are not isolated from this runtime."],
        }
        # Small generated apps can be returned and restored with scripts/decode_agentcore.py.
        # Never silently truncate. Large apps need a reviewed artifact store (e.g., S3).
        if len(archive) <= 700_000:
            output["artifact_zip_base64"] = base64.b64encode(archive).decode("ascii")
        else:
            output["artifact_error"] = "Output exceeds inline limit; configure an external artifact store"
        return output


if __name__ == "__main__":
    app.run()
