# Running exclurad-mcp on a fully free / open-source stack

The MCP server is agent-agnostic. Two open agents are relevant here:

- **[OpenClaude](https://github.com/Gitlawb/openclaude)** (`npm i -g
  @gitlawb/openclaude`, Node ≥ 22) — points at any OpenAI-compatible
  endpoint. Register with `openclaude mcp add ...`, verify with
  `openclaude mcp list` (note which command/env it launches — no
  auto-update, it runs whatever the registration points at).
- **[OpenCode](https://opencode.ai)** — an alternative open agent worth
  trying for comparison; also speaks MCP and any OpenAI-compatible endpoint.

Both take OpenAI-compatible endpoints, which is what NVIDIA Build provides
for free.

## Free inference: NVIDIA Build + GLM 5.2

| Layer | Component | Cost |
|---|---|---|
| Model | GLM 5.2 (`z-ai/glm-5.2`, open-weight, strong agentic model) | free via NVIDIA |
| Inference | `https://integrate.api.nvidia.com/v1` (OpenAI-compatible) | free tier, `nvapi-` key, no credit card |
| Agent | OpenClaude (or OpenCode) | free |
| Tools | this MCP server + conda env (`environment.yml`) | free |

Caveats to state honestly in any demo/talk: the NVIDIA free tier queues badly
at peak hours (fine off-peak, not production), and "GLM ~ Opus" is a community
claim — treat agent-model quality as something the benchmark study measures
(same task list under Claude and GLM 5.2, compare input-validity rates), not
something we assert.

### Get the key

Sign in at https://build.nvidia.com (developer program, no card), open
https://build.nvidia.com/z-ai/glm-5.2, click **Get API Key**, then:

```bash
export NVIDIA_API_KEY=nvapi-...
```

### Sanity-check the endpoint

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)
resp = client.chat.completions.create(
    model="z-ai/glm-5.2",
    messages=[{"role": "user", "content": "Say OK."}],
    max_tokens=16,
)
print(resp.choices[0].message.content)
```

### Register the MCP server in OpenClaude

Exact CLI/JSON syntax: check `openclaude mcp --help` for the installed
version — pin the command to the conda env that has `exclurad-mcp` on PATH:

```bash
openclaude mcp add exclurad \
  --env EXCLURAD_WORK_DIR_ETA=/path/to/IzzyIllari-exclurad/exclurad \
  --env EXCLURAD_WORK_DIR_PIPLUS=/path/to/JeffersonLab-exclurad/exclurad \
  -- ~/miniforge3/envs/exclurad/bin/exclurad-mcp
openclaude mcp list   # verify the command/env it will launch
```

Any other OpenAI-compatible provider wires up the same way.

### Same server in Claude Code (for the cross-model benchmark)

```bash
claude mcp add exclurad \
  -e EXCLURAD_WORK_DIR_ETA=/path/to/IzzyIllari-exclurad/exclurad \
  -e EXCLURAD_WORK_DIR_PIPLUS=/path/to/JeffersonLab-exclurad/exclurad \
  -- exclurad-mcp
```

Then try, in either agent:

> "Smoke test the eta channel at W=1.49 GeV, Q²=0.5, cos θ*=0.9, φ=90°,
> then explain the preflight report."

The agent-accuracy benchmark runs the identical task list under several
models — if validity rates match across models, that supports the claim
that the deterministic tooling carries correctness, not the model.
