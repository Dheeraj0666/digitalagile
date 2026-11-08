# AgentCore Runtime — optional POC path

This is **not a deployment-tested, production-ready configuration**. First validate the local Docker workflow using a throwaway app. A Strands agent can call models via Anthropic/Bedrock/Ollama. AgentCore hosts the agent process; it does not implicitly provide model credentials.

## Preflight

1. AWS account with AgentCore Runtime permissions, ECR/CodeBuild access as required by your deployment route, IAM role with appropriate model access, and CloudWatch logs.
2. Choose the model provider and configure credentials securely. For Bedrock, set `MODEL_PROVIDER=bedrock`, `BEDROCK_MODEL_ID`, and `AWS_REGION` in runtime configuration; do **not** bake credentials into images or Git.
3. Build the included container with the intended AgentCore deployment method. It exposes port **8080** through `BedrockAgentCoreApp` at `agentcore/app.py` and installs Node.js plus Python. It does **not** contain a separate sandbox for npm scripts.
4. For *trusted source only*, explicitly set `AGENTCORE_ALLOW_TRUSTED_RUNNER=1` after reviewing the risk. The default is to refuse code execution.
5. Deploy using your organization's approved AgentCore flow (starter toolkit or infrastructure-as-code). Refer to official current commands: https://github.com/aws/bedrock-agentcore-starter-toolkit and https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started.html. Actual account-specific roles, security groups and auth must be configured separately.

Local Docker image build smoke check (does not verify IAM or agent reasoning):

```bash
docker build -f Dockerfile.agentcore -t digitalagile-agent:local .
```

Example invocation payload (`agentcore/payload.example.json`):

```json
{
  "story": "Build an accessible React content-analysis UI with clearly mocked responses and uncertainty language",
  "allow_network_install": true
}
```

The AgentCore entrypoint performs one agent run, then returns validation and a small ZIP as `artifact_zip_base64`. It does not create a PR or push code. Use `python scripts/decode_agentcore.py response.json --out generated-ui.zip` to recover the artifact from a response JSON file. Very large archives return an explicit error; use S3 or a managed artifact store rather than silent truncation.

## Production migration work

Do not use `TrustedProcessRunner` against arbitrary users' repositories. Replace it with an independent tenant-isolated code execution service (for example an approved managed sandbox), artifact storage, authentication/authorization, dependency allowlisting and network egress policy. Add session isolation, approval checkpoints, cost/time budgets, structured evaluation traces, and deployment tests. AgentCore alone is not a code-execution isolation boundary.
