"""Restore a small generated project ZIP from AgentCore invocation JSON."""
import argparse
import base64
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("response_file", help="The JSON response from an AgentCore invocation")
p.add_argument("--out", default="agentcore-generated-ui.zip")
a = p.parse_args()
response = json.loads(Path(a.response_file).read_text(encoding="utf-8"))
raw = response.get("artifact_zip_base64")
if raw is None:
    raise SystemExit(f"No inline artifact in response: {response.get('artifact_error', 'not found')}")
Path(a.out).write_bytes(base64.b64decode(raw, validate=True))
print(f"Wrote {a.out}")
