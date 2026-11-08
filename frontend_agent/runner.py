"""Constrained npm operations inside Docker; never execute generated code on host.

The default is network-off. npm installation requiring internet must be enabled
explicitly in a disposable development environment, not on sensitive repos.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class DockerRunner:
    ACTION_TO_COMMAND = {
        "install": ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        "build": ["npm", "run", "build"],
        "lint": ["npm", "run", "lint"],
        "test": ["npm", "test", "--", "--run"],
    }

    def __init__(self, root: Path, allow_network_install: bool = False, image: str = "node:22-bookworm-slim"):
        self.root = root.resolve()
        self.allow_network_install = allow_network_install
        self.image = image

    def run(self, action: str) -> dict:
        if action not in self.ACTION_TO_COMMAND:
            return {"status": "rejected", "error": "Only install/build/lint/test actions are permitted"}
        if not shutil.which("docker"):
            return {"status": "unavailable", "error": "Docker is required for command execution"}
        if action == "install":
            if not (self.root / "package-lock.json").is_file():
                return {"status": "rejected", "error": "npm ci requires package-lock.json"}
            if not self.allow_network_install:
                return {"status": "rejected", "error": "Dependency installation needs explicit opt-in for network access"}
        else:
            import json
            try:
                scripts = json.loads((self.root / "package.json").read_text()).get("scripts", {})
            except (OSError, ValueError):
                return {"status": "rejected", "error": "Missing or invalid package.json"}
            if action not in scripts:
                return {"status": "skipped", "reason": f"No {action} script"}

        command = [
            "docker", "run", "--rm", "--init", "--network",
            "bridge" if action == "install" and self.allow_network_install else "none",
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "128", "--memory", "1024m", "--cpus", "2",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--tmpfs", "/tmp:rw,nosuid,size=256m",
            "--env", "HOME=/tmp", "--env", "NPM_CONFIG_CACHE=/tmp/npm-cache",
            "--mount", f"type=bind,src={self.root},dst=/work", "--workdir", "/work",
            self.image, *self.ACTION_TO_COMMAND[action],
        ]
        try:
            proc = subprocess.run(command, text=True, capture_output=True, timeout=180, check=False)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "action": action, "timeout_seconds": 180}
        except OSError as e:
            return {"status": "error", "error": str(e)}
        return {
            "status": "passed" if proc.returncode == 0 else "failed",
            "action": action, "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]
        }


def git_diff(root: Path) -> dict:
    # Safe, read-only commands without a shell. Untracked files appear in status.
    if not shutil.which("git"):
        return {"status": "unavailable", "error": "Git not installed"}
    checks = [
        ["git", "-C", str(root), "status", "--short"],
        ["git", "-C", str(root), "--no-pager", "diff", "--no-ext-diff", "--"],
    ]
    outputs = [subprocess.run(args, text=True, capture_output=True, timeout=10) for args in checks]
    if any(p.returncode != 0 for p in outputs):
        return {"status": "error", "error": outputs[0].stderr or outputs[1].stderr}
    return {"status": "ok", "files": outputs[0].stdout[-6000:], "diff": outputs[1].stdout[-14000:]}
