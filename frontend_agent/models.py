"""Choose an explicit, approved Strands LLM provider on the personal laptop or AWS."""
from __future__ import annotations
import os


def create_model():
    provider = os.getenv("MODEL_PROVIDER", "anthropic").lower().strip()
    if provider == "anthropic":
        from strands.models.anthropic import AnthropicModel
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic")
        model_id = os.getenv("ANTHROPIC_MODEL_ID")
        if not model_id:
            raise RuntimeError("ANTHROPIC_MODEL_ID must be configured for your accessible model")
        return AnthropicModel(client_args={"api_key": key}, model_id=model_id)
    if provider == "bedrock":
        from strands.models import BedrockModel
        model_id = os.getenv("BEDROCK_MODEL_ID")
        if not model_id:
            raise RuntimeError("BEDROCK_MODEL_ID is required when MODEL_PROVIDER=bedrock")
        return BedrockModel(model_id=model_id, region_name=os.getenv("AWS_REGION", "us-east-1"))
    if provider == "ollama":
        from strands.models.ollama import OllamaModel
        model_id = os.getenv("OLLAMA_MODEL_ID")
        if not model_id:
            raise RuntimeError("OLLAMA_MODEL_ID is required when MODEL_PROVIDER=ollama")
        return OllamaModel(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"), model_id=model_id)
    raise RuntimeError("Unsupported MODEL_PROVIDER. Use: anthropic, bedrock, or ollama")
