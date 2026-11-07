# Deploying to Amazon Bedrock AgentCore Runtime

## Prerequisites

- AWS account with Bedrock model access enabled for your `BEDROCK_MODEL_ID`.
- AWS credentials configured locally (`aws configure`, SSO, or an IAM role).
- Docker (for local container builds). AgentCore Runtime uses `linux/arm64`.
- `pip install bedrock-agentcore-starter-toolkit` (provides the `agentcore` CLI).

## One-time: create the memory resource

```bash
python -m src.create_memory
# copy the printed MEMORY_ID into .env
```

## Option A: deploy with the starter toolkit (recommended)

```bash
# 1. Configure the deployment (points at the entrypoint)
agentcore configure --entrypoint runtime_entrypoint.py

# 2. Build + push + deploy to AgentCore Runtime
agentcore launch

# 3. Invoke the deployed agent
agentcore invoke '{"prompt": "remember I prefer metric units", "actor_id": "user-123", "session_id": "s1"}'
```

The toolkit builds the ARM64 image, pushes to ECR, provisions the Runtime, and
wires an execution role. Pass environment variables (MEMORY_ID, model IDs) via
the toolkit config or the Runtime's environment settings.

## Option B: manual container

```bash
docker buildx build --platform linux/arm64 -t agent-memory:latest .
# push to ECR, then create the Runtime pointing at that image.
```

## IAM permissions the Runtime execution role needs

- `bedrock:InvokeModel` on your model IDs.
- `bedrock-agentcore:*` for the memory resource (create/read events, retrieve,
  consolidate, delete records). Scope to your memory ARN in production.
- `ecr` pull + CloudWatch Logs for the Runtime itself.

## Scheduling the dream job

The dream pass runs separately from the Runtime. See `deploy/schedule.md`.
