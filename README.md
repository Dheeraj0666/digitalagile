# Digital Agile Team — One Frontend Engineer Agent

A **single reusable Strands Agents frontend coding agent** that accepts a business story and either (a) initializes a new React/TypeScript/Vite application or (b) enhances a copied or cloned existing npm-based frontend repository. The agent writes actual files through constrained tools, runs validation and bounded repair, and exports a source ZIP and JSON report.

**Status:** Proof of concept (POC). Offline Python tests are provided. Live model-to-tool execution, full npm builds, AgentCore deployment, and UI behavior must be verified in your own environment. Do not assume it works across every framework. **Existing-repo support is currently limited to npm-based projects; do not feed untrusted repositories.**

## Contents

| Area | Files | Purpose |
| --- | --- | --- |
| Agent | `frontend_agent/engine.py`, `main.py`, `models.py` | Single Strands agent; provider configurable: Anthropic API, Bedrock, Ollama |
| Repo workflows | `projects.py`, `workspace.py` | Start new template or clone public GitHub, inspect/read/write files |
| Validation | `runner.py`, `tools.py` | Six tools with allowlisted commands and deterministic validation |
| Observability | `hooks.py` | Tool-call budget and metadata-only JSONL audit |
| Reports | `artifacts.py`, `evals/` | Generated project ZIP, JSON run report, deterministic scenario checks |
| AWS deployment | `agentcore/app.py`, `Dockerfile.agentcore` | Optional **trusted-code-only POC** AgentCore endpoint |
| Documentation | `docs/`, `examples/` | Local instructions, deployment limitations, ready-to-use stories |

## Get started on a personal laptop

Prerequisites: Python 3.11+, Git, VS Code, Docker Desktop with Docker running (for frontend builds), and **one configured model provider**. A Claude chat subscription or VS Code extension alone is *not* an agent API credential. Ollama is an optional local model provider but model capability varies.

```bash
git clone https://github.com/Dheeraj0666/digitalagile.git
cd digitalagile
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1
python -m pip install -e '.[test,anthropic]'
python -m pytest -q
```

Create `.env` from `.env.example`, set `ANTHROPIC_API_KEY` and a supported `ANTHROPIC_MODEL_ID`. For Bedrock use `MODEL_PROVIDER=bedrock`, `BEDROCK_MODEL_ID`, `AWS_REGION`, valid AWS credentials, and `pip install -e '.[test]'`. For local Ollama use `MODEL_PROVIDER=ollama`, an installed model, and `pip install -e '.[test,ollama]'`.

`--new` creates the React template inside a **new empty directory** outside this repository. `--allow-network-install` explicitly enables dependency download inside a disposable Docker container. It may access the public npm registry; use it only with approved dependency manifests and a non-sensitive project.

```bash
python -m frontend_agent.main --new \
  --workspace ../generated-content-ui \
  --story-file examples/content_detection_story.md \
  --allow-network-install
```

**Windows PowerShell** (one line):

```powershell
python -m frontend_agent.main --new --workspace ../generated-content-ui --story-file examples/content_detection_story.md --allow-network-install
```

For an existing **public GitHub** npm project, the agent clones it into a new disposable workspace and edits that local clone:

```bash
python -m frontend_agent.main --repo https://github.com/OWNER/REPOSITORY \
  --workspace ../existing-app-work \
  --story-file examples/existing_repo_story.md \
  --allow-network-install
```

For an existing **local checkout**, work on a separate branch **and preferably a disposable copy**, then use:

```bash
python -m frontend_agent.main --use-existing-directory \
  --workspace ../existing-app-work \
  --story "Add a keyboard-accessible filter to the dashboard" \
  --allow-network-install
```

After each run, review `outputs/<workspace-name>-report.json`, `outputs/<workspace-name>-source.zip`, source code, and Git diffs. The agent **does not** push or merge any changes. The `outputs/` folder is gitignored.

## How it works

1. User story, plus an existing repo URL or the choice of a new project.
2. Prepare a dedicated workspace separate from this agent repository.
3. Strands model invokes six tools: `inspect_repo`, `read_file`, `write_file`, `run_command`, `run_validation`, `git_diff`.
4. Hooks record tool metadata and enforce a tool budget (best-effort, **not** the underlying sandbox).
5. An external controller runs build, lint, test, and typecheck, with a bounded repair loop.
6. Export the source ZIP and validation report; inspect the files before using or committing them.

## Eval scenarios

```bash
python evals/evaluate.py --project ../generated-content-ui --scenario new_project_content_detector_ui --build-passed yes
python evals/evaluate.py --project ../existing-app-work --scenario existing_repo_add_history --build-passed yes
```

These evals check source-file presence and simple text heuristics. **They are not a full Strands Evals/AgentCore Evaluations integration, and do not prove the UX or authorship-detection accuracy.** Add UI automation, accessibility, security checks, and human review before expanding scope.

## Important safety and limitations

- No arbitrary model-provided shell command; only allowlisted npm actions. A package script may nevertheless execute arbitrary code, so **only run reviewed dependencies and trusted projects**. Docker isolation is defense-in-depth, not a security guarantee.
- Local validation runs in an isolated Docker container with restricted resources and network disabled, except explicit network-enabled dependency installation. Generated source is mounted in that container.
- `agentcore/app.py` offers an opt-in `AGENTCORE_ALLOW_TRUSTED_RUNNER=1` mode that executes npm inside the AgentCore runtime. **This is not safe for untrusted source code and should not be exposed publicly without external isolated code execution, authentication, egress controls, and security review.** See `docs/AGENTCORE.md`.
- API keys and AWS credentials must remain out of Git. `.env` is ignored. The repository is public.
- A frontend that reports AI-versus-human authorship is **only a mock UX demo**; no reliable definitive authorship detection can be inferred from text alone.
- `--allow-network-install` is a deliberate operator opt-in; this POC does not implement dependency provenance, a package proxy, or scanning.
- Generated-project ZIPs exclude known sensitive files and dependency/build folders, but **review the archive before sharing**.

## Validation status

We can run the offline unit tests in this workspace. A live Strands inference, full Docker/npm build, AWS auth, and deployment require your model credentials and machine/AWS setup and have **not** been demonstrated by this package alone.

Official docs: [Strands Python SDK](https://strandsagents.com/docs/user-guide/sdk/quickstart/python/) · [Strands hooks](https://strandsagents.com/docs/user-guide/sdk/agents/hooks/) · [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started.html).
