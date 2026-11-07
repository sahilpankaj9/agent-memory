"""Config loaded from environment (.env). One place for every tunable."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Config:
    # AWS / Bedrock
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )
    # Dreaming can run on a stronger model than the live agent.
    dream_model_id: str = os.getenv(
        "DREAM_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )

    # AgentCore Memory
    memory_id: str = os.getenv("MEMORY_ID", "")
    memory_name: str = os.getenv("MEMORY_NAME", "AgentMemoryHierarchy")

    # Identity / scoping
    actor_id: str = os.getenv("ACTOR_ID", "user-123")
    session_id: str = os.getenv("SESSION_ID", "session-abc")

    # Dreaming behavior
    dream_auto_apply: bool = _bool("DREAM_AUTO_APPLY", False)
    dream_lookback_sessions: int = int(os.getenv("DREAM_LOOKBACK_SESSIONS", "20"))
    # Goal-directed dreaming. Empty = general consolidation.
    dream_goal: str = os.getenv("DREAM_GOAL", "")
    # Cap on the injected (top) layer. The article keeps this small on purpose.
    injected_max_chars: int = int(os.getenv("INJECTED_MAX_CHARS", "25000"))


config = Config()
