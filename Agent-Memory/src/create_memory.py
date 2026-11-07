"""Create an AgentCore Memory resource shaped to the article's hierarchy.

AgentCore gives you two things for free that map onto the lower layers:
    transcript layer  -> short-term events (raw log)
    note layer        -> long-term records produced by built-in strategies

The built-in strategies below do the always-on, near-session consolidation
(extraction + merge). The deeper hierarchy work (wikis, promotion to the injected
layer, cross-session gap filling) runs in dream_job.py.

Run once:  python -m src.create_memory
Then copy the printed MEMORY_ID into .env.
"""
from __future__ import annotations

import time

from bedrock_agentcore.memory import MemoryClient

from .config import config

# Built-in strategies feed the NOTE layer. Namespaces are scoped per actor.
STRATEGIES = [
    {"semanticMemoryStrategy": {"name": "Facts", "namespaces": ["notes/{actorId}"]}},
    {"userPreferenceMemoryStrategy": {"name": "Prefs", "namespaces": ["notes/{actorId}"]}},
    {"summaryMemoryStrategy": {"name": "Summaries",
                               "namespaces": ["notes/{actorId}/{sessionId}"]}},
    {"episodicMemoryStrategy": {"name": "Episodes", "namespaces": ["notes/{actorId}"]}},
]


def create_or_get_memory() -> str:
    client = MemoryClient(region_name=config.aws_region)
    if config.memory_id:
        print(f"MEMORY_ID already set: {config.memory_id}")
        return config.memory_id

    print(f"Creating memory '{config.memory_name}' ...")
    memory = client.create_memory_and_wait(
        name=config.memory_name,
        description="Four-layer agent memory hierarchy with offline dreaming",
        strategies=STRATEGIES,
        event_expiry_days=90,
    )
    memory_id = memory.get("id") or memory.get("memoryId")
    print("\nMemory created.")
    print(f"MEMORY_ID={memory_id}")
    print("Add that to .env before running the agent.")
    return memory_id


if __name__ == "__main__":
    start = time.time()
    create_or_get_memory()
    print(f"Done in {time.time() - start:.1f}s")
