 CSPM Agent

An agentic Cloud Security Posture Management (CSPM) tool that automatically evaluates the security posture of a Cloud tenancy. The agent uses an LLM to drive security checks (based on CIS benchmark) across compute, storage, networking, and IAM resources via OCI API calls and local network scanning tools. This CSPM agent runs on Oracle Cloud Infrasructure (OCI) tenancy, and can be easily extended to other clouds.

## How it works

The agent runs in three stages:

1. **Profile load** — feeds a detailed security evaluation profile to the LLM and stores it in an MCP memory server for later retrieval.
2. **Security evaluation** — the LLM autonomously runs checks for each domain (compute, storage, networking, IAM) by calling OCI API tools via MCP and local tools (`check_ssh_connectivity`, `scan_ports`).
3. **Report** — the LLM summarises findings with severity ratings for each check.

```
cspm_agent.py
    │
    ├── OCI API MCP server (oracle.oci-api-mcp-server)  ← OCI resource queries
    ├── MCP Memory server (@modelcontextprotocol/server-memory)  ← security profile store
    └── Custom tools (mcp_tools.py)
            ├── check_ssh_connectivity  ← TCP port 22 probe
            └── scan_ports              ← nmap top-25 port scan
```

## Security checks

| Domain | Checks |
|--------|--------|
| **Compute** | Internet exposure via Security Lists / NSGs, SSH connectivity, open port scan |
| **Storage** | Public bucket access, Oracle-managed vs customer-managed encryption keys, bucket versioning |
| **Networking** | Security lists / NSGs with `0.0.0.0/0` ingress on sensitive ports (22, 3389), missing Service Gateway |
| **IAM** | MFA status, Administrators group size, API key age (>90 days), password complexity policy |

## Project structure

```
cspm/
├── cspm_agent.py        # Main agent entry point
├── mcp_tools.py         # Custom tools: SSH check and nmap port scan
├── llm_functions.py     # Helper functions for printing LLM responses and token usage
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (not committed)
```

## Prerequisites

- Python 3.13+
- [OCI CLI](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm) configured with a valid session
- [nmap](https://nmap.org/download.html) installed and on `PATH` (or set `NMAP_PATH`)
- [uvx](https://docs.astral.sh/uv/) for running the OCI MCP server
- [npx](https://docs.npmjs.com/cli/v8/commands/npx) for running the MCP memory server
- Anthropic and/or OpenAI API keys

## Installation

```bash
# Create and activate virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install oci oci-cli
pip install aisuite
pip install 'aisuite[anthropic]'
pip install 'aisuite[openai]'
pip install 'aisuite[mcp]'

# Or install everything at once
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```bash
# Required: LLM API keys
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Required: OCI configuration
OCI_COMPARTMENT_ID=ocid1.tenancy.oc1..your_compartment_id

# Optional: tool paths (defaults to PATH lookup)
UVX_PATH=uvx
NMAP_PATH=nmap
```

## OCI Authentication

Authenticate with OCI before running the agent:

```bash
oci session authenticate --region=us-ashburn-1 --tenancy-name=<your_tenancy> --profile DEFAULT
```

## Usage

```bash
source .venv/bin/activate
python cspm_agent.py
```

The agent will:
1. Load and summarise the security evaluation profile
2. Run compute, storage, networking, and IAM security checks sequentially
3. Print colour-coded results and token usage for each step

## Models

The agent defaults to `claude-sonnet-4-6`. To switch to GPT-4.1, change `models[0]` to `models[1]` in `cspm_agent.py`. The `models` list is:

```python
models = ["anthropic:claude-sonnet-4-6", "openai:gpt-4.1"]
```

## Dependencies

Key packages (see `requirements.txt` for full pinned list):

| Package | Purpose |
|---------|---------|
| `aisuite` | Multi-LLM abstraction and MCP client |
| `anthropic` | Claude API |
| `openai` | OpenAI API |
| `oci` | Oracle Cloud Infrastructure SDK |
| `mcp` | Model Context Protocol |
| `python-dotenv` | `.env` file loading |

