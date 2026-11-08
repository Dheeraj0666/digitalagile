"""Strands tools bound to a single workspace; import SDK only on agent startup."""
from .workspace import Workspace, WorkspaceError
from .runner import DockerRunner, git_diff as collect_git_diff


def make_tools(workspace: Workspace, runner: DockerRunner):
    from strands import tool

    @tool
    def inspect_repo() -> dict:
        """Inspect frontend framework, package scripts and project file names without modifying them."""
        return workspace.inspect()

    @tool
    def read_file(relative_path: str) -> dict:
        """Read a UTF-8 source file in the assigned project using a project-relative path."""
        try:
            return workspace.read(relative_path)
        except WorkspaceError as e:
            return {"status": "error", "error": str(e)}

    @tool
    def write_file(relative_path: str, content: str, overwrite: bool = False) -> dict:
        """Create or update a project-relative source file; set overwrite to true for existing files."""
        try:
            return workspace.write(relative_path, content, overwrite)
        except WorkspaceError as e:
            return {"status": "error", "error": str(e)}

    @tool
    def run_command(action: str) -> dict:
        """Execute one Docker-isolated npm action: install, build, lint or test. No arbitrary shell."""
        return runner.run(action)

    @tool
    def run_validation() -> dict:
        """Run available build, lint and test scripts in the restricted Docker runner."""
        results = {key: runner.run(key) for key in ("build", "lint", "test")}
        passed = all(v.get("status") in ("passed", "skipped") for v in results.values())
        passed = passed and results["build"].get("status") == "passed"
        return {"status": "passed" if passed else "failed", "checks": results}

    @tool
    def git_diff() -> dict:
        """Read Git status and diff for human review; never commit, merge or push."""
        return collect_git_diff(workspace.root)

    return [inspect_repo, read_file, write_file, run_command, run_validation, git_diff]
