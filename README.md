# NinjaRMM-API-Gateway-MCP7

A local-first NinjaOne API v2 gateway and **single-brain OLMo + LangGraph agent**.

This repository starts from the upstream [NinjaRMM-API-Gateway-MCP](https://github.com/jasondsmith72/NinjaRMM-API-Gateway-MCP) project. The upstream gateway and its OpenAPI catalogue are retained as the API execution/discovery layer. The agent is being built here as a separate project; no changes are made to the upstream repository or your earlier fork.

## Goals

- Cover the full NinjaOne API v2 OpenAPI catalogue, not a hand-picked list of seven business functions.
- Let one local OLMo model understand the request, plan, discover endpoints, choose parameters, call tools, inspect results, and write the answer.
- Use LangGraph for the agent loop and MCP for the API tool boundary.
- Ground answers in returned NinjaOne data. Never fabricate records, totals, or fields.
- Keep credentials local; no cloud LLM endpoint is required.
- Support multi-step requests, endpoint schema inspection, and paginated queries.
- Automatically permit GET requests. Require explicit terminal confirmation for POST, PUT, and PATCH. Block DELETE in the agent.

## Architecture

```text
User
  |
  v
Local OLMo (OpenAI-compatible Foundry endpoint)
  |  one reasoning model / one LangGraph ReAct loop
  v
MCP tools (discovery + schema + API execution)
  |
  v
NinjaOne API v2 + bundled OpenAPI catalogue
  |
  v
Grounded tool results -> OLMo final answer
```

Python provides transport, schema access, validation, and action safety. It does not hard-code intent-to-endpoint routing or compose the final answer.

## Requirements

- Python 3.10+
- A local OpenAI-compatible model server such as Foundry Local
- NinjaOne API application credentials with the scopes needed for the endpoints you intend to use

## Windows PowerShell setup

Run from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
notepad .env
```

Set the values in `.env`. Do not commit this file.

## Configuration

```dotenv
NINJAONE_CLIENT_ID=your-client-id
NINJAONE_CLIENT_SECRET=your-client-secret
NINJAONE_INSTANCE=eu.ninjarmm.com
NINJAONE_SCOPE=monitoring management control

FOUNDRY_BASE_URL=http://127.0.0.1:64541/v1
FOUNDRY_MODEL=olmo-3-7b-instruct-generic-gpu
FOUNDRY_API_KEY=local
AGENT_RECURSION_LIMIT=30
NINJA_MCP_LOG_LEVEL=INFO
```

Use the actual Foundry endpoint and model id shown by your local Foundry installation. Keep `.env` private.

## Run

```powershell
.\.venv\Scripts\Activate.ps1
ninjaone-agent
```

Or:

```powershell
python ninjaone_agent.py
```

Type `exit` to quit. The agent uses the MCP gateway as a local stdio child process, so you do not need to start a second server manually.

## API coverage and accuracy

The bundled `NinjaRMM-API-v2.json` is the source of endpoint discovery. The model can use `find_endpoint` to search across methods and categories, `describe_endpoint` to inspect parameter/body/response schemas, and `call` / `raw_call` to execute the selected API operation. Pagination must be continued when the API response indicates more records or a next-page cursor.

API coverage depends on the NinjaOne OpenAPI document, tenant permissions, API scopes, and the endpoints exposed by your region/version. A listed endpoint is not proof that your tenant can call it. The agent must report API errors and missing data rather than guessing.

## Action safety

- GET: allowed without confirmation.
- POST / PUT / PATCH: require a human confirmation in the terminal.
- DELETE: blocked by the agent.
- API credentials and Foundry configuration remain local.

These controls are deliberate safeguards, not limits on endpoint discovery. The catalogue remains available for all documented HTTP methods.

## Tests

```powershell
pytest -q
```

The gateway tests are retained from upstream. Agent-specific tests are being added as the agent implementation evolves.

## Upstream

- Gateway foundation: https://github.com/jasondsmith72/NinjaRMM-API-Gateway-MCP
- NinjaOne API documentation: https://app.ninjarmm.com/apidocs/
