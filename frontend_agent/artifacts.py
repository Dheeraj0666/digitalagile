"""Create a portable archive and report of generated code. Skip secrets and build artifacts."""
from __future__ import annotations
import json
import zipfile
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", ".aws", ".ssh", "dist", "build", "coverage", ".next"}
SKIP_NAMES = {".npmrc", ".pypirc", "id_rsa", "agent_audit.jsonl"}


def safe_source(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if path.is_symlink() or not path.is_file():
        return False
    return not any(part in SKIP_DIRS or part in SKIP_NAMES or part.startswith(".env")
                   or part.endswith((".pem", ".key", ".p12", ".pfx")) for part in rel.parts)


def export_project(project_root: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(project_root.rglob("*")):
            if safe_source(path, project_root):
                zf.write(path, arcname=path.relative_to(project_root).as_posix())
    return destination


def write_report(destination: Path, *, story: str, validation: dict, attempts: int,
                 project_root: Path, agent_result: str, errors: list[str]):
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "story": story,
        "project_root": str(project_root),
        "validation": validation,
        "attempts": attempts,
        "agent_summary": agent_result[-8000:],
        "errors": errors,
    }
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return destination
