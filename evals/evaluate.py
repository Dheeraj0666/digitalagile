"""Deterministic artifact evaluator. Run after an agent-produced project exists.

Scenarios must also be verified by meaningful UI tests and manual review.
This does not call a model, and is not a substitute for Strands Evals SDK.
"""
import argparse
import json
from pathlib import Path


def evaluate(project_dir: Path, scenario: dict, build_passed: bool | None = None) -> dict:
    presence = {p: (project_dir / p).is_file() for p in scenario["expected_paths"]}
    source = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                       for p in project_dir.rglob("*.tsx") if "node_modules" not in p.parts).lower()
    keywords = {word: word.lower() in source for word in scenario.get("expected_text", [])}
    checks = list(presence.values()) + list(keywords.values())
    if build_passed is not None:
        checks.append(build_passed)
    return {
        "scenario_id": scenario["id"], "file_checks": presence,
        "heuristic_keyword_checks": keywords,
        "build_status": "not_provided" if build_passed is None else ("passed" if build_passed else "failed"),
        "checks_passed": sum(checks), "total_checks": len(checks),
        "score": round(sum(checks) / len(checks), 3) if checks else 0,
        "caveat": "Heuristic checks cannot prove story compliance; require real UI tests and review.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--build-passed", choices=["yes", "no"])
    args = parser.parse_args()
    scenarios = json.loads((Path(__file__).parent / "scenarios.json").read_text())
    scenario = next((s for s in scenarios if s["id"] == args.scenario), None)
    if not scenario:
        parser.error("Unknown scenario")
    print(json.dumps(evaluate(Path(args.project), scenario,
                              None if args.build_passed is None else args.build_passed == "yes"), indent=2))


if __name__ == "__main__":
    main()
