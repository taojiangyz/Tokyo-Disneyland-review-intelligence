# Gemini to open-model migration

Aladdin keeps retrieval, deterministic analytics, tool contracts, prompts, and
evaluation independent from the answer-generation provider. The default is
Gemini; any endpoint that implements OpenAI-compatible chat completions and
tool calls can be selected without changing Agent code.

## Local Ollama example

Install Ollama separately on the host, pull a function-calling-capable model,
and make sure its OpenAI-compatible endpoint is available on port 11434. Set:

```env
ALADDIN_LLM_PROVIDER=openai_compatible
OPENAI_COMPAT_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_COMPAT_MODEL=<your-local-model>
OPENAI_COMPAT_API_KEY=
ALADDIN_LLM_PLANNER_ENABLED=true
```

`host.docker.internal` lets the Dockerized API reach Ollama running on macOS.
For a remote vLLM deployment, replace the base URL, model ID, and API key; the
Agent contract does not change.

## Parity evaluation

Run the same case subset once for each provider and keep separate reports:

```bash
python -m scripts.run_agent_evaluation --live --limit 5 \
  --output evals/results/agent_gemini.json

python -m scripts.run_agent_evaluation --live --limit 5 \
  --output evals/results/agent_open_model.json

python -m scripts.compare_agent_reports \
  evals/results/agent_gemini.json \
  evals/results/agent_open_model.json \
  --labels Gemini OpenModel \
  --output evals/results/provider_comparison.json
```

The comparison reports task pass rate, mean/P50/P95 total latency, provider,
model, and total token usage over exactly the same case IDs. A model is not
promoted only because it is cheaper: citation containment, valid tool plans,
filter correctness, deterministic-number usage, and no-evidence behavior must
continue to pass.
