"""Local VS Code CLI for a single Strands frontend agent."""
from __future__ import annotations
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from .artifacts import export_project, write_report
from .projects import prepare_existing, prepare_new
from .engine import run_story


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Digital Agile Team: single Frontend Engineer Agent")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--new", action="store_true", help="Initialize a new React/TypeScript frontend project")
    modes.add_argument("--repo", help="Clone and enhance an existing public GitHub repository")
    modes.add_argument("--use-existing-directory", action="store_true", help="Enhance a locally checked-out repo")
    parser.add_argument("--workspace", required=True, help="Absolute or relative path OUTSIDE this agent repo")
    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument("--story", help="Business requirement text")
    text.add_argument("--story-file", help="Path to a UTF-8 story file")
    parser.add_argument("--allow-network-install", action="store_true", help="Allow npm dependencies to be installed in disposable Docker sandbox")
    parser.add_argument("--max-repairs", type=int, default=3, choices=range(0, 5))
    parser.add_argument("--no-export", action="store_true", help="Skip generated project ZIP")
    args = parser.parse_args()

    source_root = Path(__file__).resolve().parents[1]
    root = Path(args.workspace).expanduser().resolve()
    if root == source_root or source_root.is_relative_to(root) or root.is_relative_to(source_root):
        parser.error("--workspace must point outside the agent source repository")
    if args.new:
        prepare_new(root)
    elif args.repo:
        prepare_existing(root, args.repo)
    elif not root.is_dir():
        parser.error("--use-existing-directory requires an existing directory")

    story = Path(args.story_file).read_text(encoding="utf-8") if args.story_file else args.story
    run = run_story(story, root, allow_network_install=args.allow_network_install, max_repairs=args.max_repairs)
    reports = source_root / "outputs"
    label = root.name.replace(" ", "-")
    report = write_report(reports / f"{label}-report.json", story=story, validation=run.validation,
                          attempts=run.attempts, project_root=root, agent_result=run.summary, errors=run.errors)
    print("\nAgent response:\n", run.summary)
    print("\nFINAL validation:", run.validation["status"])
    print("Report:", report)
    if not args.no_export:
        archive = export_project(root, reports / f"{label}-source.zip")
        print("Generated source ZIP:", archive)
    if run.validation["status"] != "passed":
        raise SystemExit("Agent completed with validation failures. See report for details")


if __name__ == "__main__":
    main()
