"""Dreaming: the offline pass that organizes memory.

From the article, dreaming does five jobs. Each one is a function here. All of
them read the raw transcripts as ground truth, reflect with a Bedrock model, and
either write the result back (DREAM_AUTO_APPLY=true) or stage it for review.

    correct_notes   check notes against transcripts, rewrite the wrong ones
    build_wiki      turn transcripts + notes into linked representation pages
    promote         float a few key notes into the small injected layer
    focus           grow memory toward a stated goal (DREAM_GOAL)
    fill_gaps       scan across sessions, repair broken links / missing pages

Run all:        python -m src.dream_job
Run one:        python -c "from src.dream_job import build_wiki; build_wiki()"
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

import boto3

from .backends import AgentCoreMemoryBackend
from .config import config
from .memory_backend import Layer, MemoryBackend


def _backend() -> MemoryBackend:
    if not config.memory_id:
        raise RuntimeError("MEMORY_ID not set. Run create_memory.py first.")
    return AgentCoreMemoryBackend(config.memory_id, config.aws_region)


def _reflect(system_prompt: str, payload: dict) -> dict:
    """Ask Bedrock for a JSON plan. Shared by every dreaming operation."""
    bedrock = boto3.client("bedrock-runtime", region_name=config.aws_region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 3000,
        "system": system_prompt,
        "messages": [{"role": "user",
                      "content": json.dumps(payload, default=str)[:180_000]}],
    }
    resp = bedrock.invoke_model(modelId=config.dream_model_id, body=json.dumps(body))
    text = json.loads(resp["body"].read())["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s, e = text.find("{"), text.rfind("}")
        return json.loads(text[s:e + 1])


def _apply_or_stage(backend: MemoryBackend, op: str, plan: dict) -> dict:
    """Write the plan back, or stage it for a human. Mirrors the article's
    'update automatically, or review before it lands'."""
    print(f"\n[{op}] plan:\n" + json.dumps(plan, indent=2)[:3000])
    if not config.dream_auto_apply:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = f"dream_{op}_{stamp}.json"
        with open(path, "w") as f:
            json.dump(plan, f, indent=2, default=str)
        print(f"[{op}] staged for review in {path}. Nothing written.")
        return plan

    for w in plan.get("writes", []):
        backend.write_item(config.actor_id, Layer(w["layer"]), w["content"],
                           links=w.get("links"), item_id=w.get("item_id"))
    for d in plan.get("deletes", []):
        try:
            backend.delete_item(d["item_id"])
        except Exception as exc:
            print(f"[{op}] delete failed {d.get('item_id')}: {exc}")
    print(f"[{op}] applied.")
    return plan


# ---- the five operations -------------------------------------------------

CORRECT_PROMPT = """You validate an agent's memory notes against the raw transcript,
which is ground truth. Find notes that are wrong or stale. Return JSON:
{"writes":[{"layer":"note","item_id":"<id to overwrite>","content":"<fixed note>"}],
 "deletes":[{"item_id":"<id>"}], "insights":["<what was wrong>"]}"""

BUILD_WIKI_PROMPT = """You build a wiki over the agent's notes and transcripts. Make
small linked pages, one subject each, quoting source facts rather than summarizing
them away. Merge duplicates. Return JSON:
{"writes":[{"layer":"representation","item_id":"<page key>","content":"<page>",
 "links":["<other page keys>"]}], "insights":["..."]}"""

PROMOTE_PROMPT = """You maintain the injected layer: the small index loaded into
every session. Keep it under the character budget. Promote only durable, high-value
notes. Leave links down to detail instead of copying it up. Return JSON:
{"writes":[{"layer":"injected","item_id":"index","content":"<the index>"}],
 "insights":["..."]}"""

FOCUS_PROMPT = """You grow memory toward a goal. Keep what serves the goal, drop what
does not, and say how the memory should be organized for it. Return JSON:
{"writes":[{"layer":"note","content":"<goal-focused note>"}], "insights":["..."]}"""

FILL_GAPS_PROMPT = """You scan across sessions for gaps: broken wiki links, pages that
are referenced but missing, patterns repeated across sessions that deserve a note.
Return JSON:
{"writes":[{"layer":"representation","item_id":"<page>","content":"...","links":[...]}],
 "insights":["..."]}"""


def correct_notes(backend: MemoryBackend | None = None) -> dict:
    b = backend or _backend()
    plan = _reflect(CORRECT_PROMPT, {
        "transcripts": [asdict(e) for e in b.read_transcripts(config.actor_id,
                        config.dream_lookback_sessions * 50)],
        "notes": [asdict(i) for i in b.read_layer(config.actor_id, Layer.NOTE)],
    })
    return _apply_or_stage(b, "correct", plan)


def build_wiki(backend: MemoryBackend | None = None) -> dict:
    b = backend or _backend()
    plan = _reflect(BUILD_WIKI_PROMPT, {
        "transcripts": [asdict(e) for e in b.read_transcripts(config.actor_id,
                        config.dream_lookback_sessions * 50)],
        "notes": [asdict(i) for i in b.read_layer(config.actor_id, Layer.NOTE)],
        "existing_wiki": [asdict(i) for i in b.read_layer(config.actor_id,
                          Layer.REPRESENTATION)],
    })
    return _apply_or_stage(b, "build_wiki", plan)


def promote(backend: MemoryBackend | None = None) -> dict:
    b = backend or _backend()
    plan = _reflect(PROMOTE_PROMPT + f"\nBudget: {config.injected_max_chars} chars.", {
        "notes": [asdict(i) for i in b.read_layer(config.actor_id, Layer.NOTE)],
        "wiki": [asdict(i) for i in b.read_layer(config.actor_id, Layer.REPRESENTATION)],
        "current_injected": [asdict(i) for i in b.read_layer(config.actor_id,
                             Layer.INJECTED)],
    })
    return _apply_or_stage(b, "promote", plan)


def focus(backend: MemoryBackend | None = None) -> dict:
    if not config.dream_goal:
        print("[focus] DREAM_GOAL is empty, skipping.")
        return {}
    b = backend or _backend()
    plan = _reflect(FOCUS_PROMPT + f"\nGoal: {config.dream_goal}", {
        "transcripts": [asdict(e) for e in b.read_transcripts(config.actor_id,
                        config.dream_lookback_sessions * 50)],
        "notes": [asdict(i) for i in b.read_layer(config.actor_id, Layer.NOTE)],
    })
    return _apply_or_stage(b, "focus", plan)


def fill_gaps(backend: MemoryBackend | None = None) -> dict:
    b = backend or _backend()
    plan = _reflect(FILL_GAPS_PROMPT, {
        "wiki": [asdict(i) for i in b.read_layer(config.actor_id, Layer.REPRESENTATION)],
        "notes": [asdict(i) for i in b.read_layer(config.actor_id, Layer.NOTE)],
    })
    return _apply_or_stage(b, "fill_gaps", plan)


def dream() -> None:
    """Run a full dream cycle: correct, then build, promote, focus, fill gaps."""
    b = _backend()
    if not b.read_transcripts(config.actor_id, 10):
        print("No transcripts yet. Nothing to dream on.")
        return
    correct_notes(b)
    build_wiki(b)
    promote(b)
    focus(b)
    fill_gaps(b)


if __name__ == "__main__":
    dream()
