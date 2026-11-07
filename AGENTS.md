# Agent development rules

- Keep one local OLMo model as the only planner, tool selector, reasoning engine, and final-answer writer.
- LangGraph coordinates the loop; Python must not hard-code NinjaOne intent routing or synthesize tenant answers.
- Use the bundled OpenAPI specification as the source of endpoint discovery and parameter schemas.
- Ground every tenant-specific statement in live NinjaOne tool results. Report errors, incomplete pagination, and missing permissions explicitly.
- Add tests for endpoint parsing, action policy, pagination, and tool-result handling.
- GET is allowed. POST/PUT/PATCH require an explicit human approval. DELETE remains blocked.
- Never log OAuth client secrets or commit .env.
- Do not modify the upstream repository or the user's existing NinjaRMM-API-Gateway-MCP repository from this project.
