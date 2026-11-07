"""The live agent. In the article's terms, this is the part that works "forward":
it writes the transcript and note layers while it runs.

Every turn goes to AgentCore short-term memory (the transcript layer). Built-in
strategies consolidate those turns into long-term records (the note layer) in the
background. Relevant notes are retrieved into context each turn. The injected
layer, wikis, and cross-session cleanup are produced offline by dream_job.py.

Run locally:  python -m src.agent
"""
from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from .config import config

# The AgentCore session manager ships in the Strands AgentCore tools package.
# Import name has moved around across preview versions, so try the known paths.
try:  # preferred
    from strands_tools.agent_core_memory import AgentCoreMemorySessionManager
except ImportError:  # fallback for older/newer layouts
    try:
        from strands.session.agentcore_memory_session_manager import (
            AgentCoreMemorySessionManager,
        )
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Could not import AgentCoreMemorySessionManager. Check the installed "
            "strands-agents-tools version and update the import in src/agent.py."
        ) from exc


SYSTEM_PROMPT = (
    "You are a helpful assistant with long-term memory. "
    "Use what you remember about the user's preferences, recurring tasks, and "
    "past mistakes to give better, more personalized answers. "
    "Do not fabricate memories you do not have."
)


def build_agent() -> Agent:
    if not config.memory_id:
        raise RuntimeError(
            "MEMORY_ID is not set. Run `python -m src.create_memory` first, "
            "then add MEMORY_ID to your .env."
        )

    model = BedrockModel(
        model_id=config.bedrock_model_id,
        region_name=config.aws_region,
    )

    # One line to attach persistent memory. The session manager:
    #   * saves each user/agent turn to short-term memory (on_message_add)
    #   * retrieves relevant long-term records and injects them each turn
    session_manager = AgentCoreMemorySessionManager(
        memory_id=config.memory_id,
        actor_id=config.actor_id,
        session_id=config.session_id,
        region_name=config.aws_region,
    )

    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        session_manager=session_manager,
    )


def chat_loop() -> None:
    agent = build_agent()
    print("Agent ready. Type 'exit' to quit.\n")
    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue
        result = agent(user)
        print(f"agent > {result}\n")


if __name__ == "__main__":
    chat_loop()
