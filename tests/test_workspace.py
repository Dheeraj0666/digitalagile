import json
import pytest
from digitalagile.frontend_agent.workspace import Workspace, WorkspaceError
from digitalagile.frontend_agent.runner import DockerRunner


def test_inspect_react(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "^19.0.0"}, "scripts": {"build": "vite build"}}))
    (tmp_path / "package-lock.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text("{}")
    data = Workspace(tmp_path).inspect()
    assert (data["framework"], data["language"], data["package_manager"]) == ("React", "TypeScript", "npm")
    assert data["scripts"]["build"] == "vite build"


def test_read_write_and_overwrite(tmp_path):
    ws = Workspace(tmp_path)
    ws.write("src/App.tsx", "export default function App() { return null; }")
    assert "function App" in ws.read("src/App.tsx")["content"]
    with pytest.raises(WorkspaceError):
        ws.write("src/App.tsx", "replacement")
    ws.write("src/App.tsx", "replacement", overwrite=True)
    assert ws.read("src/App.tsx")["content"] == "replacement"


@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd", ".env", "src/.env.local", ".git/config", "src/key.pem"])
def test_blocked_paths(tmp_path, path):
    with pytest.raises(WorkspaceError):
        Workspace(tmp_path).write(path, "x")


def test_symlink_escape(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir(exist_ok=True)
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceError):
        Workspace(tmp_path).write("link/test.ts", "x")


def test_new_repo_detection(tmp_path):
    assert Workspace(tmp_path).inspect()["status"] == "new_or_unknown_project"


def test_no_arbitrary_command(tmp_path):
    result = DockerRunner(tmp_path).run("rm -rf /")
    assert result["status"] == "rejected"


def test_install_requires_explicit_network(tmp_path):
    (tmp_path / "package-lock.json").write_text("{}")
    result = DockerRunner(tmp_path).run("install")
    assert result["status"] in ("unavailable", "rejected")
