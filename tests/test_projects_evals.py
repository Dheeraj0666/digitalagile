import json
import zipfile
from pathlib import Path

import pytest

from digitalagile.frontend_agent.projects import prepare_new, prepare_existing, ProjectPreparationError
from digitalagile.frontend_agent.runner import allowed_commands, scripts_in, DockerRunner
from digitalagile.frontend_agent.artifacts import export_project
from digitalagile.evals.evaluate import evaluate


def test_prepare_new_populates_template(tmp_path):
    target = tmp_path / "generated-ui"
    result = prepare_new(target)
    assert result == target
    assert (target / "src/App.tsx").is_file()
    assert "build" in json.loads((target / "package.json").read_text())["scripts"]


def test_prepare_new_does_not_overwrite(tmp_path):
    target = tmp_path / "generated-ui"
    target.mkdir()
    (target / "valuable.txt").write_text("keep")
    with pytest.raises(ProjectPreparationError):
        prepare_new(target)
    assert (target / "valuable.txt").read_text() == "keep"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "https://evil.example/x/y",
    "https://github.com/a/b?token=x",
    "https://user:pass@github.com/a/b",
    "https://github.com/a/b/tree/main",
    "git@github.com:a/b.git",
])
def test_disallowed_repo_urls(tmp_path, url):
    with pytest.raises(ProjectPreparationError):
        prepare_existing(tmp_path / "repo", url)


def test_command_policy_no_arbitrary_shell():
    assert allowed_commands("curl", has_package=True, has_script=True, allow_install=True)["status"] == "rejected"
    assert allowed_commands("install", has_package=True, has_script=False, allow_install=False)["status"] == "blocked"
    assert allowed_commands("build", has_package=True, has_script=False, allow_install=False)["status"] == "skipped"
    assert allowed_commands("test", has_package=True, has_script=True, allow_install=False) == [["npm", "run", "test"]]


def test_validator_does_not_claim_success_without_docker(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}))
    runner = DockerRunner(tmp_path)
    monkeypatch.setattr(runner, "_docker_run", lambda *args, **kwargs: {"status": "unavailable"})
    assert runner.validate()["status"] == "failed"


def test_export_skips_secrets_and_dependencies(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "App.tsx").write_text("export default function App() { return null };")
    (root / ".env").write_text("SECRET=sensitive")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.js").write_text("javascript")
    zip_path = export_project(root, tmp_path / "app.zip")
    with zipfile.ZipFile(zip_path) as z:
        assert z.namelist() == ["src/App.tsx"]


def test_eval_reports_missing_requirements(tmp_path):
    result = evaluate(tmp_path, {"id": "example", "expected_paths": ["src/App.tsx"], "expected_text": ["history"]}, build_passed=False)
    assert result["score"] == 0
    assert result["build_status"] == "failed"
