"""Exactly six Strands tools; the agent cannot run arbitrary shell or fetch secrets."""
from .workspace import WorkspaceError
from .runner import git_diff as local_git_diff


def make_tools(workspace, runner, *, remote: bool = False):
    from strands import tool

    @tool
    def inspect_repo() -> dict:
        """Inspect framework, package scripts and filenames in the assigned frontend project."""
        return workspace.inspect()

    @tool
    def read_file(relative_path: str) -> dict:
        """Read one UTF-8 source file using a project-relative path, excluding secrets."""
        try:
            return workspace.read(relative_path)
        except WorkspaceError as exc:
            return {"status": "error", "reason": str(exc)}

    @tool
    def write_file(relative_path: str, content: str, overwrite: bool = False) -> dict:
        """Create or overwrite one source file; overwrite must be explicitly true for edits."""
        try:
            return workspace.write(relative_path, content, overwrite)
        except WorkspaceError as exc:
            return {"status": "error", "reason": str(exc)}

    @tool
    def run_command(action: str) -> dict:
        """Run allowlisted npm actions: install, build, lint, test or typecheck. No arbitrary shell."""
        return runner.run(action)

    @tool
    def run_validation() -> dict:
        """Run deterministic build, lint, test and typecheck checks; build must pass."""
        return runner.validate()

    @tool
    def git_diff() -> dict:
        """Show read-only status and diff; do not commit, push or merge code."""
        return workspace.git_diff() if remote else local_git_diff(workspace.root)

    return [inspect_repo, read_file, write_file, run_command, run_validation, git_diff]
