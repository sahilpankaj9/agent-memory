"""The memory hierarchy from Anthropic's "components of agent memory".

The article describes memory as four layers, bottom to top:

    INJECTED        small index loaded into every session's context
    REPRESENTATION  wikis and other maps Claude builds over its notes
    NOTE            salient observations Claude writes during a session
    TRANSCRIPT      the raw, searchable event log of what happened

The live agent writes TRANSCRIPT and NOTE while it works. Dreaming runs offline
and moves information up the stack: it checks notes against transcripts, builds
representations, and promotes a small set of notes into the injected layer.

This file is the contract, not an implementation. Any store that can hold the
four layers and let you read and write each one can run the hierarchy. AgentCore
is the reference backend (src/backends/agentcore_backend.py). Swap it for a vector
DB, a git repo of markdown files, Mem0, or Zep and nothing above changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class Layer(str, Enum):
    TRANSCRIPT = "transcript"       # raw event log
    NOTE = "note"                   # salient observations
    REPRESENTATION = "representation"  # wikis / maps over notes
    INJECTED = "injected"           # the small top index, loaded every session


@dataclass
class Event:
    """One raw turn from the transcript layer."""
    role: str
    content: str
    session_id: str
    timestamp: str | None = None


@dataclass
class Item:
    """A stored memory item in the note, representation, or injected layer."""
    item_id: str
    layer: Layer
    content: str
    # For representations: links to other item_ids (the wiki map).
    links: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class MemoryBackend(Protocol):
    """What a store must do to host the hierarchy and support dreaming."""

    # Live agent writes these while working.
    def append_transcript(self, actor_id: str, session_id: str, role: str, content: str) -> None: ...

    # Read any layer. Dreaming reads transcripts + the layer it is curating.
    def read_transcripts(self, actor_id: str, limit: int) -> list[Event]: ...
    def read_layer(self, actor_id: str, layer: Layer) -> list[Item]: ...

    # Dreaming writes results back up the stack.
    def write_item(self, actor_id: str, layer: Layer, content: str,
                   links: list[str] | None = None, item_id: str | None = None) -> str: ...
    def delete_item(self, item_id: str) -> None: ...
