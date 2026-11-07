"""AgentCore implementation of the four-layer hierarchy.

Maps the layers onto AgentCore Memory:
    TRANSCRIPT      short-term events (create_event / list_events)
    NOTE            long-term records in note namespaces
    REPRESENTATION  long-term records in wiki namespaces
    INJECTED        a single small record in the injected namespace

This is one backend. The same hierarchy runs on anything that satisfies
MemoryBackend. Method and field names across preview SDK versions drift, so the
reads are defensive.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bedrock_agentcore.memory import MemoryClient

from ..memory_backend import Event, Item, Layer, MemoryBackend

# Namespace prefix per layer. {actor} is filled per call.
_NS = {
    Layer.NOTE: "notes/{actor}",
    Layer.REPRESENTATION: "wiki/{actor}",
    Layer.INJECTED: "injected/{actor}",
}


class AgentCoreMemoryBackend(MemoryBackend):
    def __init__(self, memory_id: str, region_name: str):
        self.memory_id = memory_id
        self.client = MemoryClient(region_name=region_name)

    def append_transcript(self, actor_id, session_id, role, content) -> None:
        self.client.create_event(
            memory_id=self.memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[(role, content)],
        )

    def read_transcripts(self, actor_id, limit) -> list[Event]:
        try:
            raw = self.client.list_events(
                memory_id=self.memory_id, actor_id=actor_id, max_results=limit
            )
        except Exception:
            raw = []
        out: list[Event] = []
        for e in raw or []:
            msgs = e.get("messages") or e.get("payload") or []
            sid = e.get("sessionId", "")
            ts = e.get("timestamp") or e.get("eventTimestamp")
            for m in msgs:
                role = m[0] if isinstance(m, (list, tuple)) else m.get("role", "user")
                text = m[1] if isinstance(m, (list, tuple)) else m.get("content", "")
                out.append(Event(role=role, content=str(text), session_id=sid,
                                 timestamp=str(ts)))
        return out

    def read_layer(self, actor_id, layer) -> list[Item]:
        if layer == Layer.TRANSCRIPT:
            raise ValueError("Use read_transcripts for the transcript layer.")
        ns = _NS[layer].format(actor=actor_id)
        try:
            res = self.client.retrieve_memories(
                memory_id=self.memory_id, namespace=ns, query="", top_k=100
            )
        except Exception:
            res = []
        items: list[Item] = []
        for r in res or []:
            items.append(Item(
                item_id=r.get("memoryRecordId", r.get("id", "")),
                layer=layer,
                content=str(r.get("content", r.get("text", ""))),
                links=r.get("links", []),
                metadata=r,
            ))
        return items

    def write_item(self, actor_id, layer, content, links=None, item_id=None) -> str:
        if layer == Layer.TRANSCRIPT:
            raise ValueError("Use append_transcript for the transcript layer.")
        ns = _NS[layer].format(actor=actor_id)
        self.client.create_event(
            memory_id=self.memory_id,
            actor_id=actor_id,
            session_id=f"dream-{datetime.now(timezone.utc):%Y%m%d}",
            messages=[("assistant", content)],
            namespace=ns,
        )
        return item_id or ns

    def delete_item(self, item_id) -> None:
        self.client.delete_memory_record(
            memory_id=self.memory_id, memory_record_id=item_id
        )
