"""Scoped, mostly read-only metadata and controlled file edits for one project.

Not a substitute for OS/container isolation. The workspace should be owned by
one run and should not be concurrently modified by an untrusted process.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

BLOCKED_DIRS = {".git", ".aws", ".ssh", ".venv", "node_modules", "dist", "build", ".next", "coverage"}
BLOCKED_FILES = {".npmrc", ".pypirc", "id_rsa", "credentials", "config.json"}
MAX_READ_BYTES = 100_000
MAX_WRITE_BYTES = 200_000


class WorkspaceError(ValueError):
    pass


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise WorkspaceError("Workspace root must be an existing directory")

    def path(self, relative_path: str) -> Path:
        if not relative_path or not isinstance(relative_path, str):
            raise WorkspaceError("A relative path is required")
        requested = Path(relative_path)
        if requested.is_absolute() or any(p in ("..", "") for p in requested.parts):
            raise WorkspaceError("Absolute and traversal paths are prohibited")
        for part in requested.parts:
            low = part.lower()
            if low in BLOCKED_DIRS or low in BLOCKED_FILES or low.startswith(".env"):
                raise WorkspaceError("Restricted path")
            if low.endswith((".pem", ".key", ".p12", ".pfx")):
                raise WorkspaceError("Sensitive file extension")
        actual = (self.root / requested).resolve()
        if not actual.is_relative_to(self.root):
            raise WorkspaceError("Path escapes workspace, including via symlink")
        return actual

    def list_files(self, limit: int = 120) -> list[str]:
        entries: list[str] = []
        for folder, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in BLOCKED_DIRS and not (Path(folder) / d).is_symlink())
            for filename in sorted(files):
                path = Path(folder) / filename
                rel = path.relative_to(self.root).as_posix()
                try:
                    self.path(rel)
                except WorkspaceError:
                    continue
                entries.append(rel)
                if len(entries) >= limit:
                    return entries
        return entries

    def inspect(self) -> dict:
        package_file = self.root / "package.json"
        if not package_file.is_file() or package_file.is_symlink():
            return {"status": "new_or_unknown_project", "files": self.list_files()}
        try:
            package = json.loads(package_file.read_text(encoding="utf-8"))
            deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        except (OSError, ValueError, TypeError) as e:
            return {"status": "invalid_package_json", "error": str(e)}
        if "@angular/core" in deps:
            framework = "Angular"
        elif "next" in deps:
            framework = "Next.js"
        elif "react" in deps:
            framework = "React"
        elif "vue" in deps:
            framework = "Vue"
        else:
            framework = "unknown"
        manager = next((m for f, m in (
            ("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
            ("package-lock.json", "npm")) if (self.root / f).exists()), "unknown")
        return {
            "status": "detected", "framework": framework,
            "language": "TypeScript" if (self.root / "tsconfig.json").exists() else "unknown",
            "package_manager": manager,
            "scripts": package.get("scripts", {}),
            "files": self.list_files(),
        }

    def read(self, relative_path: str) -> dict:
        path = self.path(relative_path)
        if not path.is_file():
            raise WorkspaceError("File not found")
        if path.stat().st_size > MAX_READ_BYTES:
            raise WorkspaceError("File too large for one read")
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError) as e:
            raise WorkspaceError("Not a readable UTF-8 text file") from e
        return {"path": relative_path, "content": content}

    def write(self, relative_path: str, content: str, overwrite: bool = False) -> dict:
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            raise WorkspaceError("Invalid or oversized content")
        target = self.path(relative_path)
        if target.exists() and not overwrite:
            raise WorkspaceError("File exists; explicit overwrite required")
        if target.exists() and (target.is_dir() or target.is_symlink()):
            raise WorkspaceError("Cannot replace directory or symlink")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Recheck after creating parents. Isolation and no concurrent untrusted access remain required.
        target = self.path(relative_path)
        if target.is_symlink():
            raise WorkspaceError("Symlink replacement prohibited")
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as tmp:
                temp_name = tmp.name
                tmp.write(content)
            os.replace(temp_name, target)
        finally:
            if temp_name and Path(temp_name).exists():
                Path(temp_name).unlink()
        return {"status": "written", "path": relative_path, "bytes": len(content.encode("utf-8"))}
