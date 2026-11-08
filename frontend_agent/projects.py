"""Prepare an isolated frontend working directory for a single agent run."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates" / "react-ts"


class ProjectPreparationError(ValueError):
    pass


def prepare_new(destination: str | Path) -> Path:
    """Copy neutral React/TS scaffolding into a new, empty target directory."""
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ProjectPreparationError("New project destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_ROOT, destination, dirs_exist_ok=True)
    return destination


def prepare_existing(destination: str | Path, repo_url: str) -> Path:
    """Clone a public GitHub repository. No credentials, ssh, or file:// schemes."""
    parsed = urlsplit(repo_url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ProjectPreparationError("Only HTTPS github.com repository URLs are supported in this POC")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise ProjectPreparationError("Repository URL contains unsupported parameters or credentials")
    segments = [s for s in parsed.path.strip("/").removesuffix(".git").split("/") if s]
    if len(segments) != 2 or not all(seg.replace("-", "").replace("_", "").isalnum() for seg in segments):
        raise ProjectPreparationError("Repository URL must be https://github.com/OWNER/REPO")
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ProjectPreparationError("Clone destination must be empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canonical = f"https://github.com/{segments[0]}/{segments[1]}.git"
    cmd = ["git", "-c", "protocol.file.allow=never", "clone", "--depth", "1", "--", canonical, str(destination)]
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""),
           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProjectPreparationError(f"Git clone could not be completed: {exc}") from exc
    if proc.returncode != 0:
        raise ProjectPreparationError("Clone failed. Check repository access and URL")
    return destination
