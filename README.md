# Digital Agile Team — Frontend Engineer Agent (POC starter)

**Scope:** One reusable Frontend Engineer Agent. Works with a supplied existing project directory or an empty directory for a new project. Python/Strands orchestrates React/TypeScript or other inspected frontend files. The first tested toolchain target is **npm-based React**; broad language/framework compatibility is a later evaluation target, not an achieved claim.

## What is included

- `frontend_agent/main.py`: one Strands Agent using Amazon Bedrock
- `workspace.py`: inspect files, read, and atomic create/update within assigned directory
- `tools.py`: six Strands tools: `inspect_repo`, `read_file`, `write_file`, `run_command`, `run_validation`, `git_diff`
- `runner.py`: Docker-contained, allowlisted npm operations, no arbitrary shell
- `hooks.py`: tool-call budget and metadata-only JSONL audit events
- `prompts/frontend_engineer.md`: agent behavior and three remediation attempts guideline
- `evals/`: deterministic smoke rubric for new-project and existing-project scenarios
- `tests/`: offline unit tests; do not require AWS credentials

## Local setup

Use an approved development environment with Python 3.11+, Docker, and Git.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m pytest -q
```

Choose **your organization's approved Bedrock Claude model ID** and region. Do not assume your office Claude chat subscription provides Bedrock API access.

```bash
export BEDROCK_MODEL_ID='YOUR_APPROVED_BEDROCK_MODEL_ID'
export AWS_REGION='us-east-1'
mkdir -p ../generated-ui
python -m frontend_agent.main \
  --workspace ../generated-ui \
  --story 'Build a React UI for written-text AI-authorship analysis using a clearly labeled mock API and uncertainty language.'
```

For an **existing repository**, create a feature branch, clone the repo to a disposable workspace, and supply that workspace directory. **Never point the agent at its own repository.** Inspect `git_diff` and review before any commit/push/merge. For a **new project**, supply an empty workspace.

### Dependency installation limitations

Build, lint, and test run in Docker with network disabled and constrained resources. The `install` action runs `npm ci --ignore-scripts` and needs a lockfile. Networked installation is explicitly blocked by default. When installing reviewed packages in a disposable non-sensitive environment, an operator may pass `--allow-network-install`; it enables network access **for npm installation only** and is **not suitable for arbitrary untrusted repos** without an outbound proxy and supply-chain controls. A new project should generate package.json + lockfile (or have an operator generate the lockfile using approved tooling). Without installed dependencies, builds will fail; the agent must report that accurately.

This starter does not include a remote workspace service, comprehensive isolation against malicious projects, repository authentication, a real frontend UI, or an AgentCore deployment manifest. Docker isolation is defense-in-depth, not a security certification. Do not connect confidential company repositories until security review.

## Offline tests

```bash
python -m pytest -q
```

These validate workspace operations, safe paths, file creation/overwriting, framework identification, and command restrictions. They **do not** test a live Strands/Bedrock agent or run a frontend build.

## Artifact evaluation after a run

```bash
python evals/evaluate.py --project ../generated-ui --scenario new_project_content_detector_ui
python evals/evaluate.py --project ../generated-ui --scenario new_project_content_detector_ui --build-passed yes
```

The evaluator checks expected files and basic strings. It does not prove UI correctness. Add Playwright acceptance tests, accessibility checks, regression tests, and judge-based evals after the first live run. Track success rate, build pass rate, tool failures, retries, and human interventions.

## Acceptance criteria for POC

1. New project story: generated files plus real npm build success.
2. Existing repo story: working enhancement, passing tests, reviewable Git diff.
3. Security: no unscoped paths, no arbitrary host shell, no branch merge/push by agent.
4. Observability: tool count and duration only; no secret-bearing input logging.
5. Report uncertainties honestly; AI authorship cannot be inferred definitively from text.

## Reusing the old POC Git repo

On your **own machine**, preserve history with a new branch before removing files; then copy this starter into that branch. Do not delete `.git`. Do not automatically run destructive commands against the original. The starter has **not** been pushed or deployed.

## Official references

- https://strandsagents.com/docs/user-guide/sdk/quickstart/python/
- https://strandsagents.com/docs/user-guide/sdk/agents/hooks/
- https://strandsagents.com/docs/user-guide/sdk/agents/hooks-events/
