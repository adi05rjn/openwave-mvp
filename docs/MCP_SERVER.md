# OpenWave local MCP server

OpenWave exposes exactly three MCP tools, backed by the same experiment
validator and numerical runner used by the CLI. The server operates only over
local **stdio**, with no listening network port, login, API key, or LLM provider.

## Install (Python 3.11+)

The GUI and regular `openwave` CLI continue to support Python 3.10 and do not
need the MCP dependency. Use Python 3.11+ for the official MCP SDK:

```bash
python -m pip install -e '.[mcp]'
openwave-mcp --output-root ./artifacts/mcp
```

The server normally appears silent while awaiting an MCP host's stdin. **Do not
type JSON into its terminal**: its input is MCP protocol messages, not raw
experiment JSON. By default, outputs live in `./artifacts/mcp`, relative to the
server's working directory. Set an absolute `--output-root` in agent settings
for predictable location and containment.

## Connect an agent

Configure an MCP-compatible local agent/host with a stdio server entry similar
to this (adapt the executable, checkout and output paths):

```json
{
  "mcpServers": {
    "openwave": {
      "command": "/absolute/path/to/openwave-mcp",
      "args": ["--output-root", "/absolute/path/to/openwave-runs"]
    }
  }
}
```

The actual configuration wrapper key may differ by MCP host. Another portable
choice is `"command": "/absolute/path/to/.venv/bin/python"` plus args
`["-m", "openwave.mcp_server", "--output-root", "..."]`.

Typical agent flow:

1. Call `get_experiment_schema` with `{}`.
2. Construct a document according to the returned versioned JSON Schema. See
   [`examples/wr90.json`](../examples/wr90.json) for a working WR-90 example.
3. Call `validate_experiment` with `{"document": <experiment>}` to check the
   document **and** the tighter MCP resource limits without solving.
4. Call `run_experiment` with `{"document": <experiment>, "run_name": "wr90-1"}`.
   It returns `status`, `run_name`, the absolute `output_dir`, and the usual
   `result` report containing cutoff frequencies and artifact hashes.
5. Read `results.json`, `fields.npy`, `x_m.npy`, and `y_m.npy` from that directory.
   Choose a new name for the next run; existing runs are never overwritten.

MCP successes return structured JSON. Invalid documents, unsafe output names,
resource excess, existing output directories, worker failures, and timeouts are
**MCP tool errors** (`is_error=true`) with specific codes and actionable text,
such as `invalid_input`, `resource_limit`, and `output_exists`.

## Resource and filesystem boundaries

| Boundary | MCP limit |
| --- | --- |
| Mesh | at most **4,096** grid cells (`nx * ny`) |
| Modes | at most **4** eigenmodes |
| Runtime | subprocess terminated after **45 seconds** |
| Parallel CPU libraries | BLAS/OMP thread environment capped at **1** thread |
| Output | new directory named by `run_name` only, under operator-set output root |
| `run_name` | 1–64 ASCII letters, digits, `_` or `-`, beginning with alphanumeric |

The regular experiment-format limits still apply. Arbitrary absolute paths,
`..` traversal, path separators, and symlinked output roots are rejected. A
run is staged in a parent-controlled temporary directory, then published only
on success; timeouts and failures clean up staging and do not leave a reported
partial result. Do not expose this local teaching server directly to untrusted
remote users; the limits are pragmatic guards, **not an OS-level security
sandbox** or a proven bound on solver memory use. The operator should configure
an output root with appropriate filesystem permissions.

The MCP adapter does not import the GUI or plotting modules, does not modify
the physics solver, and does not permit arbitrary Python or shell commands.
For the experiment and artifact semantics, see
[`AI_AGENT_WORKFLOW.md`](AI_AGENT_WORKFLOW.md).

## Tests

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest -q
```

`tests/test_mcp.py` uses the official SDK client both in memory and over a real
stdio subprocess. It covers schema discovery, validation, a complete artifact
run, errors, output confinement, duplicate names, limits, timeouts, and cleanup.
