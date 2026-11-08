"""Allowlisted frontend commands. Local builds are executed in a Docker sandbox."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

NODE_IMAGE = "node:22-bookworm-slim"
MAX_OUTPUT = 10000


def scripts_in(root: Path) -> dict:
    try:
        raw = json.loads((root / "package.json").read_text(encoding="utf-8"))
        scripts = raw.get("scripts", {})
        return scripts if isinstance(scripts, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def allowed_commands(action: str, *, has_package: bool, has_script: bool, allow_install: bool) -> list[list[str]] | dict:
    """Derive fixed argv, never directly evaluate arbitrary model-generated commands."""
    if action == "install":
        if not has_package:
            return {"status": "rejected", "reason": "Missing package.json"}
        if not allow_install:
            return {"status": "blocked", "reason": "Network install requires operator approval"}
        return [
            ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"],
            ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        ]
    if action in {"build", "lint", "test", "typecheck"}:
        if not has_script:
            return {"status": "skipped", "reason": f"No {action} script"}
        return [["npm", "run", action]]
    return {"status": "rejected", "reason": "Unapproved action"}


class DockerRunner:
    def __init__(self, root: Path, allow_network_install: bool = False, image: str = NODE_IMAGE):
        self.root = Path(root).resolve()
        self.allow_network_install = allow_network_install
        self.image = image

    def _docker_run(self, args: list[str], network: bool, timeout: int = 240) -> dict:
        if not shutil.which("docker"):
            return {"status": "unavailable", "reason": "Docker executable not found"}
        command = [
            "docker", "run", "--rm", "--init", "--network", "bridge" if network else "none",
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "128", "--memory", "1536m", "--cpus", "2",
            "--tmpfs", "/tmp:rw,nosuid,size=512m", "--env", "HOME=/tmp",
            "--env", "NPM_CONFIG_CACHE=/tmp/npm-cache",
            "--mount", f"type=bind,src={self.root},dst=/work",
            "--workdir", "/work",
        ]
        if hasattr(os, "getuid"):
            command += ["--user", f"{os.getuid()}:{os.getgid()}"]
        command += [self.image, *args]
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "reason": "Docker command exceeded time limit"}
        except OSError as exc:
            return {"status": "error", "reason": str(exc)}
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-MAX_OUTPUT:],
            "stderr": result.stderr[-MAX_OUTPUT:],
        }

    def run(self, action: str) -> dict:
        scripts = scripts_in(self.root)
        plan = allowed_commands(
            action, has_package=(self.root / "package.json").is_file(),
            has_script=action in scripts, allow_install=self.allow_network_install,
        )
        if isinstance(plan, dict):
            return {"action": action, **plan}
        for command in plan:
            step = self._docker_run(command, network=(action == "install"))
            if step.get("status") != "passed":
                return {"action": action, **step}
        return {"action": action, **step}

    def validate(self) -> dict:
        checks = {action: self.run(action) for action in ("build", "lint", "test", "typecheck")}
        valid = checks["build"]["status"] == "passed" and all(
            c["status"] in ("passed", "skipped") for c in checks.values()
        )
        return {"status": "passed" if valid else "failed", "checks": checks}


def git_diff(root: Path) -> dict:
    if not shutil.which("git"):
        return {"status": "unavailable", "reason": "Git executable not found"}
    commands = [
        ["git", "-C", str(root), "status", "--short"],
        ["git", "-C", str(root), "--no-pager", "diff", "--stat", "--"],
        ["git", "-C", str(root), "--no-pager", "diff", "--no-ext-diff", "--"],
    ]
    try:
        outputs = [subprocess.run(cmd, text=True, capture_output=True, timeout=15) for cmd in commands]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "reason": str(exc)}
    if any(p.returncode != 0 for p in outputs):
        return {"status": "no_git_repo", "files": [], "note": "Workspace is not a Git checkout"}
    return {"status": "ok", "status_short": outputs[0].stdout[-6000:],
            "diff_stat": outputs[1].stdout[-4000:], "diff": outputs[2].stdout[-14000:]}


class TrustedProcessRunner:
    """POC ONLY: executes npm in the agent's OS/container. Not an isolation boundary.

    Use only in a dedicated, disposable AgentCore container for explicitly trusted
    new projects or pre-reviewed repos. For production, replace this runner with
    an external isolated workspace service and network policies.
    """
    def __init__(self, root: Path, allow_network_install: bool = False):
        self.root = Path(root).resolve()
        self.allow_network_install = allow_network_install

    def run(self, action: str) -> dict:
        scripts = scripts_in(self.root)
        plan = allowed_commands(
            action, has_package=(self.root / "package.json").is_file(),
            has_script=action in scripts, allow_install=self.allow_network_install,
        )
        if isinstance(plan, dict):
            return {"action": action, **plan}
        # Do not forward AWS credentials, API keys, or arbitrary environment settings.
        env = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
               "HOME": "/tmp", "NPM_CONFIG_CACHE": "/tmp/digitalagile-npm-cache",
               "CI": "true"}
        for args in plan:
            try:
                proc = subprocess.run(args, cwd=self.root, capture_output=True, text=True,
                                      timeout=240, check=False, env=env)
            except (OSError, subprocess.TimeoutExpired) as exc:
                return {"action": action, "status": "error", "reason": str(exc)}
            if proc.returncode != 0:
                return {"action": action, "status": "failed", "exit_code": proc.returncode,
                        "stdout": proc.stdout[-MAX_OUTPUT:], "stderr": proc.stderr[-MAX_OUTPUT:]}
        return {"action": action, "status": "passed", "exit_code": 0,
                "stdout": proc.stdout[-MAX_OUTPUT:], "stderr": proc.stderr[-MAX_OUTPUT:]}

    def validate(self) -> dict:
        checks = {action: self.run(action) for action in ("build", "lint", "test", "typecheck")}
        ok = checks["build"]["status"] == "passed" and all(
            result["status"] in ("passed", "skipped") for result in checks.values()
        )
        return {"status": "passed" if ok else "failed", "checks": checks}
