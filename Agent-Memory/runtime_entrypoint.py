"""AgentCore Runtime entrypoint.

Wraps the Strands agent in the BedrockAgentCoreApp so it can be deployed to
Amazon Bedrock AgentCore Runtime as a managed, serverless HTTP endpoint.

Local test:   python runtime_entrypoint.py   (serves on :8080)
Deploy:       see deploy/README.md (agentcore configure / launch)
"""
from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from src.agent import build_agent
from src.config import config

app = BedrockAgentCoreApp()

# Build once at cold start; reuse across invocations.
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Runtime calls this per request.

    Expected payload: {"prompt": "...", "actor_id": "...", "session_id": "..."}
    actor_id / session_id override the defaults so one deployment serves many
    users while keeping each user's memory scoped.
    """
    prompt = payload.get("prompt", "")
    if not prompt:
        return {"error": "missing 'prompt' in payload"}

    agent = _get_agent()
    result = agent(prompt)
    return {
        "response": str(result),
        "actor_id": payload.get("actor_id", config.actor_id),
        "session_id": payload.get("session_id", config.session_id),
    }


if __name__ == "__main__":
    app.run()
