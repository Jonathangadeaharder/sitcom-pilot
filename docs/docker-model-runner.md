# Docker Model Runner Integration

Docker Model Runner with vllm-metal provides Metal-accelerated LLM inference
for sitcom-pilot's text-based AI tasks, running natively on the macOS host.

## Prerequisites
- Docker Desktop 4.40+ on Apple Silicon Mac
- Docker Model Runner enabled: `docker desktop enable model-runner`
- vllm-metal backend: `docker model install-runner --backend vllm`

## Pull Models
```bash
docker model pull ai/smollm2
```

## Endpoint
- From containers: `http://host.docker.internal:12434/engines/v1`
- From host: `http://localhost:12434/engines/v1`

## Integration
The `aiservices_client.py` provider abstraction layer can route text-based
inference requests to the DMR endpoint via the OpenAI-compatible API.
Media-generation providers (text2image, image2video, text2speech) continue
to use MLX directly.

## CI
On self-hosted macOS runners, DMR provides a reproducible inference environment
without bare-metal Ollama or LM Studio configuration.
