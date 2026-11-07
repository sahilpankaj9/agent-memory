# Scheduling the dream (consolidation) job

The dream pass is an *offline* process. Run it when the agent is idle, not in
the request path. Pick whichever fits your setup.

## Local / cron (simplest)

```cron
# Every night at 02:00, reflect across the day's sessions
0 2 * * *  cd /path/to/Agent-Memory && /usr/bin/python -m src.dream_job >> dream.log 2>&1
```

Start with `DREAM_AUTO_APPLY=false` so it only *stages* a `dream_review_*.json`.
Review a few runs, then flip to `true` to let it write automatically.

## AWS Lambda + EventBridge (serverless)

1. Package `src/` + dependencies into a Lambda (container image is easiest since
   you already have the Dockerfile, so point the handler at a small wrapper that
   calls `src.dream_job.dream`).
2. Give the Lambda role the same Bedrock + AgentCore Memory permissions as the
   Runtime role.
3. Create an EventBridge Scheduler rule, e.g. `cron(0 2 * * ? *)`, targeting it.

```python
# lambda_handler.py
from src.dream_job import dream

def handler(event, context):
    plan = dream()
    return {"applied": bool(plan)}
```

## Cross-agent dreaming

To reproduce Anthropic's *shared* consolidation across a fleet: point multiple
agents at the **same MEMORY_ID** (or shared namespace) and run one dream job over
the pooled sessions. Lessons one agent learns then surface for all of them.
Keep per-user data in `{actorId}` namespaces; put team-level insights in a shared
namespace like `team/shared`.

## Guardrails

- Don't run the dream job on sparse history. Cross-session patterns need volume,
  or you just get noise. Wait until you have real session data.
- Keep `DREAM_AUTO_APPLY=false` until you trust the consolidation prompt.
- Log every applied change (the `insights` array) so memory edits are auditable.
