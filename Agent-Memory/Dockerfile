# AgentCore Runtime requires linux/arm64 containers.
FROM --platform=linux/arm64 python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# AgentCore Runtime invokes the entrypoint on port 8080.
EXPOSE 8080

CMD ["python", "runtime_entrypoint.py"]
